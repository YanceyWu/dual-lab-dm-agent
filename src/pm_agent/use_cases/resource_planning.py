"""Resource planning service for staffing recommendations and confirmation."""

from __future__ import annotations

from pm_agent.use_cases.service import ServiceRequest, ServiceResponse, BaseService
from pm_agent.config import settings
from pm_agent.rules import scoring, validation
from pm_agent.database import decision_log, repository


class AllocationRequest(ServiceRequest):
    project_id: str
    role: str = ""
    task_type: str = "general"
    count: int = 1


class ResourcePlanningService(BaseService):
    supported_requests = ["allocate", "recommend_resource", "who_can_do"]

    def run(self, inp: ServiceRequest) -> ServiceResponse:
        # CLI commands call recommend() / confirm() directly.
        # run() keeps a simple generic entrypoint for future routing.
        return self.recommend(AllocationRequest(**inp.model_dump()))

    # ──────────────────────────────────────────
    # Core methods (called directly from CLI)
    # ──────────────────────────────────────────

    def recommend(self, inp: AllocationRequest) -> ServiceResponse:
        # Validate request
        vr = validation.validate_allocation_request(inp.model_dump())
        if not vr.valid:
            return ServiceResponse(success=False, message="; ".join(vr.errors))

        # Fetch data
        project = repository.get_project(inp.project_id)
        if not project:
            return ServiceResponse(
                success=False,
                message=f"项目 '{inp.project_id}' 不存在，请先用 `pm project add` 创建。",
            )
        current_state_freshness = repository.get_current_state_staffing_publication_freshness()
        freshness_state = str(current_state_freshness.get("state") or "unknown")
        if freshness_state in {"partial", "unknown", "unavailable"}:
            return ServiceResponse(
                success=False,
                message={
                    "partial": "当前态人员负载数据不完整，无法生成推荐方案。",
                    "unknown": "当前态人员负载未知，无法生成推荐方案。",
                    "unavailable": "当前态人员负载不可用，无法生成推荐方案。",
                }[freshness_state],
                data={"freshness": current_state_freshness},
            )
        all_members = repository.get_all_members()
        members = [
            member
            for member in all_members
            if (
                member.get("current_state_staffing_state") == "known"
                and member.get("employee_status") == "active"
                and repository.resolve_employee_id(str(member.get("id") or "")) is not None
            )
        ]
        omitted_members = [
            member
            for member in all_members
            if member not in members
        ]
        if not members:
            return ServiceResponse(
                success=False,
                message="当前态人员负载不可用，无法生成推荐方案。",
            )

        # Score every member
        scored: list[scoring.ScoringResult] = []
        for m in members:
            validation.validate_member(m)  # mutates m safely
            active_projects = repository.get_member_projects(m["id"])
            outcomes = [
                r["outcome"]
                for r in repository.get_decision_outcomes(m["id"], inp.task_type)
            ]
            result = scoring.score_member(
                member=m,
                active_projects=active_projects,
                target_project_id=inp.project_id,
                task_type=inp.task_type,
                historical_outcomes=outcomes,
                weights=settings.scoring,
                rules=settings.rules,
            )
            scored.append(result)

        # Sort: eligible first (by score desc), blocked last
        scored.sort(key=lambda s: (s.blocked, -s.score))

        # Build combination options
        options = scoring.build_options(scored, inp.count)
        if not options:
            eligible_count = sum(1 for s in scored if not s.blocked)
            return ServiceResponse(
                success=False,
                message=(
                    f"符合条件的人员不足（需要 {inp.count} 人，"
                    f"当前符合条件仅 {eligible_count} 人）。"
                ),
                data={"all_scores": _serialise_scores(scored)},
            )

        return ServiceResponse(
            success=True,
            message=f"为【{project['name']}】找到 {len(options)} 个推荐方案",
            data={
                "project": project,
                "requirement": inp.model_dump(),
                "options": [_serialise_option(o) for o in options],
                "all_scores": _serialise_scores(scored),
                "warnings": vr.warnings
                + (
                    [f"current_state_staffing_freshness:{freshness_state}"]
                    if freshness_state == "stale"
                    else []
                )
                + [
                    (
                        f"current_state_staffing_unavailable:{member['id']}:"
                        f"{member.get('current_state_staffing_state')}"
                    )
                    for member in omitted_members
                ],
                "freshness": current_state_freshness,
            },
        )

    def confirm(
        self,
        inp: AllocationRequest,
        chosen_option: scoring.AllocationOption,
        all_scored: list[scoring.ScoringResult],
        all_options: list[scoring.AllocationOption],
    ) -> ServiceResponse:
        """Persist the chosen allocation and write a Decision Log entry."""
        project = repository.get_project(inp.project_id)
        assert project  # already validated in recommend()

        # Write assignments
        for m in chosen_option.members:
            repository.create_assignment(
                employee_id=m.member_id,
                project_id=inp.project_id,
                role=inp.role or "developer",
                allocation=0.5,  # default; user can adjust later
            )

        # Write Decision Log
        alternatives = [
            {
                "label": o.label,
                "members": [{"member_id": m.member_id, "name": m.member_name} for m in o.members],
            }
            for o in all_options
            if o.label != chosen_option.label
        ]
        decision_id = decision_log.record_allocation(
            project_id=inp.project_id,
            project_name=project["name"],
            requirement=inp.model_dump(),
            all_candidates=[
                {
                    "member_id": s.member_id,
                    "name": s.member_name,
                    "score": s.score,
                    "breakdown": s.breakdown,
                    "blocked": s.blocked,
                    "blocked_reason": s.blocked_reason,
                }
                for s in all_scored
            ],
            chosen_members=[
                {"member_id": m.member_id, "name": m.member_name}
                for m in chosen_option.members
            ],
            alternatives=alternatives,
        )

        names = [m.member_name for m in chosen_option.members]
        return ServiceResponse(
            success=True,
            message=f"✅ 已分配 {', '.join(names)} 至 [{project['name']}]",
            decision_id=decision_id,
            data={"assigned": names, "project": project["name"]},
        )


# ──────────────────────────────────────────────
# Serialisation helpers
# ──────────────────────────────────────────────

def _serialise_scores(scored: list[scoring.ScoringResult]) -> list[dict]:
    return [
        {
            "member_id":     s.member_id,
            "name":          s.member_name,
            "score":         s.score,
            "breakdown":     s.breakdown,
            "blocked":       s.blocked,
            "blocked_reason": s.blocked_reason,
            "reason":        s.reason_text,
        }
        for s in scored
    ]


def _serialise_option(o: scoring.AllocationOption) -> dict:
    return {
        "label":          o.label,
        "combined_score": o.combined_score,
        "members": [
            {
                "member_id": m.member_id,
                "name":      m.member_name,
                "score":     m.score,
                "reason":    m.reason_text,
                "breakdown": m.breakdown,
            }
            for m in o.members
        ],
    }
