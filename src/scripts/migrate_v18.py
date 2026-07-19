"""
scripts/migrate_v18.py — Apply the v1.8 project snapshot redesign.

What it does:
1. Ensures the latest schema exists via init_db()
2. Migrates legacy project_plan_snapshots rows into project_snapshots
3. Prints a verification summary for the new snapshot model

Usage:
    python3 scripts/migrate_v18.py
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pm_agent.database.bootstrap import main as init_db
from pm_agent.config import settings


def migrate() -> None:
    print("Running v1.8 migration...")
    init_db()

    con = sqlite3.connect(settings.database_path)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")

    summary = {
        "project_snapshots": con.execute(
            "SELECT COUNT(*) FROM project_snapshots"
        ).fetchone()[0],
        "project_plan_snapshots_view": con.execute(
            "SELECT COUNT(*) FROM project_plan_snapshots"
        ).fetchone()[0],
    }

    print("Migration summary:")
    for key, value in summary.items():
        print(f"  - {key}: {value}")

    print("\nSample project snapshots:")
    for row in con.execute(
        """
        SELECT id, project_id, snapshot_date, artifact_kind, horizon,
               artifact_state, health, generation_mode
        FROM project_snapshots
        ORDER BY snapshot_date DESC, created_at DESC
        LIMIT 8
        """
    ).fetchall():
        print(
            f"  - {row['id']} | {row['project_id']} | {row['snapshot_date']} | "
            f"{row['artifact_kind']} | {row['horizon']} | {row['artifact_state']} | "
            f"{row['health']} | mode={row['generation_mode']}"
        )

    print("\nSample project-plans compatibility view:")
    for row in con.execute(
        """
        SELECT id, project_id, plan_type, as_of_date, status
        FROM project_plan_snapshots
        ORDER BY as_of_date DESC, created_at DESC
        LIMIT 5
        """
    ).fetchall():
        print(
            f"  - {row['id']} | {row['project_id']} | {row['plan_type']} | "
            f"{row['as_of_date']} | {row['status']}"
        )

    con.close()
    print("\n✅ v1.8 migration completed.")


if __name__ == "__main__":
    migrate()
