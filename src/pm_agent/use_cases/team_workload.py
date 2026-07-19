"""Team workload service for current capacity and member detail views."""

from __future__ import annotations

from pm_agent.use_cases.service import ServiceRequest, ServiceResponse, BaseService
from pm_agent.database import repository


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
