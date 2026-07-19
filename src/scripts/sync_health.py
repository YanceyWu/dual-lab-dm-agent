"""Thin wrapper for package-native JIRA health sync."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pm_agent.sync.jira.health_sync import main, run_sync

__all__ = ["main", "run_sync"]


if __name__ == "__main__":
    main()
