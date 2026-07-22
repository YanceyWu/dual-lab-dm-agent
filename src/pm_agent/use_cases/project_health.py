"""Read-only Project Health use case built from existing local snapshots."""

from __future__ import annotations

from typing import Any

from pm_agent.database import repository
from pm_agent.use_cases.service import UseCaseRequest, UseCaseResult, new_execution_metadata

RULE_VERSION = "project-health-v1"
MAX_CONTEXT_PROJECTS = 20


def execute_project_health_review(request: UseCaseRequest) -> UseCaseResult:
    project_id = _optional_project_id(request.parameters.get("project_id"))
    projects = repository.get_project_health_facts(project_id)
    metadata = new_execution_metadata(request)
    if project_id and not projects:
        return UseCaseResult(
            status="unavailable",
            warnings=[f"No active project found: {project_id}"],
            execution_metadata=metadata,
        )

    freshness, freshness_warnings = _health_freshness(projects)
    for project in projects:
        project["health_state"] = _health_state(project["boards"])
        project["has_health_snapshot"] = any(
            board.get("health_snapshot_id") is not None for board in project["boards"]
        )
    missing_snapshot = [project["project_id"] for project in projects if not project["has_health_snapshot"]]
    warnings = list(freshness_warnings)
    warnings.extend(f"health_snapshot_missing:{project_id}" for project_id in missing_snapshot)
    summary = {
        "project_count": len(projects),
        "green_count": sum(item["health_state"] == "green" for item in projects),
        "amber_count": sum(item["health_state"] == "amber" for item in projects),
        "red_count": sum(item["health_state"] == "red" for item in projects),
        "unknown_count": sum(item["health_state"] == "unknown" for item in projects),
    }
    evidence = [
        {
            "evidence_id": "project-health-local-snapshots",
            "source_kind": "local_sqlite",
            "entity_kind": "projects",
            "record_count": len(projects),
            "applied_filters": {"project_id": project_id, "project_status": "active"},
        },
        {
            "evidence_id": "project-health-board-snapshots",
            "source_kind": "local_sqlite",
            "entity_kind": "jira_health_snapshots",
            "record_count": sum(len(item["boards"]) for item in projects),
            "applied_filters": {"latest_per_board": True},
        },
    ]
    result = UseCaseResult(
        status="success",
        data={"projects": projects, "summary": summary},
        evidence=evidence,
        freshness=freshness,
        assumptions=[
            {
                "code": "latest_local_snapshot_only",
                "statement": "Health is derived only from the latest locally stored board snapshots.",
                "impact": "The result does not fetch, infer, or predict delivery status.",
            },
            {
                "code": "grade_precedence",
                "statement": "A JIRA overall grade takes precedence over a status-page RAG label.",
                "impact": "Conflicting local observations are exposed as evidence rather than reconciled by the model.",
            },
        ],
        warnings=warnings,
        execution_metadata=metadata,
    )
    result.context = build_project_health_context(result)
    return result


def build_project_health_context(result: UseCaseResult) -> dict[str, Any]:
    projects = result.data.get("projects", [])
    selected = projects[:MAX_CONTEXT_PROJECTS]
    return {
        "context_version": "1.0",
        "context_type": "project_health",
        "use_case_id": result.execution_metadata.get("use_case_id"),
        "project_summary": result.data.get("summary", {}),
        "projects": [
            {
                "project_id": item["project_id"],
                "display_name": item["project_name"],
                "health_state": item["health_state"],
                "boards": [
                    {
                        "board_id": board["board_id"],
                        "overall_grade": board["overall_grade"],
                        "overall_score": board["overall_score"],
                        "health_snapshot_date": board["health_snapshot_date"],
                        "rag_status": board["rag_status"],
                        "status_snapshot_date": board["status_snapshot_date"],
                    }
                    for board in item["boards"]
                ],
            }
            for item in selected
        ],
        "evidence": result.evidence,
        "freshness": result.freshness,
        "assumptions": result.assumptions,
        "warnings": result.warnings,
        "calculation": {"rule_version": RULE_VERSION, "calculation_basis": "latest_local_snapshots"},
        "truncation": {
            "is_truncated": len(projects) > MAX_CONTEXT_PROJECTS,
            "omitted_project_count": max(0, len(projects) - MAX_CONTEXT_PROJECTS),
            "maximum_projects": MAX_CONTEXT_PROJECTS,
        },
        "execution_metadata": result.execution_metadata,
    }


def _optional_project_id(value: object) -> str | None:
    candidate = str(value or "").strip()
    return candidate or None


def _health_state(boards: list[dict]) -> str:
    grades = {str(item.get("overall_grade") or "").upper() for item in boards}
    if "RED" in grades:
        return "red"
    if "YELLOW" in grades or "AMBER" in grades:
        return "amber"
    if "GREEN" in grades:
        return "green"
    rags = {str(item.get("rag_status") or "").upper() for item in boards}
    if "RED" in rags:
        return "red"
    if "AMBER" in rags or "YELLOW" in rags:
        return "amber"
    if "GREEN" in rags:
        return "green"
    return "unknown"


def _health_freshness(projects: list[dict]) -> tuple[list[dict], list[str]]:
    source_ids = {"confluence-status-batch"}
    for project in projects:
        source_ids.update(f"jira-health-{board['board_id']}" for board in project["boards"])
    source_rows = {row["id"]: row for row in repository.get_data_source_freshness(active_only=False)}
    freshness: list[dict] = []
    warnings: list[str] = []
    state_map = {"fresh": "fresh", "stale": "stale", "partial": "partial", "failed": "unavailable", "never_synced": "unknown", "inactive": "unknown", "running": "partial"}
    for source_id in sorted(source_ids):
        row = source_rows.get(source_id)
        state = state_map.get(row.get("freshness_state"), "unknown") if row else "unknown"
        warning = "" if state == "fresh" else f"Source freshness is {state}."
        freshness.append({
            "source_id": source_id,
            "state": state,
            "observed_at": row.get("latest_finished_at") if row else None,
            "last_success_at": row.get("latest_finished_at") if row and row.get("latest_status") == "success" else None,
            "refresh_sla_hours": row.get("refresh_sla_hours") if row else None,
            "warning": warning,
        })
        if warning:
            warnings.append(f"freshness:{source_id}:{state}")
    return freshness, warnings
