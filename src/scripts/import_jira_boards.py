#!/usr/bin/env python3
# ruff: noqa: E402
"""Compatibility wrapper for importing JIRA board configuration rows from CSV."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from pm_agent.database.bootstrap import main as init_db
from pm_agent.connectors.jira.board_registry import apply_registry_import


def import_jira_boards(
    file_path: Path,
    dry_run: bool = False,
    merge_only: bool = False,
) -> None:
    init_db()
    result = apply_registry_import(
        file_path,
        dry_run=dry_run,
        merge_only=merge_only,
    )
    print(f"Loaded {result['loaded_rows']} JIRA board rows from {file_path}")
    if dry_run:
        for row in result["dry_run_rows"]:
            print("  DRY", row["id"], row["project_key"], row["version_name_pattern"])
        if not merge_only:
            print(
                "  DRY sync-mode: rows absent from the CSV would be removed from "
                "board configs and JIRA caches."
            )
        return
    print(f"Imported {result['imported_rows']} JIRA board configuration rows.")
    if not merge_only:
        print(
            f"Removed {result['removed_rows']} stale board configuration(s) "
            "and related cache rows."
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Import JIRA board configurations from CSV "
            "(deprecated compatibility wrapper awaiting Batch D; "
            "pm onboarding is the supported path)."
        )
    )
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
