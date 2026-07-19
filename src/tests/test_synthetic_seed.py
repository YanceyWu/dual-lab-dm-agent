from __future__ import annotations

import sqlite3
from pathlib import Path

from pm_agent.config import settings
from scripts import seed


def test_synthetic_seed_builds_a_clean_local_dataset(
    isolated_db: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "database_path", str(isolated_db))

    seed.main()

    with sqlite3.connect(isolated_db) as connection:
        counts = {
            table: connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
            for table in ("employees", "projects", "assignments")
        }
        names = {
            row[0] for row in connection.execute("SELECT name FROM employees").fetchall()
        }

    assert counts == {"employees": 4, "projects": 3, "assignments": 4}
    assert names == {
        "Alex Example",
        "Blair Example",
        "Casey Example",
        "Drew Example",
    }
