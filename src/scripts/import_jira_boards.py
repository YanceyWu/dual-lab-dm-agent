#!/usr/bin/env python3
# ruff: noqa: E402
"""Import JIRA board configuration rows from CSV."""

from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from pm_agent.config import settings
from pm_agent.database.bootstrap import main as init_db


def _to_bool(value: str | None, default: bool = False) -> int:
    if value is None or value == "":
        return 1 if default else 0
    return 1 if value.strip().lower() in {"1", "true", "yes", "y"} else 0


def _load_rows(file_path: Path) -> list[dict[str, str]]:
    with file_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = [dict(row) for row in reader]
    return rows


def _upsert_data_source(con: sqlite3.Connection, payload: dict) -> None:
    con.execute(
        """
        INSERT INTO data_sources
            (id, source_type, source_name, ingestion_mode, refresh_sla_hours,
             active, config_json, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            source_type = excluded.source_type,
            source_name = excluded.source_name,
            ingestion_mode = excluded.ingestion_mode,
            refresh_sla_hours = excluded.refresh_sla_hours,
            active = excluded.active,
            config_json = excluded.config_json,
            notes = excluded.notes,
            updated_at = datetime('now')
        """,
        [
            payload["id"],
            payload["source_type"],
            payload["source_name"],
            payload.get("ingestion_mode", "manual"),
            payload.get("refresh_sla_hours", 24),
            1 if payload.get("active", True) else 0,
            json.dumps(payload.get("config", {}), ensure_ascii=False),
            payload.get("notes", ""),
        ],
    )


def _delete_board_family(con: sqlite3.Connection, board_ids: list[str]) -> None:
    if not board_ids:
        return
    placeholders = ",".join("?" for _ in board_ids)
    params = list(board_ids)
    con.execute(f"DELETE FROM jira_health_snapshots WHERE board_id IN ({placeholders})", params)
    con.execute(f"DELETE FROM jira_sprints WHERE board_id IN ({placeholders})", params)
    con.execute(f"DELETE FROM jira_issues WHERE board_id IN ({placeholders})", params)
    con.execute(f"DELETE FROM jira_stream_versions WHERE board_id IN ({placeholders})", params)
    con.execute(f"DELETE FROM jira_board_configs WHERE id IN ({placeholders})", params)
    data_source_ids: list[str] = []
    for board_id in board_ids:
        data_source_ids.extend(
            [
                f"jira-release-{board_id}",
                f"jira-health-{board_id}",
                f"jira-evidence-{board_id}",
            ]
        )
    ds_placeholders = ",".join("?" for _ in data_source_ids)
    con.execute(f"DELETE FROM data_sources WHERE id IN ({ds_placeholders})", data_source_ids)


def _cleanup_project_key_facts(con: sqlite3.Connection) -> None:
    con.execute(
        """
        DELETE FROM memory_facts
        WHERE category = 'jira_project_key'
          AND source = 'csv-import'
          AND subject NOT IN (
              SELECT DISTINCT project_key
              FROM jira_board_configs
          )
        """
    )


def import_jira_boards(
    file_path: Path,
    dry_run: bool = False,
    merge_only: bool = False,
) -> None:
    init_db()
    rows = _load_rows(file_path)
    print(f"Loaded {len(rows)} JIRA board rows from {file_path}")
    incoming_board_ids = [row.get("id", "").strip() for row in rows if row.get("id", "").strip()]
    if dry_run:
        for row in rows[:5]:
            print(
                "  DRY",
                row.get("id", "").strip(),
                row.get("project_key", "").strip().upper(),
                row.get("version_name_pattern", "").strip() or "(no version filter)",
            )
        if not merge_only:
            print("  DRY sync-mode: rows absent from the CSV would be removed from board configs and JIRA caches.")
        return

    con = sqlite3.connect(settings.database_path)
    imported = 0
    removed = 0
    try:
        if not merge_only:
            stale_board_ids = [
                row[0]
                for row in con.execute(
                    f"SELECT id FROM jira_board_configs WHERE id NOT IN ({','.join('?' for _ in incoming_board_ids)})",
                    incoming_board_ids,
                ).fetchall()
            ] if incoming_board_ids else [
                row[0] for row in con.execute("SELECT id FROM jira_board_configs").fetchall()
            ]
            _delete_board_family(con, stale_board_ids)
            removed = len(stale_board_ids)

        for row in rows:
            board_key = row.get("id", "").strip()
            name = row.get("name", "").strip()
            project_key = row.get("project_key", "").strip().upper()
            base_jql = row.get("base_jql", "").strip()
            if not board_key or not name or not project_key or not base_jql:
                raise ValueError(
                    "Each CSV row must include id, name, project_key, and base_jql."
                )

            version_name_pattern = row.get("version_name_pattern", "").strip() or None
            jira_board_id = row.get("board_id", "").strip() or None
            board_url = row.get("board_url", "").strip() or None
            pm_project_id = row.get("pm_project_id", "").strip() or None
            active = _to_bool(row.get("active"), default=True)
            issues_use_base_jql = _to_bool(row.get("issues_use_base_jql"), default=False)
            notes = row.get("notes", "").strip()

            con.execute(
                """
                INSERT INTO jira_board_configs
                    (id, name, project_key, base_jql, version_name_pattern,
                     board_id, board_url, pm_project_id, active, notes, issues_use_base_jql)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    project_key = excluded.project_key,
                    base_jql = excluded.base_jql,
                    version_name_pattern = excluded.version_name_pattern,
                    board_id = excluded.board_id,
                    board_url = excluded.board_url,
                    pm_project_id = excluded.pm_project_id,
                    active = excluded.active,
                    notes = excluded.notes,
                    issues_use_base_jql = excluded.issues_use_base_jql,
                    updated_at = datetime('now')
                """,
                [
                    board_key,
                    name,
                    project_key,
                    base_jql,
                    version_name_pattern,
                    jira_board_id,
                    board_url,
                    pm_project_id,
                    active,
                    notes,
                    issues_use_base_jql,
                ],
            )
            con.execute(
                """
                INSERT OR IGNORE INTO memory_facts (category, subject, fact, confidence, source)
                VALUES ('jira_project_key', ?, 'JIRA project key registered for sync', 1.0, 'csv-import')
                """,
                [project_key],
            )
            _upsert_data_source(
                con,
                {
                    "id": f"jira-release-{board_key}",
                    "source_type": "jira",
                    "source_name": f"JIRA Release Sync — {name}",
                    "ingestion_mode": "api",
                    "refresh_sla_hours": 24,
                    "active": bool(active),
                    "config": {
                        "board_id": board_key,
                        "jira_board_id": jira_board_id or "",
                        "project_key": project_key,
                        "version_name_pattern": version_name_pattern or "",
                        "board_url": board_url or "",
                        "pm_project_id": pm_project_id or "",
                        "issues_use_base_jql": bool(issues_use_base_jql),
                    },
                    "notes": "Per-board JIRA release/version sync.",
                }
            )
            _upsert_data_source(
                con,
                {
                    "id": f"jira-health-{board_key}",
                    "source_type": "jira",
                    "source_name": f"JIRA Health Sync — {name}",
                    "ingestion_mode": "api",
                    "refresh_sla_hours": 24,
                    "active": bool(active),
                    "config": {
                        "board_id": board_key,
                        "jira_board_id": jira_board_id or "",
                        "project_key": project_key,
                        "version_name_pattern": version_name_pattern or "",
                        "board_url": board_url or "",
                        "pm_project_id": pm_project_id or "",
                    },
                    "notes": "Per-board JIRA sprint/health sync.",
                }
            )
            _upsert_data_source(
                con,
                {
                    "id": f"jira-evidence-{board_key}",
                    "source_type": "jira",
                    "source_name": f"JIRA Incremental Evidence — {name}",
                    "ingestion_mode": "api",
                    "refresh_sla_hours": 24,
                    "active": bool(active),
                    "config": {
                        "board_id": board_key,
                        "project_key": project_key,
                        "bootstrap_days": 90,
                        "overlap_seconds": 300,
                        "field_mappings": {},
                    },
                    "notes": (
                        "Phase 3 incremental Issue history and Issue Link evidence. "
                        "Connector-local field mappings require explicit local configuration."
                    ),
                }
            )
            imported += 1

        if not merge_only:
            _cleanup_project_key_facts(con)
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()

    print(f"Imported {imported} JIRA board configuration rows.")
    if not merge_only:
        print(f"Removed {removed} stale board configuration(s) and related cache rows.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Import JIRA board configurations from CSV")
    parser.add_argument("--file", required=True, help="Path to jira_board_configs CSV")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--merge-only",
        action="store_true",
        help="Only upsert rows from the CSV; do not delete boards missing from the file.",
    )
    args = parser.parse_args()
    import_jira_boards(Path(args.file), dry_run=args.dry_run, merge_only=args.merge_only)


if __name__ == "__main__":
    main()
