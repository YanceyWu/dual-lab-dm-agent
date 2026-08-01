"""C1 read-only projection of Phase 3 canonical execution facts."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from pm_agent.database.execution_review import list_latest_execution_facts
from pm_agent.use_cases.service import (
    IntelligenceFact,
    IntelligenceSignal,
    IntelligenceSubject,
    UseCaseRequest,
    UseCaseResult,
    new_execution_metadata,
)

LAYERS = {"sprint", "release_milestone", "all"}
SUBJECT_KINDS = {"sprint", "release", "milestone", "dependency"}


def execute_delivery_execution_review(request: UseCaseRequest) -> UseCaseResult:
    try:
        filters = _validated_filters(request.parameters)
        facts = list_latest_execution_facts(**filters)
    except ValueError as exc:
        return UseCaseResult(
            status="invalid" if str(exc) != "PROJECT_NOT_FOUND" else "unavailable",
            warnings=[{"code": str(exc)}],
            execution_metadata=new_execution_metadata(request),
        )
    except Exception:
        return UseCaseResult(
            status="failed",
            warnings=[{"code": "EXECUTION_REVIEW_DATA_ACCESS_FAILED"}],
            execution_metadata=new_execution_metadata(request),
        )
    return _result(request, filters, facts)


def _validated_filters(parameters: dict[str, Any]) -> dict[str, Any]:
    project_id = parameters.get("project_id")
    layer = parameters.get("layer", "all")
    subject_kind = parameters.get("subject_kind")
    subject_id = parameters.get("subject_id")
    window_days = parameters.get("window_days", 30)
    limit = parameters.get("limit", 100)
    if not isinstance(project_id, str) or not project_id.strip() or len(project_id) > 128:
        raise ValueError("PROJECT_ID_REQUIRED")
    if layer not in LAYERS:
        raise ValueError("EXECUTION_LAYER_INVALID")
    if subject_kind is not None and subject_kind not in SUBJECT_KINDS:
        raise ValueError("EXECUTION_SUBJECT_KIND_INVALID")
    if subject_id is not None and (not isinstance(subject_id, str) or not subject_id.strip() or not subject_kind):
        raise ValueError("EXECUTION_SUBJECT_SCOPE_INVALID")
    if not isinstance(window_days, int) or not 1 <= window_days <= 365:
        raise ValueError("EXECUTION_WINDOW_INVALID")
    if not isinstance(limit, int) or not 1 <= limit <= 200:
        raise ValueError("EXECUTION_LIMIT_INVALID")
    if layer == "sprint" and subject_kind and subject_kind != "sprint":
        raise ValueError("EXECUTION_SUBJECT_LAYER_INVALID")
    if layer == "release_milestone" and subject_kind == "sprint":
        raise ValueError("EXECUTION_SUBJECT_LAYER_INVALID")
    since = (datetime.now(timezone.utc) - timedelta(days=window_days)).isoformat(timespec="seconds")
    return {
        "project_id": project_id.strip(), "layer": layer, "subject_kind": subject_kind,
        "subject_id": subject_id.strip() if isinstance(subject_id, str) else None,
        "since": since, "limit": limit,
    }


def _result(request: UseCaseRequest, filters: dict[str, Any], rows: list[dict[str, Any]]) -> UseCaseResult:
    facts: list[IntelligenceFact] = []
    signals: list[IntelligenceSignal] = []
    evidence: list[dict[str, Any]] = []
    freshness: list[dict[str, Any]] = []
    sprint_execution: list[dict[str, Any]] = []
    release_milestone: list[dict[str, Any]] = []
    warnings: set[str] = set()
    for row in rows:
        fact_id = f"execution-fact-{row['fact_id']}"
        evidence_id = f"execution-evidence-{row['fact_id']}"
        freshness_id = f"execution-freshness-{row['fact_id']}"
        subject = IntelligenceSubject(kind=row["subject_kind"], id=row["subject_id"])
        facts.append(IntelligenceFact(
            fact_id=fact_id, fact_type=row["fact_key"], fact_kind="derived", subject=subject,
            value=row["value"], value_state=row["value_state"], observed_at=row["finished_at"] or row["started_at"],
            freshness_refs=[freshness_id], evidence_refs=[evidence_id], rule_version=row["rule_version"],
        ))
        evidence.append({"evidence_id": evidence_id, "source_kind": "local_sqlite", "entity_kind": "execution_derivation", "record_count": 1, "derivation_run_id": row["derivation_run_id"], "input_ids": row["input_ids"], "coverage": row["completeness_state"], "fact_evidence": row["evidence"], "event_time": {"state": row["event_time_state"], "occurred_at": row["event_occurred_at"] or None, "precision": row["event_time_precision"], "basis": row["event_time_basis"] or None}})
        freshness.append({"source_id": freshness_id, "state": row["freshness_state"], "observed_at": row["finished_at"] or row["started_at"]})
        warnings.update(row["warning_codes"])
        projection = {"subject": subject.model_dump(), "fact_key": row["fact_key"], "value": row["value"], "value_state": row["value_state"], "freshness_state": row["freshness_state"], "coverage": row["completeness_state"], "fact_observed_at": row["fact_observed_at"], "event_occurred_at": row["event_occurred_at"] or None, "event_time_precision": row["event_time_precision"], "event_time_state": row["event_time_state"], "event_time_basis": row["event_time_basis"] or None}
        (sprint_execution if row["subject_kind"] == "sprint" else release_milestone).append(projection)
        signal = _signal(row, fact_id, evidence_id, subject)
        if signal:
            signals.append(signal)
    if not rows:
        warnings.add("EXECUTION_FACTS_NOT_AVAILABLE")
    projection = {"sprint_execution": sprint_execution, "release_milestone": release_milestone, "source_coverage": sorted({row["completeness_state"] for row in rows}), "limitations": sorted(warnings), "filters": {key: value for key, value in filters.items() if key != "since"}}
    return UseCaseResult(status="success", data=projection, context=projection, facts=facts, signals=signals, evidence=evidence, freshness=freshness, assumptions=[{"code": "stored_execution_facts_only", "statement": "The review reads the latest bounded local derivation facts without running sync or derivation.", "impact": "It does not create a forecast, health RAG, Attention item, or business-object change."}], warnings=sorted(warnings), execution_metadata=new_execution_metadata(request))


def _signal(row: dict[str, Any], fact_id: str, evidence_id: str, subject: IntelligenceSubject) -> IntelligenceSignal | None:
    if row["value_state"] in {"unknown", "unavailable", "conflicting"}:
        state = "unavailable" if row["value_state"] == "unavailable" else "unknown"
        return IntelligenceSignal(signal_id=f"execution-signal-{row['fact_id']}", signal_type="execution_evidence_limited", subject=subject, state=state, severity="info", reason_codes=[f"FACT_{row['value_state'].upper()}"], fact_refs=[fact_id], evidence_refs=[evidence_id], rule_version=row["rule_version"])
    if row["fact_key"] == "milestone_adherence" and row["value"] in {"overdue", "achieved_late"}:
        return IntelligenceSignal(signal_id=f"execution-signal-{row['fact_id']}", signal_type="milestone_schedule_exception", subject=subject, state="active", severity="high" if row["value"] == "overdue" else "medium", reason_codes=[str(row["value"]).upper()], fact_refs=[fact_id], evidence_refs=[evidence_id], rule_version=row["rule_version"])
    return None
