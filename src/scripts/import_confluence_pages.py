#!/usr/bin/env python3
# ruff: noqa: E402
"""Compatibility wrapper for importing Confluence page registry rows from CSV."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from pm_agent.connectors.confluence.page_registry import apply_registry_import
from pm_agent.database.bootstrap import main as init_db


def import_confluence_pages(
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
    print(f"Loaded {result['loaded_rows']} Confluence page rows from {file_path}")
    if dry_run:
        for row in result["dry_run_rows"]:
            print("  DRY", row["board_id"], row["id"], row["page_type"])
        if not merge_only:
            print(
                "  DRY sync-mode: rows absent from the CSV would be removed from "
                "page registry and related snapshots."
            )
        return
    print(f"Imported {result['imported_rows']} Confluence page registry rows.")
    if not merge_only:
        print(
            f"Removed {result['removed_pages']} stale page row(s) and "
            f"{result['removed_boards']} stale board snapshot set(s)."
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Import Confluence page registry from CSV "
            "(deprecated compatibility wrapper awaiting Batch D; "
            "pm onboarding is the supported path)."
        )
    )
    parser.add_argument("--file", required=True, help="Path to confluence_pages CSV")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--merge-only",
        action="store_true",
        help="Only upsert rows from the CSV; do not delete pages/boards missing from the file.",
    )
    args = parser.parse_args()
    import_confluence_pages(Path(args.file), dry_run=args.dry_run, merge_only=args.merge_only)


if __name__ == "__main__":
    main()
