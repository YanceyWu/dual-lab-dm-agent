#!/usr/bin/env python3
"""Load the committed sample source files into an isolated demo database."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
SAMPLE_ROOT = ROOT / "sample-data"
DEFAULT_DB = SAMPLE_ROOT / "demo" / "sample_pm.db"


def _run(command: list[str], env: dict[str, str]) -> None:
    subprocess.run(command, cwd=ROOT, env=env, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Load committed sample data into a demo DB")
    parser.add_argument(
        "--db",
        default=str(DEFAULT_DB),
        help="Target SQLite DB path for the demo environment",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite the demo DB if it already exists",
    )
    parser.add_argument(
        "--skip-project-profiles",
        action="store_true",
        help="Skip importing the optional project_profiles sample workbook",
    )
    args = parser.parse_args()

    db_path = Path(args.db).resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        if not args.force:
            raise SystemExit(
                f"Demo DB already exists: {db_path}\n"
                "Re-run with --force to recreate it."
            )
        db_path.unlink()

    env = os.environ.copy()
    env["DATABASE_PATH"] = str(db_path)

    commands = [
        [
            sys.executable,
            "scripts/import_from_excel.py",
            "--file",
            str((SAMPLE_ROOT / "excel" / "resource_portal_team_sample.xlsx").resolve()),
        ],
        [
            sys.executable,
            "scripts/import_skills.py",
            "--team-data",
            str((SAMPLE_ROOT / "json" / "team_data.sample.json").resolve()),
            "--skill-data",
            str((SAMPLE_ROOT / "json" / "skillset.sample.json").resolve()),
        ],
        [
            sys.executable,
            "scripts/import_hiref.py",
            "--file",
            str((SAMPLE_ROOT / "excel" / "hiref_status_sample.xlsx").resolve()),
        ],
        [
            sys.executable,
            "scripts/import_cr_csv.py",
            "--file",
            str((SAMPLE_ROOT / "csv" / "servicenow_change_requests.sample.csv").resolve()),
        ],
        [
            sys.executable,
            "scripts/import_jira_boards.py",
            "--file",
            str((SAMPLE_ROOT / "csv" / "jira_board_configs.sample.csv").resolve()),
        ],
        [
            sys.executable,
            "scripts/import_confluence_pages.py",
            "--file",
            str((SAMPLE_ROOT / "csv" / "confluence_pages.sample.csv").resolve()),
        ],
    ]
    if not args.skip_project_profiles:
        commands.append(
            [
                sys.executable,
                "scripts/import_project_profiles.py",
                "--file",
                str((SAMPLE_ROOT / "excel" / "project_profiles_sample.xlsx").resolve()),
            ]
        )

    for command in commands:
        print(f"Running: {' '.join(command[1:])}")
        _run(command, env)

    print()
    print(f"Demo DB ready: {db_path}")
    print("Next steps:")
    print(f"  DATABASE_PATH='{db_path}' python3 -m pm_agent.cli.app workload")
    print(f"  DATABASE_PATH='{db_path}' python3 -m pm_agent.cli.app report")
    print(f"  DATABASE_PATH='{db_path}' python3 -m pm_agent.dashboard")


if __name__ == "__main__":
    main()
