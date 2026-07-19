"""
scripts/migrate_v17.py — Apply the v1.7 PM framework migration.

What it does:
1. Ensures the v1.7 schema exists via init_db()
2. Seeds explicit use_cases and data_sources
3. Prints a verification summary for the new framework tables

Usage:
    python3 scripts/migrate_v17.py
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pm_agent.database.bootstrap import main as init_db
from pm_agent.config import settings


def migrate() -> None:
    print("Running v1.7 migration...")
    init_db()

    con = sqlite3.connect(settings.database_path)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")

    summary = {
        "use_cases": con.execute("SELECT COUNT(*) FROM use_cases").fetchone()[0],
        "data_sources": con.execute("SELECT COUNT(*) FROM data_sources").fetchone()[0],
        "sync_runs": con.execute("SELECT COUNT(*) FROM sync_runs").fetchone()[0],
        "project_plan_snapshots": con.execute(
            "SELECT COUNT(*) FROM project_plan_snapshots"
        ).fetchone()[0],
    }

    print("Migration summary:")
    for key, value in summary.items():
        print(f"  - {key}: {value}")

    print("\nSample use_cases:")
    for row in con.execute(
        """
        SELECT id, name, use_case_type, decision_type, priority, status
        FROM use_cases
        ORDER BY priority, id
        LIMIT 8
        """
    ).fetchall():
        print(
            f"  - {row['id']} | {row['name']} | {row['use_case_type']} | "
            f"{row['decision_type']} | P{row['priority']} | {row['status']}"
        )

    print("\nSample data_sources:")
    for row in con.execute(
        """
        SELECT id, source_type, source_name, ingestion_mode, refresh_sla_hours, active
        FROM data_sources
        ORDER BY source_type, id
        LIMIT 12
        """
    ).fetchall():
        print(
            f"  - {row['id']} | {row['source_type']} | {row['ingestion_mode']} | "
            f"SLA={row['refresh_sla_hours']}h | active={row['active']}"
        )

    print("\nLatest sync_runs:")
    for row in con.execute(
        """
        SELECT id, source_id, status, started_at, finished_at, rows_changed
        FROM sync_runs
        ORDER BY
            CASE
                WHEN COALESCE(finished_at, '') != '' THEN finished_at
                ELSE started_at
            END DESC,
            started_at DESC
        LIMIT 8
        """
    ).fetchall():
        print(
            f"  - {row['id']} | {row['source_id']} | {row['status']} | "
            f"{row['started_at']} -> {row['finished_at'] or '-'} | changed={row['rows_changed']}"
        )

    con.close()
    print("\n✅ v1.7 migration completed.")


if __name__ == "__main__":
    migrate()
