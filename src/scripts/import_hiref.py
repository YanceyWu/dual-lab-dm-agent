"""
scripts/import_hiref.py — Import HIREF Status Report Excel into pm.db

Updates:
  - employees.resource_type  (STFTE for listed staff, LTFTE for rest)
  - employees.current_hiref  (HIREF ID)
  - employees.billing_end_date
  - hiref table              (upsert current HIREF contracts; preserve start dates and next HIREF slots)

Usage:
    python3 scripts/import_hiref.py --file "data-feed/HIREF_Status_Report_2026-05-25.xlsx"
"""

import re
import sys
import sqlite3
import argparse
from pathlib import Path
from datetime import date, datetime

sys.path.insert(0, str(Path(__file__).parent.parent))
from pm_agent.database.bootstrap import main as init_db
from pm_agent.config import settings
from pm_agent.database import repository

try:
    import openpyxl
except ImportError:
    print("Run: pip3 install openpyxl")
    sys.exit(1)


def normalize_name(name: str) -> str:
    """Strip Chinese suffix and extra whitespace for fuzzy matching."""
    name = name.strip()
    name = re.sub(r'\s*[（(][^）)]+[）)]\s*', '', name)
    return name.strip().lower()


def load_hiref_excel(file_path: str) -> list[dict]:
    wb = openpyxl.load_workbook(file_path, data_only=True)
    ws = wb['Staff HIREF Status']
    records = []
    for row in ws.iter_rows(min_row=3, values_only=True):
        if not row[1]:
            continue
        records.append({
            'name':          str(row[1]).strip(),
            'role':          str(row[2]).strip() if row[2] else '',
            'resource_type': str(row[3]).strip() if row[3] else 'STFTE',
            'current_hiref': str(row[4]).strip() if row[4] else '',
            'hiref_project': str(row[5]).strip() if row[5] else '',
            'end_date':      str(row[6]).strip() if row[6] else '',
            'actual_project':str(row[9]).strip() if row[9] else '',
            'match':         str(row[10]).strip() if row[10] else '',
        })
    return records


def import_hiref(file_path: str, dry_run: bool = False) -> None:
    init_db()
    records = load_hiref_excel(file_path)
    print(f"Loaded {len(records)} STFTE records from Excel")

    db_path = settings.database_path
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row

    # Load all employees for name matching
    employees = con.execute("SELECT id, name FROM employees WHERE status = 'active'").fetchall()
    emp_lookup = {}  # normalized_name → employee_id
    for e in employees:
        key = normalize_name(e['name'])
        emp_lookup[key] = e['id']

    stfte_ids = set()
    matched = []
    unmatched = []

    for rec in records:
        key = normalize_name(rec['name'])
        emp_id = emp_lookup.get(key)
        if emp_id:
            stfte_ids.add(emp_id)
            matched.append((emp_id, rec))
        else:
            unmatched.append(rec['name'])

    print(f"  Matched: {len(matched)} employees")
    if unmatched:
        print(f"  Unmatched (check names): {unmatched}")

    if dry_run:
        print("[DRY RUN] Stopping before DB writes.")
        con.close()
        return

    run_id = repository.start_sync_run(
        "import-hiref-report",
        run_type="file-import",
        target_tables=["employees", "hiref"],
        artifact_path=str(Path(file_path).resolve()),
        triggered_by="cli",
        notes="HIREF status report import",
    )
    updated_stfte = 0
    ltfte_ids: list[str] = []
    fallback_start_date_count = 0
    hiref_map: dict[str, dict] = {}
    try:
        # Update STFTE employees
        for emp_id, rec in matched:
            con.execute("""
                UPDATE employees
                SET resource_type = ?,
                    current_hiref = ?,
                    billing_end_date = ?
                WHERE id = ?
            """, [rec['resource_type'], rec['current_hiref'], rec['end_date'], emp_id])
            updated_stfte += 1

        # Mark remaining active employees as LTFTE
        ltfte_ids = [e['id'] for e in employees if e['id'] not in stfte_ids]
        if ltfte_ids:
            con.executemany(
                "UPDATE employees SET resource_type = 'LTFTE' WHERE id = ?",
                [(eid,) for eid in ltfte_ids]
            )
        print(f"  ✓ Updated {updated_stfte} STFTE employees")
        print(f"  ✓ Marked {len(ltfte_ids)} employees as LTFTE")

        # Upsert hiref table — collect unique HIREF IDs
        for rec in records:
            hid = rec['current_hiref']
            if hid and hid not in hiref_map:
                hiref_map[hid] = rec

        existing_hiref = {
            row["id"]: row["start_date"]
            for row in con.execute("SELECT id, start_date FROM hiref").fetchall()
        }
        for hid, rec in hiref_map.items():
            start_date = existing_hiref.get(hid) or date.today().isoformat()
            note_parts = [
                f"Actual project: {rec['actual_project']}.",
                f"Match: {rec['match']}",
            ]
            if hid not in existing_hiref:
                fallback_start_date_count += 1
                note_parts.append(
                    f"Start date unavailable in source file; defaulted to import date {start_date}."
                )
            con.execute("""
                INSERT OR REPLACE INTO hiref (id, project, request_type, start_date, end_date, notes)
                VALUES (?, ?, 'extend', ?, ?, ?)
            """, [hid, rec['hiref_project'], start_date, rec['end_date'], " ".join(note_parts)])
        print(f"  ✓ Upserted {len(hiref_map)} HIREF contracts")
        if fallback_start_date_count:
            print(
                f"  ⚠ Defaulted {fallback_start_date_count} HIREF start date(s) to the import date "
                "because the source report does not provide contract start dates"
            )

        con.commit()
        con.close()
        repository.finish_sync_run(
            run_id,
            rows_in=len(records),
            rows_changed=updated_stfte + len(ltfte_ids) + len(hiref_map),
            notes=(
                "HIREF import completed successfully."
                if not fallback_start_date_count
                else (
                    "HIREF import completed successfully. "
                    f"{fallback_start_date_count} missing start date(s) defaulted to import date."
                )
            ),
        )
    except Exception as exc:
        con.close()
        repository.fail_sync_run(run_id, str(exc), rows_in=len(records))
        raise

    print()
    print("Verification:")
    con2 = sqlite3.connect(db_path)
    rows = con2.execute("""
        SELECT resource_type, COUNT(*) as cnt FROM employees GROUP BY resource_type ORDER BY resource_type
    """).fetchall()
    for r in rows:
        print(f"  {r[0] or '(empty)':8s}: {r[1]} staff")

    print()
    print("STFTE expiry summary:")
    today = date.today()
    stfte_rows = con2.execute("""
        SELECT name, billing_end_date, current_hiref FROM employees
        WHERE resource_type = 'STFTE' ORDER BY billing_end_date
    """).fetchall()
    buckets = {}
    for r in stfte_rows:
        if r[1]:
            d = (datetime.strptime(r[1], '%Y-%m-%d').date() - today).days
            label = 'Jul-31' if d <= 65 else ('Sep-30' if d <= 125 else ('Dec-31' if d <= 220 else 'Apr-27+'))
            buckets.setdefault(label, []).append(r[0])
    for label, names in buckets.items():
        print(f"  {label}: {len(names)} — {', '.join(names)}")
    con2.close()
    print()
    print("Done. HIREF data is now in DB.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Import HIREF Status Report Excel into pm.db')
    parser.add_argument('--file', required=True, help='Path to HIREF Status Report Excel')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    import_hiref(args.file, dry_run=args.dry_run)
