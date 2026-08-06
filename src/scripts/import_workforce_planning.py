#!/usr/bin/env python3
# ruff: noqa: E402
"""Non-interactive workforce/project/plan/monthly-allocation clean import."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pm_agent.database.bootstrap import main as bootstrap
from pm_agent.workforce_planning_import.service import confirm_import, preview_import


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Preview or explicitly confirm a versioned workforce/planning clean import "
            "(deprecated compatibility wrapper awaiting Batch D; "
            "pm onboarding is the supported path)."
        )
    )
    parser.add_argument("--file", required=True, type=Path)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--dry-run", action="store_true")
    action.add_argument("--confirm", action="store_true")
    args = parser.parse_args()

    payload = json.loads(args.file.read_text(encoding="utf-8"))
    bootstrap(quiet=True)
    preview = preview_import(payload)
    if args.dry_run or preview["status"] in {"already_completed", "in_progress", "rejected"}:
        result = preview
    else:
        result = confirm_import(preview["session_id"])
    print(json.dumps(result, sort_keys=True))
    if result["status"] == "rejected":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
