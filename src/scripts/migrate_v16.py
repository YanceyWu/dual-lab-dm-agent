"""
scripts/migrate_v16.py — Apply the v1.6 Workday-canonical identity migration.

What it does:
1. Ensures the v1.6 schema exists via init_db()
2. Migrates employees.id to canonical Workday IDs
3. Splits HIREF-only rows into staffing_placeholders
4. Cleans employee_external_ids to keep non-canonical mappings only
5. Prints a verification summary

Usage:
    python3 scripts/migrate_v16.py
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pm_agent.database.bootstrap import main as init_db
from pm_agent.config import settings


def migrate() -> None:
    print("Running v1.6 migration...")
    init_db()

    con = sqlite3.connect(settings.database_path)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")

    summary = {
        "employees": con.execute("SELECT COUNT(*) FROM employees").fetchone()[0],
        "active_employees": con.execute(
            "SELECT COUNT(*) FROM employees WHERE status = 'active'"
        ).fetchone()[0],
        "staffing_placeholders": con.execute(
            "SELECT COUNT(*) FROM staffing_placeholders"
        ).fetchone()[0],
        "employee_external_ids": con.execute(
            "SELECT COUNT(*) FROM employee_external_ids"
        ).fetchone()[0],
        "plan_versions": con.execute("SELECT COUNT(*) FROM plan_versions").fetchone()[0],
        "monthly_allocations": con.execute("SELECT COUNT(*) FROM monthly_allocations").fetchone()[0],
        "placeholder_monthly_allocations": con.execute(
            "SELECT COUNT(*) FROM placeholder_monthly_allocations"
        ).fetchone()[0],
    }

    print("Migration summary:")
    for key, value in summary.items():
        print(f"  - {key}: {value}")

    print("\nExternal ID counts:")
    for row in con.execute(
        """
        SELECT system_name, id_type, COUNT(*) AS cnt
        FROM employee_external_ids
        GROUP BY system_name, id_type
        ORDER BY system_name, id_type
        """
    ).fetchall():
        print(f"  - {row['system_name']} | {row['id_type']} | {row['cnt']}")

    print("\nSample employees:")
    for row in con.execute(
        """
        SELECT id, wd_id, name, resource_type, status
        FROM employees
        ORDER BY id
        LIMIT 8
        """
    ).fetchall():
        print(
            f"  - {row['id']} | wd_id={row['wd_id']} | {row['name']} "
            f"| {row['resource_type'] or '-'} | {row['status']}"
        )

    print("\nSample staffing_placeholders:")
    for row in con.execute(
        """
        SELECT placeholder_id, display_name, hiref_id, source_employee_id, status
        FROM staffing_placeholders
        ORDER BY placeholder_id
        LIMIT 8
        """
    ).fetchall():
        print(
            f"  - {row['placeholder_id']} | {row['display_name']} | "
            f"hiref={row['hiref_id'] or '-'} | source={row['source_employee_id'] or '-'} | {row['status']}"
        )

    con.close()
    print("\n✅ v1.6 migration completed.")


if __name__ == "__main__":
    migrate()
