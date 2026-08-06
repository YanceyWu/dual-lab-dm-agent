#!/usr/bin/env python3
# ruff: noqa: E402
"""Preview or confirm Team/Project + Capacity workbook onboarding v1."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pm_agent.database.bootstrap import main as bootstrap
from pm_agent.workbook_onboarding.service import (
    import_workbook,
    preview_workbook_import,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Preview or confirm Team/Project + Capacity workbook onboarding v1 "
            "(deprecated compatibility wrapper awaiting Batch D; "
            "pm onboarding is the supported path)."
        )
    )
    parser.add_argument("--file", required=True, type=Path)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--dry-run", action="store_true")
    action.add_argument("--confirm", action="store_true")
    args = parser.parse_args()

    bootstrap(quiet=True)
    if args.dry_run:
        result = preview_workbook_import(args.file)
    else:
        result = import_workbook(args.file)
    print(json.dumps(result, sort_keys=True))
    if result["status"] in {"rejected", "partially_completed"}:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
