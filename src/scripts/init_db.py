"""Thin wrapper for package-native DB bootstrap."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pm_agent.database.bootstrap import main

__all__ = ["main"]


if __name__ == "__main__":
    main()
