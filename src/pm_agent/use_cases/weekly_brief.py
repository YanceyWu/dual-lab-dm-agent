"""Read-only structured weekly Delivery Manager brief."""

from __future__ import annotations

from pm_agent.database import repository
from pm_agent.use_cases.service import UseCaseRequest, UseCaseResult, new_execution_metadata
from pm_agent.use_cases.weekly_report import WeeklyReportService


def execute_weekly_dm_brief(request: UseCaseRequest) -> UseCaseResult:
    response = WeeklyReportService().weekly()
    raw = response.data["raw"]
    freshness_rows = repository.get_data_source_freshness(active_only=False)
    freshness = [{"source_id": row["id"], "state": {"fresh": "fresh", "stale": "stale", "partial": "partial", "failed": "unavailable", "never_synced": "unknown", "inactive": "unknown", "running": "partial"}.get(row.get("freshness_state"), "unknown"), "observed_at": row.get("latest_finished_at"), "refresh_sla_hours": row.get("refresh_sla_hours")} for row in freshness_rows if row["id"] in {"confluence-status-batch", "servicenow-change-requests"}]
    summary = {"project_count": len(raw["projects"]), "open_action_count": len(raw["actions"]), "overdue_action_count": len(raw["overdue"]), "recent_decision_count": len(raw["decisions"])}
    result = UseCaseResult(status="success", data={"week": response.data["week"], "brief": response.data["report"], "summary": summary}, evidence=[{"evidence_id": "weekly-dm-brief-local-facts", "source_kind": "local_sqlite", "entity_kind": "projects_actions_decisions", "record_count": summary["project_count"] + summary["open_action_count"] + summary["recent_decision_count"], "applied_filters": {"week": response.data["week"]}}], freshness=freshness, assumptions=[{"code": "current_local_weekly_facts", "statement": "The brief reflects locally stored current project, action, decision, and status facts.", "impact": "It does not fetch new source data or claim unrecorded changes."}], warnings=[f"freshness:{item['source_id']}:{item['state']}" for item in freshness if item["state"] != "fresh"], execution_metadata=new_execution_metadata(request))
    result.context = {"context_version": "1.0", "context_type": "weekly_dm_brief", "week": result.data["week"], "summary": summary, "evidence": result.evidence, "freshness": freshness, "assumptions": result.assumptions, "warnings": result.warnings, "calculation": {"rule_version": "weekly-dm-brief-v1", "calculation_basis": "local_weekly_report"}, "execution_metadata": result.execution_metadata}
    return result
