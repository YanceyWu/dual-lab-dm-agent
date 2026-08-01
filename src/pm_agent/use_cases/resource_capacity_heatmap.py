"""Read-only Resource Intelligence heatmap over published capacity facts."""

from __future__ import annotations

from typing import Any

from pm_agent.resource_intelligence.read_model import list_effective_capacity
from pm_agent.use_cases.service import (
    IntelligenceFact,
    IntelligenceSignal,
    IntelligenceSubject,
    UseCaseRequest,
    UseCaseResult,
    new_execution_metadata,
)

_STATES = {"known", "stale", "unknown", "conflicting"}


def execute_resource_capacity_heatmap(request: UseCaseRequest) -> UseCaseResult:
    parameters = request.parameters
    try:
        member_ids = _string_list(parameters.get("member_ids"), "member_ids")
        states = _string_list(parameters.get("states"), "states")
    except ValueError as exc:
        return _invalid(request, str(exc))
    if states and not set(states).issubset(_STATES):
        return _invalid(request, "RESOURCE_CAPACITY_STATE_FILTER_INVALID")
    rows = list_effective_capacity(
        int(parameters["year"]),
        int(parameters["month"]),
        str(parameters["plan_version_id"]),
        member_ids=member_ids,
        states=states,
    )
    if not rows:
        return UseCaseResult(
            status="unavailable",
            data={"rows": [], "filters": _filters(parameters)},
            warnings=["RESOURCE_CAPACITY_HEATMAP_NOT_AVAILABLE"],
            assumptions=[_assumption()],
            execution_metadata=new_execution_metadata(request),
        )

    facts: list[IntelligenceFact] = []
    signals: list[IntelligenceSignal] = []
    evidence: list[dict[str, Any]] = []
    freshness: list[dict[str, Any]] = []
    warnings: list[str] = []
    for row in rows:
        subject = IntelligenceSubject(kind="workforce_member", id=row["member_id"])
        evidence_id = f"capacity-evidence-{row['derivation_id']}"
        freshness_id = f"capacity-freshness-{row['derivation_id']}"
        fact_id = f"capacity-fact-{row['derivation_id']}"
        evidence.append({
            "evidence_id": evidence_id,
            "source_kind": "published_resource_capacity",
            "publication_id": row["publication_id"],
            "derivation_id": row["derivation_id"],
            "plan_version_id": row["plan_version_id"],
            "component_evidence": row["evidence"],
        })
        freshness.append({
            "source_id": freshness_id,
            "state": "fresh" if row["state"] == "known" else row["state"],
            "observed_at": row["assessment_time"],
            "rule_version": row["freshness_rule_version"],
        })
        known = row["state"] == "known"
        facts.append(IntelligenceFact(
            fact_id=fact_id,
            fact_type="effective_capacity",
            fact_kind="derived",
            subject=subject,
            value={
                "year": row["year"],
                "month": row["month"],
                "base_capacity": row["base_capacity"],
                "leave_fraction": row["leave_fraction"],
                "bau_fraction": row["bau_fraction"],
                "non_project_fraction": row["non_project_fraction"],
                "effective_capacity_raw": row["effective_capacity_raw"],
                "effective_capacity": row["effective_capacity"],
                "planned_project_allocation": row["planned_project_allocation"],
                "available_capacity_raw": row["available_capacity_raw"],
                "available_capacity": row["available_capacity"],
                "total_commitment": row["total_commitment"],
                "overload_amount": row["overload_amount"],
                "overload_state": row["overload_state"],
                "plan_version_id": row["plan_version_id"],
                "derivation_id": row["derivation_id"],
            } if known else None,
            value_state="known" if known else (
                "conflicting" if row["state"] == "conflicting" else "unknown"
            ),
            observed_at=row["assessment_time"],
            freshness_refs=[freshness_id],
            evidence_refs=[evidence_id],
            rule_version=row["derivation_rule_version"],
        ))
        if known:
            overload = row["overload_state"]
            signals.append(IntelligenceSignal(
                signal_id=f"capacity-overload-{row['derivation_id']}",
                signal_type="resource_overload",
                subject=subject,
                state="clear" if overload == "clear" else "active",
                severity={"clear": "info", "amber": "medium", "red": "high"}[overload],
                reason_codes=[f"RESOURCE_OVERLOAD_{overload.upper()}"],
                fact_refs=[fact_id],
                evidence_refs=[evidence_id],
                rule_version=row["overload_rule_version"],
            ))
        else:
            warnings.append(f"RESOURCE_CAPACITY_{row['state'].upper()}:{row['member_id']}")
    return UseCaseResult(
        status="success",
        data={"rows": rows, "filters": _filters(parameters)},
        context={"limitations": sorted(set(warnings))},
        facts=facts,
        signals=signals,
        evidence=evidence,
        freshness=freshness,
        assumptions=[_assumption()],
        warnings=sorted(set(warnings)),
        execution_metadata=new_execution_metadata(request),
    )


def _string_list(value: object, field: str) -> list[str] | None:
    if value is None:
        return None
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item.strip() or len(item) > 128 for item in value
    ):
        raise ValueError(f"RESOURCE_CAPACITY_{field.upper()}_INVALID")
    normalized = [item.strip() for item in value]
    if len(normalized) > 200:
        raise ValueError(f"RESOURCE_CAPACITY_{field.upper()}_LIMIT_EXCEEDED")
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"RESOURCE_CAPACITY_{field.upper()}_DUPLICATE")
    return normalized


def _filters(parameters: dict[str, Any]) -> dict[str, Any]:
    return {
        "year": parameters["year"],
        "month": parameters["month"],
        "plan_version_id": parameters["plan_version_id"],
        "member_ids": parameters.get("member_ids", []),
        "states": parameters.get("states", []),
    }


def _assumption() -> dict[str, str]:
    return {
        "code": "published_capacity_only",
        "statement": "The heatmap reads persisted current capacity derivations only.",
        "impact": "It does not recalculate capacity, change Staffing, or write data.",
    }


def _invalid(request: UseCaseRequest, code: str) -> UseCaseResult:
    return UseCaseResult(
        status="invalid",
        warnings=[{"code": code}],
        execution_metadata=new_execution_metadata(request),
    )
