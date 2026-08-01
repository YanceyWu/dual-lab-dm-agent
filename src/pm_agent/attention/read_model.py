"""Capability-owned public reader for persisted Attention current state."""

from __future__ import annotations

import copy
import re
from pathlib import Path
from typing import Any

from pm_agent.attention.rules import ACTIVE_RULE_KEYS, ALL_RULE_KEYS
from pm_agent.database import attention as attention_repository

SUBJECT_KIND_BY_RULE = {
    "project_health_attention": "project",
    "overdue_action_attention": "action",
    "source_freshness_attention": "source",
    "resource_overload_attention": "member",
    "critical_milestone_overdue_attention": "milestone",
    "pending_decision_attention": "decision",
}
DEFAULT_ATTENTION_STATES = ["open", "acknowledged", "snoozed"]
ATTENTION_STATES = ("open", "acknowledged", "snoozed", "resolved")
_STABLE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


def current_attention(
    *,
    attention_states: list[str] | None = None,
    rule_key: str | None = None,
    subject_kind: str | None = None,
    subject_id: str | None = None,
    include_history: bool = False,
    limit: int = 20,
    history_limit: int = 5,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    """Return bounded persisted Attention without evaluating or reconciling."""
    states = (
        list(DEFAULT_ATTENTION_STATES)
        if attention_states is None
        else attention_states
    )
    _validate(
        states,
        rule_key,
        subject_kind,
        subject_id,
        include_history,
        limit,
        history_limit,
    )
    with attention_repository.attention_connection(db_path=db_path) as connection:
        matched = attention_repository.list_center_signals(
            connection,
            attention_states=states,
            rule_key=rule_key,
            subject_kind=subject_kind,
            subject_id=subject_id,
        )
        coverage = reconciliation_coverage(
            attention_repository.list_reconciliations(connection),
            rule_key=rule_key,
            subject_kind=subject_kind,
            subject_id=subject_id,
        )
        items = []
        for signal in matched[:limit]:
            observation = signal["observation"]
            limited = None
            if signal["evaluation_status"] in {"partial", "failed"}:
                limited = attention_repository.get_latest_limited_observation(
                    connection,
                    attention_id=signal["attention_id"],
                )
            association = (
                {
                    "state": "known",
                    "project_id": signal["subject_id"],
                    "basis": "project_subject",
                }
                if signal["subject_kind"] == "project"
                else {
                    "state": "unavailable",
                    "project_id": None,
                    "basis": "association_not_published",
                }
            )
            item = {
                "attention_id": signal["attention_id"],
                "rule_key": signal["rule_key"],
                "rule_version": signal["rule_version"],
                "subject": {
                    "kind": signal["subject_kind"],
                    "id": signal["subject_id"],
                },
                "project_association": association,
                "rule_state": signal["rule_state"],
                "attention_state": signal["attention_state"],
                "evaluation_status": signal["evaluation_status"],
                "severity": signal["severity"],
                "first_seen_at": signal["first_seen_at"],
                "last_seen_at": signal["last_seen_at"],
                "resolved_at": signal["resolved_at"] or None,
                "fact": copy.deepcopy(observation.get("fact", {})),
                "signal": copy.deepcopy(observation.get("signal", {})),
                "evidence": copy.deepcopy(observation.get("evidence", {})),
                "freshness": copy.deepcopy((limited or observation).get("freshness", {})),
            }
            if include_history:
                item["recent_events"] = attention_repository.list_recent_history(
                    connection,
                    attention_id=signal["attention_id"],
                    limit=history_limit,
                )
            items.append(item)
    return {
        "contract_version": "attention-current-read-model-v1",
        "items": items,
        "summary": {
            "matched_count": len(matched),
            "returned_count": len(items),
            "truncated": len(matched) > len(items),
        },
        "reconciliation_coverage": coverage,
    }


def reconciliation_coverage(
    reconciliations: list[dict[str, Any]],
    *,
    rule_key: str | None,
    subject_kind: str | None,
    subject_id: str | None,
) -> dict[str, Any]:
    """Return coverage for the exact requested Attention scope."""
    if not reconciliations:
        return {"status": "absent"}
    for reconciliation in reconciliations:
        if _scope_covers(
            reconciliation["scope"],
            rule_key=rule_key,
            subject_kind=subject_kind,
            subject_id=subject_id,
        ):
            stored_status = reconciliation["status"]
            coverage_status = {
                "success": "complete",
                "partial": "partial",
                "failed": "unavailable",
                "invalid": "unavailable",
            }.get(stored_status, "unavailable")
            warning_codes = list(reconciliation["warning_codes"])
            if coverage_status == "unavailable":
                warning_codes.append(
                    f"ATTENTION_RECONCILIATION_{stored_status.upper()}"
                )
            return {
                "status": coverage_status,
                "reconciliation_id": reconciliation["reconciliation_id"],
                "finished_at": reconciliation["finished_at"],
                "rule_set_version": reconciliation["rule_set_version"],
                "warning_codes": sorted(set(warning_codes)),
            }
    return {"status": "out_of_scope"}


def _scope_covers(
    scope: dict[str, Any],
    *,
    rule_key: str | None,
    subject_kind: str | None,
    subject_id: str | None,
) -> bool:
    query_rules = (
        {rule_key}
        if rule_key
        else {
            key for key, kind in SUBJECT_KIND_BY_RULE.items() if kind == subject_kind
        }
        if subject_kind
        else set(ACTIVE_RULE_KEYS)
    )
    scoped_rules = scope.get("rule_keys")
    covered_rules = set(ACTIVE_RULE_KEYS) if scoped_rules is None else set(scoped_rules)
    if not query_rules <= covered_rules:
        return False
    scoped_kind = scope.get("subject_kind")
    if subject_kind:
        if scoped_kind is not None and scoped_kind != subject_kind:
            return False
    elif scoped_kind is not None:
        return False
    scoped_id = scope.get("subject_id")
    if subject_id:
        if scoped_id is not None and scoped_id != subject_id:
            return False
    elif scoped_id is not None:
        return False
    return True


def _validate(
    states: list[str],
    rule_key: str | None,
    subject_kind: str | None,
    subject_id: str | None,
    include_history: bool,
    limit: int,
    history_limit: int,
) -> None:
    if (
        not isinstance(states, list)
        or not states
        or any(not isinstance(state, str) for state in states)
        or len(states) != len(set(states))
        or not set(states) <= set(ATTENTION_STATES)
    ):
        raise ValueError("ATTENTION_STATES_INVALID")
    if rule_key is not None and (
        not isinstance(rule_key, str) or rule_key not in ALL_RULE_KEYS
    ):
        raise ValueError("ATTENTION_RULE_INVALID")
    if subject_kind is not None and (
        not isinstance(subject_kind, str)
        or subject_kind not in set(SUBJECT_KIND_BY_RULE.values())
    ):
        raise ValueError("ATTENTION_SUBJECT_KIND_INVALID")
    if subject_id is not None and (
        not isinstance(subject_id, str) or not _STABLE_ID.fullmatch(subject_id)
    ):
        raise ValueError("ATTENTION_SUBJECT_ID_INVALID")
    if subject_id and not subject_kind:
        raise ValueError("ATTENTION_SUBJECT_SCOPE_INVALID")
    if rule_key and subject_kind and SUBJECT_KIND_BY_RULE[rule_key] != subject_kind:
        raise ValueError("ATTENTION_SUBJECT_SCOPE_INVALID")
    if not isinstance(include_history, bool):
        raise ValueError("ATTENTION_INCLUDE_HISTORY_INVALID")
    if not isinstance(limit, int) or not 1 <= limit <= 50:
        raise ValueError("ATTENTION_LIMIT_INVALID")
    if not isinstance(history_limit, int) or not 1 <= history_limit <= 50:
        raise ValueError("ATTENTION_HISTORY_LIMIT_INVALID")
