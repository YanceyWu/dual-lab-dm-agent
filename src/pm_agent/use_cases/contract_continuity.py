"""Read-only contract continuity review over existing local HIREF facts."""

from __future__ import annotations

from pm_agent.database import repository
from pm_agent.use_cases.service import UseCaseRequest, UseCaseResult, new_execution_metadata

RULE_VERSION = "contract-continuity-v1"
MAX_ROWS = 50


def execute_contract_continuity_review(request: UseCaseRequest) -> UseCaseResult:
    days = _bounded_days(request.parameters.get("days"))
    rows = repository.get_hiref_staff_review(days=days)
    risks = [row for row in rows if row.get("requires_action")]
    result = UseCaseResult(
        status="success",
        data={"review_window_days": days, "contracts": risks[:MAX_ROWS], "summary": {"reviewed_count": len(rows), "attention_count": len(risks), "critical_count": sum(row.get("urgency") in {"expired", "critical"} or row.get("current_hiref_missing") for row in risks)}},
        evidence=[{"evidence_id": "contract-continuity-hiref", "source_kind": "local_sqlite", "entity_kind": "hiref", "record_count": len(rows), "applied_filters": {"active_stfte": True, "days": days}}],
        assumptions=[{"code": "recorded_contracts_only", "statement": "Continuity uses active STFTE, recorded HIREF dates, next HIREF links, and active assignments.", "impact": "Unrecorded contract changes are not inferred."}],
        warnings=[f"contract_data_missing:{row['employee_id']}" for row in risks if row.get("current_hiref_missing")],
        execution_metadata=new_execution_metadata(request),
    )
    result.context = {"context_version": "1.0", "context_type": "contract_continuity", "review_window_days": days, "contracts": result.data["contracts"], "summary": result.data["summary"], "evidence": result.evidence, "assumptions": result.assumptions, "warnings": result.warnings, "calculation": {"rule_version": RULE_VERSION, "calculation_basis": "hiref_dates_assignments"}, "truncation": {"is_truncated": len(risks) > MAX_ROWS, "omitted_contract_count": max(0, len(risks) - MAX_ROWS), "maximum_contracts": MAX_ROWS}, "execution_metadata": result.execution_metadata}
    return result


def _bounded_days(value: object) -> int:
    try:
        return max(1, min(int(value or 180), 365))
    except (TypeError, ValueError):
        return 180
