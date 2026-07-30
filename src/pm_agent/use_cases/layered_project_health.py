"""Read-only layered Project Health use case over persisted assessments."""

from __future__ import annotations

from typing import Any

from pm_agent.project_health.read_model import latest_assessments
from pm_agent.use_cases.service import (
    IntelligenceFact,
    IntelligenceSignal,
    IntelligenceSubject,
    UseCaseRequest,
    UseCaseResult,
    new_execution_metadata,
)


def execute_layered_project_health_review(request: UseCaseRequest) -> UseCaseResult:
    try:
        project_id = _project_id(request.parameters)
        assessments = latest_assessments(project_id=project_id)
    except ValueError as exc:
        return UseCaseResult(
            status="unavailable" if str(exc) == "PROJECT_NOT_FOUND" else "invalid",
            warnings=[{"code": str(exc)}],
            execution_metadata=new_execution_metadata(request),
        )
    return _result(request, project_id, assessments)


def _project_id(parameters: dict[str, Any]) -> str | None:
    value = parameters.get("project_id")
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > 128:
        raise ValueError("PROJECT_ID_INVALID")
    return value.strip()


def _result(
    request: UseCaseRequest, project_id: str | None, assessments: list[dict[str, Any]]
) -> UseCaseResult:
    facts: list[IntelligenceFact] = []
    signals: list[IntelligenceSignal] = []
    evidence: list[dict[str, Any]] = []
    freshness: list[dict[str, Any]] = []
    for assessment in assessments:
        subject = IntelligenceSubject(kind="project", id=assessment["project_id"])
        fact_id = f"layered-health-{assessment['assessment_run_id']}"
        evidence_id = f"layered-health-evidence-{assessment['assessment_run_id']}"
        freshness_id = f"layered-health-freshness-{assessment['assessment_run_id']}"
        value_state = (
            "unavailable" if assessment["state"] == "not_available"
            else "conflicting" if assessment["state"] == "conflicting"
            else "unknown" if assessment["state"] in {"unknown", "stale", "missing"}
            else "known"
        )
        facts.append(IntelligenceFact(
            fact_id=fact_id,
            fact_type="layered_project_health",
            fact_kind="derived",
            subject=subject,
            value={"overall_state": assessment["state"], "dimensions": assessment["dimensions"]},
            value_state=value_state,
            observed_at=assessment["created_at"],
            freshness_refs=[freshness_id],
            evidence_refs=[evidence_id],
            rule_version=assessment["catalog_version"],
        ))
        evidence.append({
            "evidence_id": evidence_id,
            "source_kind": "local_sqlite",
            "entity_kind": "project_health_assessment",
            "record_count": 1,
            "assessment_run_id": assessment["assessment_run_id"],
            "configuration_version_id": assessment["configuration_version_id"],
            "guard_outcomes": assessment["guard_outcomes"],
            "legacy_comparison": assessment["legacy_comparison"],
        })
        freshness.append({
            "source_id": freshness_id,
            "state": _assessment_freshness(assessment),
            "observed_at": assessment["created_at"],
        })
        if assessment["state"] in {"red", "amber"}:
            signals.append(IntelligenceSignal(
                signal_id=f"layered-health-signal-{assessment['assessment_run_id']}",
                signal_type="layered_project_health_state",
                subject=subject,
                state="active",
                severity="high" if assessment["state"] == "red" else "medium",
                reason_codes=[f"OVERALL_{assessment['state'].upper()}"],
                fact_refs=[fact_id],
                evidence_refs=[evidence_id],
                rule_version=assessment["catalog_version"],
            ))
    warnings = [] if assessments else ["LAYERED_PROJECT_HEALTH_NOT_AVAILABLE"]
    return UseCaseResult(
        status="success",
        data={"assessments": assessments, "filters": {"project_id": project_id}},
        context={"assessments": assessments, "limitations": warnings},
        facts=facts,
        signals=signals,
        evidence=evidence,
        freshness=freshness,
        assumptions=[{
            "code": "persisted_assessments_only",
            "statement": "The review reads only the latest persisted assessment for each selected project.",
            "impact": "It does not evaluate health, change configuration, reconcile Attention, or read a connector.",
        }],
        warnings=warnings,
        execution_metadata=new_execution_metadata(request),
    )


def _assessment_freshness(assessment: dict[str, Any]) -> str:
    """Do not label a persisted assessment fresh when its factors are limited."""
    states = {factor["state"] for factor in assessment["factors"]}
    if "stale" in states:
        return "stale"
    if all(factor["detail"].get("freshness") == "fresh" for factor in assessment["factors"]):
        return "fresh"
    return "unknown"
