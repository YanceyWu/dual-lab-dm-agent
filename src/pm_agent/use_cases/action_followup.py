"""Read-only follow-up view for recorded open action items."""

from __future__ import annotations

from pm_agent.database import repository
from pm_agent.use_cases.service import UseCaseRequest, UseCaseResult, new_execution_metadata


def execute_action_followup(request: UseCaseRequest) -> UseCaseResult:
    items = repository.get_action_items(status="open")
    overdue_ids = {item["id"] for item in repository.get_action_items(overdue_only=True)}
    follow_up = []
    for item in items:
        reasons = []
        if item["id"] in overdue_ids: reasons.append("overdue")
        if not item.get("owner_id"): reasons.append("missing_owner")
        if not item.get("due_date"): reasons.append("missing_due_date")
        if reasons:
            follow_up.append({**item, "follow_up_reasons": reasons, "severity": "high" if "overdue" in reasons and item.get("priority") == "high" else "medium"})
    follow_up.sort(key=lambda item: (0 if item["severity"] == "high" else 1, item["id"]))
    result = UseCaseResult(status="success", data={"items": follow_up, "summary": {"open_count": len(items), "follow_up_count": len(follow_up), "overdue_count": len(overdue_ids)}}, evidence=[{"evidence_id": "action-followup-open-actions", "source_kind": "local_sqlite", "entity_kind": "action_items", "record_count": len(items), "applied_filters": {"status": "open"}}], assumptions=[{"code": "recorded_actions_only", "statement": "Follow-up uses recorded action status, owner, due date, and priority.", "impact": "It does not create, assign, or complete an action."}], warnings=[], execution_metadata=new_execution_metadata(request))
    result.context = {"context_version": "1.0", "context_type": "action_followup", "items": follow_up, "summary": result.data["summary"], "evidence": result.evidence, "assumptions": result.assumptions, "calculation": {"rule_version": "action-followup-v1", "calculation_basis": "open_action_fields"}, "execution_metadata": result.execution_metadata}
    return result
