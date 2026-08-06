"""
pm_agent.sync.servicenow.cr_import — Import Change Requests from ServiceNow CSV export.

Workflow:
  1. Log into ServiceNow in your browser
  2. Visit the report URL — CSV will auto-download
  3. Save a `servicenow-change-request-csv` source profile under `pm onboarding`
  4. Run preview → confirm through `pm onboarding`

The script auto-detects column names (SNOW exports vary by report config).
"""

import csv
import json
import sqlite3
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any

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


def preview_cr_import(
    file_path: Path,
    *,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    records, unmapped = load_csv(str(file_path))
    counts = _plan_counts(records, db_path=db_path)
    counts["unmapped_columns"] = len(unmapped)
    warnings: list[dict[str, Any]] = []
    if unmapped:
        warnings.append(
            {
                "severity": "warning",
                "code": "SERVICENOW_CHANGE_REQUEST_UNMAPPED_COLUMNS_STORED",
                "message": (
                    "Unmapped CSV columns will be preserved in raw_data: "
                    + ", ".join(unmapped[:8])
                    + (" ..." if len(unmapped) > 8 else "")
                ),
                "location": "source",
            }
        )
    status = (
        "already_completed"
        if counts["planned_inserts"] == 0 and counts["planned_updates"] == 0
        else "previewed"
    )
    return {
        "status": status,
        "blockers": [],
        "warnings": warnings,
        "conflicts": [],
        "counts": counts,
        "payload": {
            "publication_id": _publication_id(records, unmapped),
            "change_request_fingerprint": _fingerprint(records, unmapped),
            "change_request_ids": [str(record.get("id") or "") for record in records],
            "sample_records": [
                {
                    "id": record.get("id"),
                    "state": record.get("state"),
                    "short_desc": record.get("short_desc", ""),
                }
                for record in records[:3]
            ],
        },
        "report": {
            "coverage": {
                "state": "complete",
                "change_requests": counts["change_requests"],
                "planned_inserts": counts["planned_inserts"],
                "planned_updates": counts["planned_updates"],
                "unchanged_records": counts["unchanged_records"],
                "project_codes": counts["project_codes"],
                "unmapped_columns": len(unmapped),
            },
            "preserved_semantics": {
                "newer_updated_on_required_for_updates": True,
                "unmapped_columns_preserved_in_raw_data": bool(unmapped),
                "audit_source_id": "servicenow-change-requests",
            },
        },
    }


def apply_cr_import(
    file_path: Path,
    *,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    records, unmapped = load_csv(str(file_path))
    counts = _plan_counts(records, db_path=db_path)
    counts["unmapped_columns"] = len(unmapped)
    total = len(records)
    run_id = repository.start_sync_run(
        "servicenow-change-requests",
        run_type="file-import",
        target_tables=["change_requests"],
        artifact_path=str(file_path.resolve()),
        triggered_by="cli",
        notes="ServiceNow CR CSV import",
    )

    database_path = Path(db_path or settings.database_path)
    con = None
    inserted = updated = skipped = 0
    try:
        con = sqlite3.connect(database_path)
        con.row_factory = sqlite3.Row

        for record in records:
            cr_id = record.get("id", "")
            existing = con.execute(
                "SELECT updated_on FROM change_requests WHERE id=?",
                [cr_id],
            ).fetchone()

            fields = {
                key: record.get(key, "")
                for key in (
                    "id",
                    "short_desc",
                    "state",
                    "priority",
                    "category",
                    "assignment_group",
                    "assigned_to",
                    "requested_by",
                    "project_code",
                    "planned_start",
                    "planned_end",
                    "actual_start",
                    "actual_end",
                    "created_on",
                    "updated_on",
                    "close_code",
                    "close_notes",
                    "raw_data",
                )
            }
            fields["imported_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if not existing:
                con.execute(
                    """
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
                    """,
                    fields,
                )
                inserted += 1
                continue

            existing_upd = existing["updated_on"] or ""
            new_upd = fields.get("updated_on", "")
            if not existing_upd or new_upd > existing_upd:
                con.execute(
                    """
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
                    """,
                    fields,
                )
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
        state_counts = [
            {"state": row["state"] or "Unknown", "count": int(row["cnt"])}
            for row in con.execute(
                """
                SELECT state, COUNT(*) as cnt
                FROM change_requests
                GROUP BY state ORDER BY cnt DESC
                """
            ).fetchall()
        ]
    except Exception as exc:
        if con is not None:
            con.close()
        repository.fail_sync_run(
            run_id,
            str(exc),
            rows_in=total,
            rows_changed=inserted + updated,
        )
        raise
    finally:
        if con is not None:
            con.close()

    warnings: list[dict[str, Any]] = []
    if unmapped:
        warnings.append(
            {
                "severity": "warning",
                "code": "SERVICENOW_CHANGE_REQUEST_UNMAPPED_COLUMNS_STORED",
                "message": (
                    "Unmapped CSV columns were preserved in raw_data: "
                    + ", ".join(unmapped[:8])
                    + (" ..." if len(unmapped) > 8 else "")
                ),
                "location": "source",
            }
        )
    return {
        "status": "completed",
        "blockers": [],
        "warnings": warnings,
        "conflicts": [],
        "counts": counts,
        "payload": {
            "publication_id": _publication_id(records, unmapped),
            "change_request_fingerprint": _fingerprint(records, unmapped),
            "change_request_ids": [str(record.get("id") or "") for record in records],
            "sync_run_id": run_id,
        },
        "report": {
            "coverage": {
                "state": "complete",
                "change_requests": counts["change_requests"],
                "planned_inserts": counts["planned_inserts"],
                "planned_updates": counts["planned_updates"],
                "unchanged_records": counts["unchanged_records"],
                "project_codes": counts["project_codes"],
                "unmapped_columns": counts["unmapped_columns"],
            },
            "result": {
                "inserted": inserted,
                "updated": updated,
                "skipped": skipped,
                "sync_run_id": run_id,
                "state_counts": state_counts,
                "unmapped_columns": counts["unmapped_columns"],
            },
            "preserved_semantics": {
                "newer_updated_on_required_for_updates": True,
                "unmapped_columns_preserved_in_raw_data": bool(unmapped),
                "audit_source_id": "servicenow-change-requests",
            },
        },
    }


def import_cr(file_path: str, dry_run: bool = False) -> None:
    init_db()

    path = Path(file_path)
    preview = preview_cr_import(path)
    print(f"Parsed {preview['counts']['change_requests']} CR records from {path.name}")

    if preview["warnings"]:
        print(f"  ℹ  {preview['warnings'][0]['message']}")

    if dry_run:
        print("[DRY RUN] Sample records:")
        for record in preview["payload"]["sample_records"]:
            print(
                f"  {record.get('id')} | {record.get('state')} | "
                f"{str(record.get('short_desc') or '')[:60]}"
            )
        return

    result = apply_cr_import(path)
    summary = result["report"]["result"]
    print(
        "  ✓ Inserted: "
        f"{summary['inserted']}  Updated: {summary['updated']}  "
        f"Skipped (no change): {summary['skipped']}"
    )
    print()
    print("  CR状态分布:")
    for row in summary["state_counts"]:
        bar = "█" * min(int(row["count"]), 30)
        print(f"    {str(row['state']):20s}  {int(row['count']):4d}  {bar}")
    print()
    print("Done. Run `python3 -m pm_agent.cli.app cr list` to view.")


def main() -> None:
    raise SystemExit(
        "This direct ServiceNow CR import entrypoint is retired. "
        "Use `pm onboarding` with source type `servicenow-change-request-csv`."
    )


def _plan_counts(
    records: list[dict[str, Any]],
    *,
    db_path: str | Path | None = None,
) -> dict[str, int]:
    connection = sqlite3.connect(Path(db_path or settings.database_path))
    connection.row_factory = sqlite3.Row
    planned_inserts = 0
    planned_updates = 0
    unchanged_records = 0
    try:
        for record in records:
            existing = connection.execute(
                """
                SELECT id, short_desc, state, priority, category,
                       assignment_group, assigned_to, requested_by,
                       project_code, planned_start, planned_end,
                       actual_start, actual_end, created_on, updated_on,
                       close_code, close_notes, raw_data
                FROM change_requests
                WHERE id=?
                """,
                [record.get("id", "")],
            ).fetchone()
            if existing is None:
                planned_inserts += 1
                continue
            if _matches_existing_record(existing, record):
                unchanged_records += 1
                continue
            existing_upd = existing["updated_on"] or ""
            new_upd = record.get("updated_on", "")
            if not existing_upd or new_upd > existing_upd:
                planned_updates += 1
            else:
                unchanged_records += 1
    finally:
        connection.close()
    return {
        "change_requests": len(records),
        "planned_inserts": planned_inserts,
        "planned_updates": planned_updates,
        "unchanged_records": unchanged_records,
        "project_codes": len(
            {
                str(record.get("project_code") or "")
                for record in records
                if record.get("project_code")
            }
        ),
        "unmapped_columns": 0,
    }


def _fingerprint(records: list[dict[str, Any]], unmapped: list[str]) -> str:
    digest = hashlib.sha256()
    digest.update(
        json.dumps(
            {"records": records, "unmapped": unmapped},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    )
    return digest.hexdigest()


def _publication_id(records: list[dict[str, Any]], unmapped: list[str]) -> str:
    return f"servicenow-change-request-csv:{_fingerprint(records, unmapped)}"


def _matches_existing_record(existing: sqlite3.Row, record: dict[str, Any]) -> bool:
    return all(
        str(existing[field] or "") == str(record.get(field, "") or "")
        for field in (
            "id",
            "short_desc",
            "state",
            "priority",
            "category",
            "assignment_group",
            "assigned_to",
            "requested_by",
            "project_code",
            "planned_start",
            "planned_end",
            "actual_start",
            "actual_end",
            "created_on",
            "updated_on",
            "close_code",
            "close_notes",
            "raw_data",
        )
    )


if __name__ == "__main__":
    main()
