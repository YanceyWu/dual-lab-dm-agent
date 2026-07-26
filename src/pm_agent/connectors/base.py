from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ConnectorValidationResult:
    name: str
    display_name: str
    enabled: bool
    ready: bool
    auth_mode: str
    details: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ConnectorStatusRow:
    name: str
    display_name: str
    enabled: bool
    ready: bool | None
    auth_mode: str
    active_sources: int
    stale_sources: int
    latest_run_at: str
    freshness_summary: str


@dataclass(frozen=True)
class ConnectorProbeResult:
    name: str
    display_name: str
    enabled: bool
    ready: bool
    auth_mode: str
    token_refreshed: bool = False
    warning_codes: list[str] = field(default_factory=list)
    error_codes: list[str] = field(default_factory=list)
