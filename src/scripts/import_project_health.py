#!/usr/bin/env python3
# ruff: noqa: E402
"""Non-interactive synthetic Project Health re-import entrypoint."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pm_agent.database.bootstrap import main as bootstrap
from pm_agent.project_health.service import confirm_reimport, preview_reimport


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--confirm", action="store_true")
    args = parser.parse_args()
    if not args.dry_run and not args.confirm:
        parser.error("choose --dry-run or --confirm")
    payload = json.loads(args.file.read_text(encoding="utf-8"))
    bootstrap(quiet=True)
    preview = preview_reimport(payload)
    result = preview if args.dry_run or preview["status"] == "already_completed" else confirm_reimport(preview["session_id"])
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
