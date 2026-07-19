# ruff: noqa: E402
from __future__ import annotations

import socket
import sys
from pathlib import Path
from typing import Iterator

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pm_agent.config import settings


@pytest.fixture(autouse=True)
def protect_private_runtime_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[Path]:
    """Keep every test away from the default operational database and network."""
    operational_path = Path(settings.database_path).resolve()
    safe_path = (tmp_path / "default-test.db").resolve()
    monkeypatch.setattr(settings, "database_path", str(safe_path))

    def deny_network(*_args, **_kwargs):
        raise AssertionError("Live network access is disabled in the default test suite")

    monkeypatch.setattr(socket.socket, "connect", deny_network)
    yield safe_path

    selected_path = Path(settings.database_path).resolve()
    assert selected_path != operational_path
    assert selected_path == safe_path or tmp_path.resolve() in selected_path.parents


@pytest.fixture
def isolated_db(
    protect_private_runtime_state: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    db_path = protect_private_runtime_state.with_name("pm.db")
    monkeypatch.setattr(settings, "database_path", str(db_path))
    return db_path
