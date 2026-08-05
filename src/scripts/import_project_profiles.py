#!/usr/bin/env python3
# ruff: noqa: E402
"""
Compatibility wrapper for importing project profiles from the workbook template.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from pm_agent.config import get_database_path
from pm_agent.project_profile_import import (
    apply_project_profile_import,
    preview_project_profile_import,
)

DEFAULT_FILE = ROOT / "data-feed" / "Project_Profiles_Template.xlsx"
__all__ = ["DEFAULT_FILE", "get_database_path", "main"]


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Import project profiles from workbook "
            "(compatibility wrapper; pm onboarding is the supported path)."
        )
    )
    parser.add_argument("--file", default=str(DEFAULT_FILE))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    db_path = get_database_path()
    workbook_path = Path(args.file)
    preview = preview_project_profile_import(workbook_path, db_path=db_path)
    for row in preview["payload"].get("preview_rows", []):
        action = str(row.get("action"))
        label = str(row.get("project_name") or row.get("project_id") or "")
        if action == "skipped":
            print(f"  SKIP  {label} — phase not filled")
        elif action == "error":
            print(f"  ERROR {row.get('project_id')} — not found in DB")
        else:
            prefix = "DRY " if args.dry_run else ""
            print(f"  {prefix}UPDATE  {label}")
            print(
                "         "
                f"phase={row.get('phase')} | priority={row.get('priority_tier')} | "
                f"focus={row.get('is_focus')}"
            )
    if args.dry_run:
        counts = preview["counts"]
        print(
            "\nDone.  Updated: "
            f"{counts['actionable_profiles']}  "
            f"Skipped: {counts['skipped_phase_rows']}  "
            f"Errors: {counts['missing_project_rows']}"
        )
        return

    result = apply_project_profile_import(workbook_path, db_path=db_path)
    counts = result["counts"]
    print(
        "\nDone.  Updated: "
        f"{counts['actionable_profiles']}  "
        f"Skipped: {counts['skipped_phase_rows']}  "
        f"Errors: {counts['missing_project_rows']}"
    )
    print("Run: python3 -m pm_agent.cli.app report  to verify")

if __name__ == "__main__":
    main()
