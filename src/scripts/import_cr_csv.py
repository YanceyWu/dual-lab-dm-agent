"""Deprecated compatibility wrapper for the retained ServiceNow CR CSV import."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pm_agent.sync.servicenow.cr_import import import_cr, load_csv, main

__all__ = ["import_cr", "load_csv", "main"]


if __name__ == "__main__":
    main()
