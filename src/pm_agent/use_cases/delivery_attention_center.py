"""Read-only projection of persisted Delivery Attention state."""

from __future__ import annotations

import copy
import json
import re
import sqlite3
from hashlib import sha256
from typing import Any

from pm_agent.attention.rules import ACTIVE_RULE_KEYS, ALL_RULE_KEYS
from pm_agent.database import attention as attention_repository
from pm_agent.use_cases.service import (
    IntelligenceFact,
    IntelligenceRecommendation,
    IntelligenceSignal,
    IntelligenceSubject,
    UseCaseRequest,
    UseCaseResult,
    new_execution_metadata,
)

DEFAULT_ATTENTION_STATES = ["open", "acknowledged", "snoozed"]
ATTENTION_STATES = ("open", "acknowledged", "snoozed", "resolved")
RULE_STATES = ("active", "clear", "unknown", "unavailable")
SUBJECT_KIND_BY_RULE = {
    "project_health_attention": "project",
    "overdue_action_attention": "action",
    "source_freshness_attention": "source",
    "resource_overload_attention": "member",
    "pending_decision_attention": "decision",
}
RECOMMENDATION_TYPE_BY_RULE = {
    "project_health_attention": "review_project_health",
    "overdue_action_attention": "follow_up_action",
    "source_freshness_attention": "review_source_freshness",
    "resource_overload_attention": "review_resource_load",
}
_STABLE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


def execute_delivery_attention_center(request: UseCaseRequest) -> UseCaseResult:
    parameters = request.parameters
    try:
        filters = _validated_filters(parameters)
    except ValueError as exc:
        return UseCaseResult(
            status="invalid",
            warnings=[{"code": str(exc)}],
            execution_metadata=new_execution_metadata(request),
        )

    try:
        with attention_repository.attention_connection() as connection:
            matched = attention_repository.list_center_signals(
                connection,
                attention_states=filters["attention_states"],
                rule_key=filters["rule_key"],
                subject_kind=filters["subject_kind"],
                subject_id=filters["subject_id"],
            )
            coverage = _reconciliation_coverage(
                attention_repository.list_reconciliations(connection),
                rule_key=filters["rule_key"],
                subject_kind=filters["subject_kind"],
                subject_id=filters["subject_id"],
            )
            selected = matched[: filters["limit"]]
            return _build_result(
                request,
                connection=connection,
                matched=matched,
                selected=selected,
                filters=filters,
                coverage=coverage,
            )
    except (json.JSONDecodeError, KeyError, TypeError, ValueError, sqlite3.Error):
        return UseCaseResult(
            status="failed",
            warnings=[{"code": "DATA_ACCESS_FAILED"}],
            execution_metadata=new_execution_metadata(request),
        )


def _validated_filters(parameters: dict[str, Any]) -> dict[str, Any]:
    states = parameters.get("attention_states", list(DEFAULT_ATTENTION_STATES))
    if (
        not isinstance(states, list)
        or not states
        or len(states) != len(set(states))
        or any(
            not isinstance(state, str) or state not in ATTENTION_STATES
            for state in states
        )
    ):
        raise ValueError("ATTENTION_STATES_INVALID")

    rule_key = _optional_id(parameters.get("rule_key"), "ATTENTION_RULE_INVALID")
    subject_kind = _optional_id(
        parameters.get("subject_kind"),
        "ATTENTION_SUBJECT_KIND_INVALID",
    )
    subject_id = _optional_id(
        parameters.get("subject_id"),
        "ATTENTION_SUBJECT_ID_INVALID",
    )
    if rule_key and rule_key not in ALL_RULE_KEYS:
        raise ValueError("ATTENTION_RULE_INVALID")
    if subject_kind and subject_kind not in set(SUBJECT_KIND_BY_RULE.values()):
        raise ValueError("ATTENTION_SUBJECT_KIND_INVALID")
    if subject_id and not subject_kind:
        raise ValueError("ATTENTION_SUBJECT_SCOPE_INVALID")
    if (
        rule_key
        and subject_kind
        and SUBJECT_KIND_BY_RULE[rule_key] != subject_kind
    ):
        raise ValueError("ATTENTION_SUBJECT_SCOPE_INVALID")

    return {
        "attention_states": list(states),
        "rule_key": rule_key,
        "subject_kind": subject_kind,
        "subject_id": subject_id,
        "include_history": parameters.get("include_history", False),
        "limit": parameters.get("limit", 20),
        "history_limit": parameters.get("history_limit", 5),
    }


def _build_result(
    request: UseCaseRequest,
    *,
    connection,
    matched: list[dict[str, Any]],
    selected: list[dict[str, Any]],
    filters: dict[str, Any],
    coverage: dict[str, Any],
) -> UseCaseResult:
    facts: list[IntelligenceFact] = []
    signals: list[IntelligenceSignal] = []
    recommendations: list[IntelligenceRecommendation] = []
    evidence: list[dict[str, Any]] = []
    freshness: list[dict[str, Any]] = []
    items: list[dict[str, Any]] = []

    for signal in selected:
        projection = _project_signal(signal)
        facts.append(projection["fact"])
        signals.append(projection["signal"])
        recommendations.append(projection["recommendation"])
        evidence.append(projection["evidence"])
        freshness.append(projection["freshness"])
        item = projection["item"]
        if filters["include_history"]:
            item["recent_events"] = attention_repository.list_recent_history(
                connection,
                attention_id=signal["attention_id"],
                limit=filters["history_limit"],
            )
        items.append(item)

    summary = _summary(matched, len(selected))
    projection = {
        "items": items,
        "summary": summary,
        "reconciliation_coverage": coverage,
    }
    warning_codes = []
    if coverage["status"] == "absent":
        warning_codes.append("ATTENTION_NOT_RECONCILED")
    elif coverage["status"] == "out_of_scope":
        warning_codes.append("ATTENTION_SCOPE_NOT_RECONCILED")
    elif coverage["status"] == "partial":
        warning_codes.extend(coverage.get("warning_codes", []))

    return UseCaseResult(
        status="success",
        data=projection,
        context=copy.deepcopy(projection),
        evidence=evidence,
        freshness=freshness,
        facts=facts,
        signals=signals,
        recommendations=recommendations,
        warnings=sorted(set(warning_codes)),
        execution_metadata=new_execution_metadata(request),
    )


def _project_signal(signal: dict[str, Any]) -> dict[str, Any]:
    attention_id = signal["attention_id"]
    observation = signal["observation"]
    subject = IntelligenceSubject(
        kind=signal["subject_kind"],
        id=signal["subject_id"],
    )
    fact_id = _local_id("fact", attention_id)
    signal_id = _local_id("signal", attention_id)
    recommendation_id = _local_id("recommendation", attention_id)
    evidence_id = _local_id("evidence", attention_id)
    freshness_id = _local_id("freshness", attention_id)
    fact_payload = observation["fact"]
    signal_payload = observation["signal"]
    freshness_state = _freshness_state(observation.get("freshness", {}))

    fact = IntelligenceFact(
        fact_id=fact_id,
        fact_type=fact_payload["fact_type"],
        fact_kind="derived",
        subject=subject,
        value=fact_payload.get("value"),
        value_state=fact_payload["value_state"],
        observed_at=_observed_at(observation, signal),
        freshness_refs=[freshness_id],
        evidence_refs=[evidence_id],
        rule_version=signal["rule_version"],
    )
    intelligence_signal = IntelligenceSignal(
        signal_id=signal_id,
        signal_type=signal["rule_key"],
        subject=subject,
        state=signal["rule_state"],
        severity="info" if signal["severity"] == "none" else signal["severity"],
        reason_codes=list(signal_payload.get("reason_codes", [])),
        fact_refs=[fact_id],
        evidence_refs=[evidence_id],
        rule_version=signal["rule_version"],
    )
    recommendation_state, rationale_codes = _recommendation_state(
        signal,
        freshness_state=freshness_state,
    )
    recommendation = IntelligenceRecommendation(
        recommendation_id=recommendation_id,
        recommendation_type=RECOMMENDATION_TYPE_BY_RULE.get(
            signal["rule_key"],
            "review_attention_item",
        ),
        subject=subject,
        state=recommendation_state,
        rationale_codes=rationale_codes,
        signal_refs=[signal_id],
        evidence_refs=[evidence_id],
        write_mode="advisory",
        confirmation_required=False,
    )
    evidence = {
        "evidence_id": evidence_id,
        "source_kind": "local_sqlite",
        "entity_kind": observation.get("evidence", {}).get(
            "entity_kind",
            "attention_observation",
        ),
        "record_count": _record_count(observation.get("evidence", {})),
        "applied_filters": {
            "attention_id": attention_id,
            "rule_key": signal["rule_key"],
            "subject_kind": signal["subject_kind"],
            "subject_id": signal["subject_id"],
        },
        "normalized_details": observation.get("evidence", {}),
    }
    freshness = {
        "source_id": freshness_id,
        "state": freshness_state,
        "observed_at": _observed_at(observation, signal),
        "source_ids": _source_ids(observation.get("freshness", {})),
    }
    item = {
        "attention_id": attention_id,
        "rule_key": signal["rule_key"],
        "rule_version": signal["rule_version"],
        "subject": {
            "kind": signal["subject_kind"],
            "id": signal["subject_id"],
        },
        "rule_state": signal["rule_state"],
        "attention_state": signal["attention_state"],
        "evaluation_status": signal["evaluation_status"],
        "severity": signal["severity"],
        "first_seen_at": signal["first_seen_at"],
        "last_seen_at": signal["last_seen_at"],
        "latest_reconciliation_id": signal["last_reconciliation_id"],
        "acknowledged_at": signal["acknowledged_at"] or None,
        "snoozed_until": signal["snoozed_until"] or None,
        "resolved_at": signal["resolved_at"] or None,
        "fact_ref": fact_id,
        "signal_ref": signal_id,
        "recommendation_ref": recommendation_id,
        "evidence_refs": [evidence_id],
        "freshness_refs": [freshness_id],
    }
    return {
        "fact": fact,
        "signal": intelligence_signal,
        "recommendation": recommendation,
        "evidence": evidence,
        "freshness": freshness,
        "item": item,
    }


def _recommendation_state(
    signal: dict[str, Any],
    *,
    freshness_state: str,
) -> tuple[str, list[str]]:
    if signal["rule_state"] != "active" or signal["attention_state"] == "resolved":
        return "not_applicable", ["attention_not_active"]
    if signal["evaluation_status"] == "disabled":
        return "blocked", ["rule_disabled"]
    if signal["rule_key"] == "source_freshness_attention":
        return "available", ["normalized_source_limitation_review"]
    if signal["evaluation_status"] != "complete" or freshness_state != "fresh":
        return "blocked", ["retained_evidence_unusable"]
    return "available", ["attention_review_advised"]


def _reconciliation_coverage(
    reconciliations: list[dict[str, Any]],
    *,
    rule_key: str | None,
    subject_kind: str | None,
    subject_id: str | None,
) -> dict[str, Any]:
    if not reconciliations:
        return {"status": "absent"}
    for reconciliation in reconciliations:
        if _scope_covers(
            reconciliation["scope"],
            rule_key=rule_key,
            subject_kind=subject_kind,
            subject_id=subject_id,
        ):
            return {
                "status": (
                    "partial"
                    if reconciliation["status"] == "partial"
                    else "complete"
                ),
                "reconciliation_id": reconciliation["reconciliation_id"],
                "finished_at": reconciliation["finished_at"],
                "rule_set_version": reconciliation["rule_set_version"],
                "warning_codes": reconciliation["warning_codes"],
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
            key
            for key, kind in SUBJECT_KIND_BY_RULE.items()
            if kind == subject_kind
        }
        if subject_kind
        else set(ACTIVE_RULE_KEYS)
    )
    scoped_rules = scope.get("rule_keys")
    covered_rules = (
        set(ACTIVE_RULE_KEYS)
        if scoped_rules is None
        else set(scoped_rules)
    )
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


def _summary(matched: list[dict[str, Any]], returned_count: int) -> dict[str, Any]:
    return {
        "matched_count": len(matched),
        "returned_count": returned_count,
        "truncated": len(matched) > returned_count,
        "by_rule_key": {
            key: sum(item["rule_key"] == key for item in matched)
            for key in ALL_RULE_KEYS
        },
        "by_rule_state": {
            state: sum(item["rule_state"] == state for item in matched)
            for state in RULE_STATES
        },
        "by_attention_state": {
            state: sum(item["attention_state"] == state for item in matched)
            for state in ATTENTION_STATES
        },
    }


def _freshness_state(payload: dict[str, Any]) -> str:
    if payload.get("basis") == "local_record":
        return "fresh"
    states = list(payload.get("states", {}).values())
    if not states and payload.get("state"):
        states = [payload["state"]]
    for candidate in ("unavailable", "unknown", "partial", "stale"):
        if candidate in states:
            return candidate
    return "fresh" if states and all(state == "fresh" for state in states) else "unknown"


def _source_ids(payload: dict[str, Any]) -> list[str]:
    values = payload.get("source_ids")
    if isinstance(values, list):
        return [str(value) for value in values]
    value = payload.get("source_id")
    return [str(value)] if value else []


def _observed_at(observation: dict[str, Any], signal: dict[str, Any]) -> str:
    return str(observation.get("freshness", {}).get("observed_at") or signal["last_seen_at"])


def _record_count(payload: dict[str, Any]) -> int:
    if isinstance(payload.get("record_count"), int):
        return payload["record_count"]
    if isinstance(payload.get("snapshot_ids"), list):
        return len(payload["snapshot_ids"])
    return 1


def _local_id(prefix: str, attention_id: str) -> str:
    candidate = f"{prefix}:{attention_id}"
    if len(candidate) <= 128:
        return candidate
    digest = sha256(candidate.encode("utf-8")).hexdigest()[:16]
    return f"{candidate[:111]}:{digest}"


def _optional_id(value: Any, code: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not _STABLE_ID.fullmatch(value.strip()):
        raise ValueError(code)
    return value.strip()
