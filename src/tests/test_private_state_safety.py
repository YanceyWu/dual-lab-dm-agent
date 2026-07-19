from __future__ import annotations

from pathlib import Path

from pm_agent.config import settings


def test_default_test_database_is_isolated(
    protect_private_runtime_state: Path,
) -> None:
    selected = Path(settings.database_path).resolve()
    assert selected == protect_private_runtime_state
    assert selected.name == "default-test.db"
    assert "data/pm.db" not in selected.as_posix()
