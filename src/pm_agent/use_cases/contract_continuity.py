"""Read-only contract continuity review over existing local HIREF facts."""

from __future__ import annotations

from pm_agent.database import repository
from pm_agent.rules.hiref import contract_review_counts_available
from pm_agent.use_cases.service import UseCaseRequest, UseCaseResult, new_execution_metadata

RULE_VERSION = "contract-continuity-v1"
MAX_ROWS = 50


def execute_contract_continuity_review(request: UseCaseRequest) -> UseCaseResult:
    days = _bounded_days(request.parameters.get("days"))
    rows = repository.get_hiref_staff_review(days=days)
    publication = repository.get_contract_coverage_publication_freshness()
    freshness = [publication]
    risks = [row for row in rows if row.get("requires_action")]
    summary = {
        "reviewed_count": len(rows) if contract_review_counts_available(publication) else None,
        "attention_count": len(risks) if contract_review_counts_available(publication) else None,
        "critical_count": (
            sum(
                row.get("urgency") in {"expired", "critical"} or row.get("current_hiref_missing")
                for row in risks
            )
            if contract_review_counts_available(publication)
            else None
        ),
    }
    warnings = [
        f"freshness:{publication['source_id']}:{publication['state']}"
    ] if publication.get("warning") else []
    warnings.extend(
        f"contract_data_missing:{row['employee_id']}"
        for row in risks
        if row.get("current_hiref_missing")
    )
    result = UseCaseResult(
        status="success",
        data={"review_window_days": days, "contracts": risks[:MAX_ROWS], "summary": summary},
        evidence=[
            {
                "evidence_id": "contract-continuity-contract-rows",
                "source_kind": "local_sqlite",
                "entity_kind": "contract_coverage_members",
                "record_count": len(rows),
                "applied_filters": {"active_stfte": True, "days": days},
            },
            {
                "evidence_id": "contract-coverage-publication",
                "source_kind": "contract_coverage_publication",
                "entity_kind": "contract_coverage_publication",
                "authority": "canonical",
                "publication_id": publication.get("publication_id"),
                "state": publication.get("state"),
                "state_reason": publication.get("state_reason"),
                "as_of_date": publication.get("as_of_date"),
                "observed_at": publication.get("observed_at"),
                "coverage_state": publication.get("coverage_state"),
            },
        ],
        freshness=freshness,
        assumptions=[{"code": "contract_coverage_publication", "statement": "Continuity reads the latest canonical contract-coverage publication for active STFTE contract facts and uses current-state staffing only for active-project context.", "impact": "Missing or incomplete contract-coverage publication keeps freshness explicit and does not infer unseen contracts."}],
        warnings=warnings,
        execution_metadata=new_execution_metadata(request),
    )
    result.context = {"context_version": "1.0", "context_type": "contract_continuity", "review_window_days": days, "contracts": result.data["contracts"], "summary": result.data["summary"], "evidence": result.evidence, "freshness": result.freshness, "assumptions": result.assumptions, "warnings": result.warnings, "calculation": {"rule_version": RULE_VERSION, "calculation_basis": "contract_coverage_publication_plus_current_state_staffing"}, "truncation": {"is_truncated": len(risks) > MAX_ROWS, "omitted_contract_count": max(0, len(risks) - MAX_ROWS), "maximum_contracts": MAX_ROWS}, "execution_metadata": result.execution_metadata}
    return result


def _bounded_days(value: object) -> int:
    try:
        return max(1, min(int(value or 180), 365))
    except (TypeError, ValueError):
        return 180
