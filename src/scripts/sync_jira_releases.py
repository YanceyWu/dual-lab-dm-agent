"""Thin wrapper for package-native JIRA release sync."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pm_agent.sync.jira.release_sync import main, sync_all

__all__ = ["main", "sync_all"]


if __name__ == "__main__":
    main()
