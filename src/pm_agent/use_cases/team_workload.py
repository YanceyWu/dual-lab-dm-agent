"""Team workload service for current capacity and member detail views."""

from __future__ import annotations

from pm_agent.use_cases.service import (
    BaseService,
    ServiceRequest,
    ServiceResponse,
    UseCaseRequest,
    UseCaseResult,
    new_execution_metadata,
)
from pm_agent.database import repository
from pm_agent.use_cases.team_capacity_context import build_team_capacity_context


class TeamWorkloadService(BaseService):
    supported_requests = ["workload", "who_is_available", "team_status"]

    def run(self, inp: ServiceRequest) -> ServiceResponse:
        return self.overview(team_filter=inp.context.get("team"))

    def overview(self, team_filter: str | None = None) -> ServiceResponse:
        members = repository.get_all_members()

        if team_filter:
            members = [m for m in members if m.get("team") == team_filter]

        if not members:
            return ServiceResponse(success=False, message="没有找到成员数据。")

        stats = _compute_stats(members)
        return ServiceResponse(
            success=True,
            message=f"共 {len(members)} 名成员",
            data={"members": members, "stats": stats},
        )

    def member_detail(self, member_id: str) -> ServiceResponse:
        m = repository.get_member(member_id)
        if not m:
            return ServiceResponse(success=False, message=f"成员 '{member_id}' 不存在。")

        projects = repository.get_member_projects(member_id)
        team_data = []
        for pid in projects:
            team_data.append(repository.get_project_team(pid))

        return ServiceResponse(
            success=True,
            data={"member": m, "projects": projects},
        )


def execute_team_workload_overview(request: UseCaseRequest) -> UseCaseResult:
    """Reference read-only use case exposed through the shared executor."""

    response = TeamWorkloadService().overview(team_filter=request.parameters.get("team"))
    metadata = new_execution_metadata(request)
    if not response.success:
        return UseCaseResult(
            status="unavailable",
            warnings=[response.message] if response.message else [],
            execution_metadata=metadata,
        )

    members = response.data["members"]
    freshness, freshness_warnings = _workload_freshness()
    result = UseCaseResult(
        status="success",
        data=response.data,
        evidence=[
            {
                "evidence_id": "team-workload-members",
                "source_kind": "local_sqlite",
                "entity_kind": "employees",
                "record_count": len(members),
                "applied_filters": {"team": request.parameters.get("team")},
            }
        ],
        freshness=freshness,
        assumptions=[
            {
                "code": "current_active_assignments",
                "statement": "Workload is derived from active assignments at execution time.",
                "impact": "Future allocations and unrecorded work are not included.",
            }
        ],
        warnings=freshness_warnings,
        alternatives=[],
        execution_metadata=metadata,
    )
    result.context = build_team_capacity_context(
        data=result.data,
        evidence=result.evidence,
        freshness=result.freshness,
        assumptions=result.assumptions,
        warnings=result.warnings,
        alternatives=result.alternatives,
        execution_metadata=result.execution_metadata,
    )
    return result


def _workload_freshness() -> tuple[list[dict], list[str]]:
    source_ids = {"import-resource-portal", "import-skills-matrix"}
    rows = {row["id"]: row for row in repository.get_data_source_freshness(active_only=False)}
    freshness: list[dict] = []
    warnings: list[str] = []
    for source_id in sorted(source_ids):
        row = rows.get(source_id)
        if row is None:
            state = "unknown"
            warning = "Source state is not registered locally."
        else:
            raw_state = row.get("freshness_state")
            state = {
                "fresh": "fresh",
                "stale": "stale",
                "partial": "partial",
                "failed": "unavailable",
                "never_synced": "unknown",
                "inactive": "unknown",
                "running": "partial",
            }.get(raw_state, "unknown")
            warning = "" if state == "fresh" else f"Source freshness is {state}."
        freshness.append(
            {
                "source_id": source_id,
                "state": state,
                "observed_at": row.get("latest_finished_at") if row else None,
                "last_success_at": row.get("latest_finished_at") if row and row.get("latest_status") == "success" else None,
                "refresh_sla_hours": row.get("refresh_sla_hours") if row else None,
                "warning": warning,
            }
        )
        if warning:
            warnings.append(f"freshness:{source_id}:{state}")
    return freshness, warnings


def _compute_stats(members: list[dict]) -> dict:
    loads = [m.get("current_load", 0.0) for m in members]
    available = [m for m in members if m.get("current_load", 0) < 0.8]
    overloaded = [m for m in members if m.get("current_load", 0) >= 1.0]

    return {
        "total":          len(members),
        "available":      len(available),   # < 80% load
        "overloaded":     len(overloaded),  # 100% load
        "avg_load":       round(sum(loads) / len(loads), 2) if loads else 0.0,
        "max_load":       round(max(loads), 2) if loads else 0.0,
    }
