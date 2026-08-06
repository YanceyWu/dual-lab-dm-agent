#!/usr/bin/env python3
# ruff: noqa: E402
"""Non-interactive synthetic canonical Milestone clean import."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pm_agent.database.bootstrap import main as bootstrap
from pm_agent.database.execution import (
    confirm_milestone_import,
    preview_milestone_import,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Preview or explicitly confirm canonical Milestone import "
            "(deprecated compatibility wrapper awaiting Batch D; "
            "pm onboarding is the supported path)."
        )
    )
    parser.add_argument("--file", required=True, type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--confirm", action="store_true")
    args = parser.parse_args()
    if not args.dry_run and not args.confirm:
        parser.error("choose --dry-run or --confirm")
    payload = json.loads(args.file.read_text(encoding="utf-8"))
    bootstrap(quiet=True)
    preview = preview_milestone_import(payload)
    if args.dry_run or preview["status"] == "no_op":
        print(json.dumps(preview, sort_keys=True))
        return
    confirmed = confirm_milestone_import(
        preview["operation_id"],
        preview["confirmation_token"],
    )
    print(json.dumps(confirmed, sort_keys=True))


if __name__ == "__main__":
    main()
