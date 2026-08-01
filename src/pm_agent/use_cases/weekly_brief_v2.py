"""Opt-in shared read interface for the B3 Weekly Brief v2 composer."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from pm_agent.use_cases.service import (
    IntelligenceFact,
    IntelligenceRecommendation,
    IntelligenceSignal,
    IntelligenceSubject,
    UseCaseRequest,
    UseCaseResult,
    new_execution_metadata,
)
from pm_agent.weekly_brief.composer import compose_weekly_brief_v2

_SUBJECT_KIND_BY_PRODUCER = {
    "project_health": "project",
    "resource_intelligence": "project",
    "attention": "attention",
    "action": "action",
}


def execute_weekly_dm_brief_v2(request: UseCaseRequest) -> UseCaseResult:
    """Compose v2 read-only; capture remains a dedicated controlled operation."""
    try:
        params = _parameters(request.parameters)
        composed = compose_weekly_brief_v2(**params)
        statements_by_id = {
            item["statement_id"]: item for item in composed.get("statements", [])
        }
        evidence, freshness = _references(composed)
        return UseCaseResult(
            contract_version="2.0",
            status="success",
            data=composed,
            facts=[
                _fact(item, statements_by_id.get(item.get("statement_id")))
                for item in composed["facts"]
            ],
            signals=[
                _signal(item, statements_by_id.get(item.get("statement_id")))
                for item in composed["signals"]
            ],
            recommendations=[
                _recommendation(
                    item, statements_by_id.get(item.get("statement_id"))
                )
                for item in composed["recommendations"]
            ],
            evidence=evidence,
            freshness=freshness,
            warnings=sorted({code for section in composed["sections"].values() for code in section["limitations"]}),
            context={"context_version": "2.0", "context_type": "weekly_dm_brief_v2", "snapshot": composed["snapshot"]},
            execution_metadata=new_execution_metadata(request),
        )
    except ValueError as exc:
        return UseCaseResult(status="invalid", warnings=[{"code": str(exc)}], execution_metadata=new_execution_metadata(request))


def _parameters(value: dict[str, Any]) -> dict[str, Any]:
    allowed = {"project_ids", "plan_version_id", "attention_limit", "baseline_snapshot_id"}
    if set(value) - allowed:
        raise ValueError("WEEKLY_BRIEF_V2_PARAMETER_INVALID")
    project_ids = value.get("project_ids")
    if project_ids is not None and (not isinstance(project_ids, list) or any(not isinstance(item, str) for item in project_ids)):
        raise ValueError("WEEKLY_BRIEF_V2_PROJECT_IDS_INVALID")
    return {key: value[key] for key in allowed & set(value)}


def _references(composed: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    evidence = {ref["evidence_id"]: {"evidence_id": ref["evidence_id"], "producer": ref["producer"], "source_id": ref["source_id"]} for collection in (composed["facts"], composed["signals"], composed["recommendations"]) for item in collection for ref in item.get("evidence_refs", [])}
    freshness = {}
    for ref in (entry for collection in (composed["facts"], composed["signals"], composed["recommendations"]) for item in collection for entry in item.get("freshness_refs", [])):
        if not isinstance(ref, dict):
            continue
        encoded = json.dumps(ref, sort_keys=True, separators=(",", ":"))
        source_id = "weekly-brief-freshness-" + hashlib.sha256(encoded.encode()).hexdigest()[:20]
        freshness[source_id] = {"source_id": source_id, **ref}
    return list(evidence.values()), list(freshness.values())


def _subject_kind(statement: dict[str, Any] | None, producer: str, fallback: str) -> str:
    if statement is not None:
        return statement.get("subject_kind") or fallback
    return _SUBJECT_KIND_BY_PRODUCER.get(producer, fallback)


def _fact(item: dict[str, Any], statement: dict[str, Any] | None) -> IntelligenceFact:
    value = {"statement_id": item.get("statement_id")}
    value_state = item.get("value_state", "unknown")
    if value_state not in {"known", "unknown", "unavailable", "conflicting"}:
        value["state"] = value_state
        value_state = "known"
    return IntelligenceFact(
        fact_id=item["fact_id"],
        fact_type=f"weekly_brief_{item['producer']}",
        fact_kind="derived",
        subject=IntelligenceSubject(
            kind=_subject_kind(statement, item["producer"], "execution"),
            id=item["subject_id"],
        ),
        value=value,
        value_state=value_state,
        evidence_refs=[ref["evidence_id"] for ref in item["evidence_refs"]],
        rule_version="weekly-brief-v2",
    )


def _signal(item: dict[str, Any], statement: dict[str, Any] | None) -> IntelligenceSignal:
    return IntelligenceSignal(
        signal_id=item["signal_id"],
        signal_type=f"weekly_brief_{item['producer']}",
        subject=IntelligenceSubject(
            kind=_subject_kind(statement, item["producer"], "attention"),
            id=item["subject_id"],
        ),
        state="active",
        severity=(
            item["severity"]
            if item["severity"] in {"critical", "high", "medium", "low", "info"}
            else "unknown"
        ),
        reason_codes=[],
        fact_refs=[],
        evidence_refs=[ref["evidence_id"] for ref in item["evidence_refs"]],
        rule_version="weekly-brief-v2",
    )


def _recommendation(
    item: dict[str, Any], statement: dict[str, Any] | None
) -> IntelligenceRecommendation:
    return IntelligenceRecommendation(
        recommendation_id=item["recommendation_id"],
        recommendation_type="weekly_brief_action_follow_up",
        subject=IntelligenceSubject(
            kind=_subject_kind(statement, item["producer"], "action"),
            id=item["subject_id"],
        ),
        state="available",
        rationale_codes=[],
        signal_refs=[],
        evidence_refs=[ref["evidence_id"] for ref in item["evidence_refs"]],
        write_mode="advisory",
        confirmation_required=False,
    )
