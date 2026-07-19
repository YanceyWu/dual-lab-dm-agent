"""
pm_agent.sync.servicenow.cr_import — Import Change Requests from ServiceNow CSV export.

Workflow:
  1. Log into ServiceNow in your browser
  2. Visit the report URL — CSV will auto-download
  3. Run: python3 scripts/import_cr_csv.py --file <path_to_csv>

The script auto-detects column names (SNOW exports vary by report config).

Usage:
    python3 scripts/import_cr_csv.py --file ~/Downloads/sys_report_template.csv
    python3 scripts/import_cr_csv.py --file data-feed/cr_2026-05-31.csv --dry-run
"""

import csv
import json
import sqlite3
import argparse
from datetime import datetime
from pathlib import Path

from pm_agent.database.bootstrap import main as init_db
from pm_agent.config import settings
from pm_agent.database import repository


# ── Column name mapping (SNOW column → our field) ──────────────────────────
# Keys are lowercase stripped versions of whatever SNOW exports.
# Add aliases here if the report has different column names.
FIELD_MAP = {
    # CR number
    "number":                   "id",
    "change":                   "id",
    "change request":           "id",

    # Short description
    "short description":        "short_desc",
    "short_description":        "short_desc",
    "description":              "short_desc",

    # State / status
    "state":                    "state",
    "status":                   "state",

    # Priority
    "priority":                 "priority",

    # Category / type
    "type":                     "category",
    "change type":              "category",
    "category":                 "category",

    # Assignment
    "assignment group":         "assignment_group",
    "assignment_group":         "assignment_group",
    "assigned to":              "assigned_to",
    "assigned_to":              "assigned_to",

    # Requestor
    "requested by":             "requested_by",
    "requested_by":             "requested_by",
    "opened by":                "requested_by",
    "sys created by":           "requested_by",

    # Dates
    "planned start date":       "planned_start",
    "planned start":            "planned_start",
    "start date":               "planned_start",
    "start_date":               "planned_start",
    "planned end date":         "planned_end",
    "planned end":              "planned_end",
    "end date":                 "planned_end",
    "end_date":                 "planned_end",
    "actual start":             "actual_start",
    "actual start date":        "actual_start",
    "work start":               "actual_start",
    "work_start":               "actual_start",
    "actual end":               "actual_end",
    "actual end date":          "actual_end",
    "work end":                 "actual_end",
    "work_end":                 "actual_end",
    "created":                  "created_on",
    "created on":               "created_on",
    "opened":                   "created_on",
    "updated":                  "updated_on",
    "updated on":               "updated_on",

    # Close info
    "close code":               "close_code",
    "close notes":              "close_notes",

    # Project linkage
    "project":                  "project_code",
    "business service":         "project_code",
    "u_project_code":           "project_code",
    "u project code":           "project_code",
}

KNOWN_FIELDS = set(FIELD_MAP.values())


def normalise_col(col: str) -> str:
    return col.strip().lower().replace("_", " ")


def parse_date(val: str) -> str:
    """Try to normalise various date formats to YYYY-MM-DD."""
    if not val or val.strip() in ("", "N/A", "None", "-"):
        return ""
    val = val.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%m/%d/%Y %H:%M:%S",
                "%m/%d/%Y", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(val, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return val  # return as-is if no format matched


def load_csv(file_path: str) -> tuple[list[dict], list[str]]:
    """Return (records, unmapped_columns)."""
    records = []
    unmapped = set()

    with open(file_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        raw_cols = reader.fieldnames or []

        # Build col → field mapping for this file
        col_map = {}
        for col in raw_cols:
            norm = normalise_col(col)
            if norm in FIELD_MAP:
                col_map[col] = FIELD_MAP[norm]
            else:
                unmapped.add(col)

        for row in reader:
            record: dict = {}
            extra: dict = {}
            for col, val in row.items():
                val = (val or "").strip()
                field = col_map.get(col)
                if field:
                    record[field] = val
                else:
                    extra[col] = val  # stash in raw_data

            # Skip rows without a CR number
            cr_id = record.get("id", "").strip()
            if not cr_id or cr_id.lower() in ("", "number", "change"):
                continue

            # Normalise dates
            for date_field in ("planned_start", "planned_end", "actual_start",
                               "actual_end", "created_on", "updated_on"):
                if date_field in record:
                    record[date_field] = parse_date(record[date_field])

            record["raw_data"] = json.dumps(extra, ensure_ascii=False)
            records.append(record)

    return records, sorted(unmapped)


def import_cr(file_path: str, dry_run: bool = False) -> None:
    init_db()

    records, unmapped = load_csv(file_path)
    total = len(records)
    print(f"Parsed {total} CR records from {Path(file_path).name}")

    if unmapped:
        print(f"  ℹ  Unmapped columns (stored in raw_data): {', '.join(unmapped[:8])}"
              + (" ..." if len(unmapped) > 8 else ""))

    if dry_run:
        print("[DRY RUN] Sample records:")
        for r in records[:3]:
            print(f"  {r.get('id')} | {r.get('state')} | {r.get('short_desc','')[:60]}")
        return

    run_id = repository.start_sync_run(
        "servicenow-change-requests",
        run_type="file-import",
        target_tables=["change_requests"],
        artifact_path=str(Path(file_path).resolve()),
        triggered_by="cli",
        notes="ServiceNow CR CSV import",
    )

    db_path = Path(settings.database_path)
    con = None
    inserted = updated = skipped = 0
    try:
        con = sqlite3.connect(db_path)
        con.row_factory = sqlite3.Row

        for r in records:
            cr_id = r.get("id", "")
            existing = con.execute(
                "SELECT updated_on FROM change_requests WHERE id=?", [cr_id]
            ).fetchone()

            fields = {
                k: r.get(k, "")
                for k in ("id", "short_desc", "state", "priority", "category",
                          "assignment_group", "assigned_to", "requested_by",
                          "project_code", "planned_start", "planned_end",
                          "actual_start", "actual_end", "created_on",
                          "updated_on", "close_code", "close_notes", "raw_data")
            }
            fields["imported_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if not existing:
                con.execute("""
                    INSERT INTO change_requests
                    (id, short_desc, state, priority, category,
                     assignment_group, assigned_to, requested_by,
                     project_code, planned_start, planned_end,
                     actual_start, actual_end, created_on, updated_on,
                     close_code, close_notes, raw_data, imported_at)
                    VALUES
                    (:id,:short_desc,:state,:priority,:category,
                     :assignment_group,:assigned_to,:requested_by,
                     :project_code,:planned_start,:planned_end,
                     :actual_start,:actual_end,:created_on,:updated_on,
                     :close_code,:close_notes,:raw_data,:imported_at)
                """, fields)
                inserted += 1
            else:
                # Update only if SNOW record is newer
                existing_upd = existing["updated_on"] or ""
                new_upd = fields.get("updated_on", "")
                if not existing_upd or new_upd > existing_upd:
                    con.execute("""
                        UPDATE change_requests SET
                            short_desc=:short_desc, state=:state, priority=:priority,
                            category=:category, assignment_group=:assignment_group,
                            assigned_to=:assigned_to, requested_by=:requested_by,
                            project_code=:project_code, planned_start=:planned_start,
                            planned_end=:planned_end, actual_start=:actual_start,
                            actual_end=:actual_end, created_on=:created_on,
                            updated_on=:updated_on, close_code=:close_code,
                            close_notes=:close_notes, raw_data=:raw_data,
                            imported_at=:imported_at
                        WHERE id=:id
                    """, fields)
                    updated += 1
                else:
                    skipped += 1

        con.commit()
        repository.finish_sync_run(
            run_id,
            rows_in=total,
            rows_changed=inserted + updated,
            notes=(
                "ServiceNow CR CSV import completed successfully."
                if not unmapped
                else (
                    "ServiceNow CR CSV import completed successfully. "
                    f"Unmapped columns stored in raw_data: {', '.join(unmapped[:5])}"
                )
            ),
        )

        # ── Summary ──
        print(f"  ✓ Inserted: {inserted}  Updated: {updated}  Skipped (no change): {skipped}")

        # State breakdown
        print()
        print("  CR状态分布:")
        state_counts = con.execute("""
            SELECT state, COUNT(*) as cnt
            FROM change_requests
            GROUP BY state ORDER BY cnt DESC
        """).fetchall()
        for row in state_counts:
            bar = "█" * min(row["cnt"], 30)
            print(f"    {(row['state'] or 'Unknown'):20s}  {row['cnt']:4d}  {bar}")

        con.close()
        print()
        print("Done. Run `python3 -m pm_agent.cli.app cr list` to view.")
    except Exception as exc:
        if con is not None:
            con.close()
        repository.fail_sync_run(run_id, str(exc), rows_in=total, rows_changed=inserted + updated)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description="Import ServiceNow CR CSV into pm.db")
    parser.add_argument("--file", required=True, help="Path to downloaded CSV file")
    parser.add_argument("--dry-run", action="store_true",
                        help="Parse only, do not write to DB")
    args = parser.parse_args()
    import_cr(args.file, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
