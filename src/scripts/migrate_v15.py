"""
scripts/migrate_v15.py — Legacy v1.5 migration entrypoint.

What it does:
1. Calls init_db()
2. Applies any idempotent schema/data migrations implemented there
3. Prints a verification summary

Usage:
    python3 scripts/migrate_v15.py
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pm_agent.database.bootstrap import main as init_db
from pm_agent.config import settings


def migrate() -> None:
    print("Running legacy v1.5 migration entrypoint...")
    init_db()

    con = sqlite3.connect(settings.database_path)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")

    summary = {
        "employees": con.execute("SELECT COUNT(*) FROM employees").fetchone()[0],
        "projects": con.execute("SELECT COUNT(*) FROM projects").fetchone()[0],
        "employee_external_ids": con.execute("SELECT COUNT(*) FROM employee_external_ids").fetchone()[0],
        "plan_versions": con.execute("SELECT COUNT(*) FROM plan_versions").fetchone()[0],
        "monthly_allocations": con.execute("SELECT COUNT(*) FROM monthly_allocations").fetchone()[0],
        "monthly_allocations_with_version": con.execute(
            "SELECT COUNT(*) FROM monthly_allocations WHERE COALESCE(plan_version_id, '') != ''"
        ).fetchone()[0],
    }

    print("Migration summary:")
    for key, value in summary.items():
        print(f"  - {key}: {value}")

    print("\nPlan versions:")
    for row in con.execute(
        """
        SELECT plan_version_id, version_name, scenario_type, as_of_date, version_status
        FROM plan_versions
        ORDER BY
            CASE version_status WHEN 'active' THEN 0 WHEN 'draft' THEN 1 ELSE 2 END,
            CASE scenario_type WHEN 'forecast' THEN 0 WHEN 'baseline' THEN 1 ELSE 2 END,
            COALESCE(as_of_date, '') DESC
        """
    ).fetchall():
        print(
            f"  - {row['plan_version_id']}: {row['version_name']} "
            f"[{row['scenario_type']}, {row['version_status']}] as_of={row['as_of_date']}"
        )

    print("\nSample employee_external_ids:")
    for row in con.execute(
        """
        SELECT employee_id, system_name, id_type, external_id, external_name
        FROM employee_external_ids
        ORDER BY employee_id, system_name
        LIMIT 12
        """
    ).fetchall():
        print(
            f"  - {row['employee_id']} | {row['system_name']} | {row['id_type']} "
            f"| {row['external_id']} | {row['external_name']}"
        )

    con.close()
    print("\n✅ migration completed.")


if __name__ == "__main__":
    migrate()
