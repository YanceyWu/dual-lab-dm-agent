"""Compatibility facade for Phase 3 execution persistence services."""

from __future__ import annotations

from pm_agent.database.execution_common import (
    FRESHNESS_STATES,
    RULE_VERSION,
    VALUE_STATES,
    connection_scope,
    json_dumps,
    now_utc,
    stable_id,
)
from pm_agent.database.execution_derivation import (
    _board_project,
    _fact,
    _latest_run,
    _legacy_snapshot_input,
    _parse_list,
    _parse_refs,
    _upsert_work_item,
    derive_board,
)
from pm_agent.database.execution_milestones import (
    _milestone_state,
    _validate_milestones,
    _validate_release_references,
    confirm_milestone_import,
    preview_milestone_import,
)

_connection = connection_scope
_json = json_dumps
_now = now_utc
_stable_id = stable_id

__all__ = [
    "FRESHNESS_STATES",
    "RULE_VERSION",
    "VALUE_STATES",
    "_board_project",
    "_connection",
    "_fact",
    "_json",
    "_latest_run",
    "_legacy_snapshot_input",
    "_milestone_state",
    "_now",
    "_parse_list",
    "_parse_refs",
    "_stable_id",
    "_upsert_work_item",
    "_validate_milestones",
    "_validate_release_references",
    "connection_scope",
    "confirm_milestone_import",
    "derive_board",
    "json_dumps",
    "now_utc",
    "preview_milestone_import",
    "stable_id",
]
