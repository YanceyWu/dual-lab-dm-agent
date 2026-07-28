"""Deterministic, read-only ranking of locally observed management attention."""

from __future__ import annotations

from hashlib import sha256
from typing import Any

from pm_agent.database import repository
from pm_agent.use_cases.service import (
    IntelligenceFact,
    IntelligenceSignal,
    IntelligenceSubject,
    UseCaseRequest,
    UseCaseResult,
    new_execution_metadata,
)

RULE_VERSION = "management-attention-v1"
MAX_ITEMS = 20


def execute_management_attention(request: UseCaseRequest) -> UseCaseResult:
    limit = _bounded_int(request.parameters.get("limit"), default=10, maximum=MAX_ITEMS)
    items: list[dict[str, Any]] = []
    projects = repository.get_project_health_facts()
    for project in projects:
        state = _project_state(project["boards"])
        if state in {"red", "amber"}:
            items.append({
                "attention_type": "project_health",
                "severity": "critical" if state == "red" else "high",
                "subject_id": project["project_id"],
                "subject": project["project_name"],
                "reason_code": f"project_health_{state}",
                "evidence": {"health_state": state, "boards": project["boards"]},
            })
    for action in repository.get_action_items(overdue_only=True):
        items.append({
            "attention_type": "overdue_action",
            "severity": "high" if action.get("priority") == "high" else "medium",
            "subject_id": str(action.get("id", "")),
            "subject": action.get("title", ""),
            "reason_code": "action_overdue",
            "evidence": {"due_date": action.get("due_date"), "owner_id": action.get("owner_id"), "priority": action.get("priority")},
        })
    freshness, freshness_items, recorded_source_ids = _freshness_attention(projects)
    items.extend(freshness_items)
    items.sort(key=lambda item: (_severity_rank(item["severity"]), item["attention_type"], item["subject_id"]))
    selected = items[:limit]
    evidence = [
        {"evidence_id": "management-attention-project-health", "source_kind": "local_sqlite", "entity_kind": "projects", "record_count": len(projects), "applied_filters": {"active": True}},
        {"evidence_id": "management-attention-overdue-actions", "source_kind": "local_sqlite", "entity_kind": "action_items", "record_count": sum(item["attention_type"] == "overdue_action" for item in items), "applied_filters": {"overdue_only": True}},
    ]
    facts, signals, intelligence_evidence = _build_intelligence(
        selected,
        recorded_source_ids,
    )
    result = UseCaseResult(
        status="success",
        data={"items": selected, "summary": _summary(items, selected, limit)},
        evidence=[*evidence, *intelligence_evidence],
        freshness=freshness,
        facts=facts,
        signals=signals,
        assumptions=[{"code": "observed_attention_only", "statement": "Items are ranked from stored project health, overdue actions, and source freshness.", "impact": "The result does not predict risks, assign owners, or create actions."}],
        warnings=[f"attention_source_not_fresh:{item['subject_id']}" for item in freshness_items],
        execution_metadata=new_execution_metadata(request),
    )
    result.context = {"context_version": "1.0", "context_type": "management_attention", "items": selected, "summary": result.data["summary"], "evidence": result.evidence, "freshness": freshness, "warnings": result.warnings, "calculation": {"rule_version": RULE_VERSION, "calculation_basis": "health_actions_freshness"}, "truncation": {"is_truncated": len(items) > limit, "omitted_item_count": max(0, len(items) - limit), "maximum_items": limit}, "execution_metadata": result.execution_metadata}
    return result


def _project_state(boards: list[dict]) -> str:
    grades = {str(item.get("overall_grade") or "").upper() for item in boards}
    if "RED" in grades:
        return "red"
    if "YELLOW" in grades or "AMBER" in grades:
        return "amber"
    rags = {str(item.get("rag_status") or "").upper() for item in boards}
    if "RED" in rags:
        return "red"
    if "AMBER" in rags or "YELLOW" in rags:
        return "amber"
    return "unknown"


def _freshness_attention(
    projects: list[dict],
) -> tuple[list[dict], list[dict], set[str]]:
    source_ids = {"confluence-status-batch"}
    for project in projects:
        source_ids.update(f"jira-health-{board['board_id']}" for board in project["boards"])
    rows = {row["id"]: row for row in repository.get_data_source_freshness(active_only=False)}
    states = {"fresh": "fresh", "stale": "stale", "partial": "partial", "failed": "unavailable", "never_synced": "unknown", "inactive": "unknown", "running": "partial"}
    freshness, attention = [], []
    for source_id in sorted(source_ids):
        row = rows.get(source_id)
        state = states.get(row.get("freshness_state"), "unknown") if row else "unknown"
        freshness.append({"source_id": source_id, "state": state, "observed_at": row.get("latest_finished_at") if row else None, "refresh_sla_hours": row.get("refresh_sla_hours") if row else None})
        if state != "fresh":
            attention.append({"attention_type": "source_freshness", "severity": "high" if state in {"stale", "unavailable"} else "medium", "subject_id": source_id, "subject": source_id, "reason_code": f"source_{state}", "evidence": {"freshness_state": state}})
    return freshness, attention, set(rows)


def _build_intelligence(
    selected: list[dict[str, Any]],
    recorded_source_ids: set[str],
) -> tuple[list[IntelligenceFact], list[IntelligenceSignal], list[dict[str, Any]]]:
    facts: list[IntelligenceFact] = []
    signals: list[IntelligenceSignal] = []
    extra_evidence: list[dict[str, Any]] = []
    subject_kinds = {
        "project_health": "project",
        "overdue_action": "action",
        "source_freshness": "source",
    }
    fact_types = {
        "project_health": "project_health_state",
        "overdue_action": "action_due_state",
        "source_freshness": "source_freshness_state",
    }
    signal_types = {
        "project_health": "project_health_attention",
        "overdue_action": "overdue_action_attention",
        "source_freshness": "source_freshness_attention",
    }
    base_evidence_ids = {
        "project_health": "management-attention-project-health",
        "overdue_action": "management-attention-overdue-actions",
    }

    for item in selected:
        attention_type = str(item["attention_type"])
        subject_id = str(item["subject_id"])
        fact_id = _result_local_id("fact", attention_type, subject_id)
        signal_id = _result_local_id("signal", attention_type, subject_id)
        freshness_refs: list[str] = []
        if attention_type == "project_health":
            freshness_refs = sorted(
                {
                    "confluence-status-batch",
                    *(
                        f"jira-health-{board['board_id']}"
                        for board in item["evidence"].get("boards", [])
                    ),
                }
            )

        if attention_type == "source_freshness":
            freshness_refs = [subject_id]
            evidence_id = _result_local_id(
                "evidence",
                attention_type,
                subject_id,
            )
            extra_evidence.append(
                {
                    "evidence_id": evidence_id,
                    "source_kind": "local_sqlite",
                    "entity_kind": "data_sources_sync_runs",
                    "record_count": int(subject_id in recorded_source_ids),
                    "applied_filters": {
                        "source_id": subject_id,
                        "latest_sync_only": True,
                    },
                }
            )
        else:
            evidence_id = base_evidence_ids[attention_type]

        value, value_state = _fact_value(item)
        subject = IntelligenceSubject(
            kind=subject_kinds[attention_type],
            id=subject_id,
        )
        facts.append(
            IntelligenceFact(
                fact_id=fact_id,
                fact_type=fact_types[attention_type],
                fact_kind="derived",
                subject=subject,
                value=value,
                value_state=value_state,
                freshness_refs=freshness_refs,
                evidence_refs=[evidence_id],
                rule_version=RULE_VERSION,
            )
        )
        signals.append(
            IntelligenceSignal(
                signal_id=signal_id,
                signal_type=signal_types[attention_type],
                subject=subject,
                state="active",
                severity=item["severity"],
                reason_codes=[item["reason_code"]],
                fact_refs=[fact_id],
                evidence_refs=[evidence_id],
                rule_version=RULE_VERSION,
            )
        )

    return facts, signals, extra_evidence


def _fact_value(item: dict[str, Any]) -> tuple[object | None, str]:
    attention_type = item["attention_type"]
    if attention_type == "project_health":
        return item["evidence"]["health_state"], "known"
    if attention_type == "overdue_action":
        return "overdue", "known"
    state = item["evidence"]["freshness_state"]
    if state in {"unknown", "unavailable"}:
        return None, state
    return state, "known"


def _result_local_id(prefix: str, attention_type: str, subject_id: str) -> str:
    candidate = f"{prefix}:{attention_type}:{subject_id}"
    if len(candidate) <= 128:
        return candidate
    digest = sha256(candidate.encode("utf-8")).hexdigest()[:16]
    return f"{candidate[:111]}:{digest}"


def _summary(all_items: list[dict], selected: list[dict], limit: int) -> dict:
    return {"total_attention_count": len(all_items), "returned_count": len(selected), "critical_count": sum(item["severity"] == "critical" for item in all_items), "high_count": sum(item["severity"] == "high" for item in all_items), "limit": limit}


def _severity_rank(severity: str) -> int:
    return {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(severity, 9)


def _bounded_int(value: object, default: int, maximum: int) -> int:
    try:
        return max(1, min(int(value or default), maximum))
    except (TypeError, ValueError):
        return default
