"""Shared deterministic helpers for Phase 3 execution storage."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from pm_agent.config import settings

RULE_VERSION = "execution-foundation-v1"
VALUE_STATES = {"known", "unknown", "unavailable", "conflicting"}
FRESHNESS_STATES = {"fresh", "stale", "partial", "failed", "never_observed"}


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def stable_id(prefix: str, *parts: str) -> str:
    payload = json.dumps(parts, ensure_ascii=True, separators=(",", ":"))
    return f"{prefix}-{hashlib.sha256(payload.encode()).hexdigest()[:24]}"


def json_dumps(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


@contextmanager
def connection_scope(db_path: str | Path | None = None) -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(Path(db_path or settings.database_path), isolation_level=None)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 10000")
    try:
        yield connection
    finally:
        connection.close()
