"""Bounded deterministic context for the current team-workload reference use case."""

from __future__ import annotations

from typing import Any

MAX_CONTEXT_MEMBERS = 20
RULE_VERSION = "team-workload-v1"


def build_team_capacity_context(
    *,
    data: dict[str, Any],
    evidence: list[dict[str, Any]],
    freshness: list[dict[str, Any]],
    assumptions: list[dict[str, Any]],
    warnings: list[str],
    alternatives: list[dict[str, Any]],
    execution_metadata: dict[str, Any],
) -> dict[str, Any]:
    """Build a size-bounded current-state context from an existing result only."""
    members = sorted(
        data.get("members", []),
        key=lambda member: (member.get("current_load", 0.0), member.get("id", "")),
    )
    selected_members = members[:MAX_CONTEXT_MEMBERS]
    context_members = [
        {
            "member_id": member.get("id", ""),
            "display_name": member.get("name", ""),
            "current_load": member.get("current_load", 0.0),
            "active_project_count": member.get("active_projects", 0),
            "availability_classification": _availability_classification(member.get("current_load", 0.0)),
        }
        for member in selected_members
    ]
    stats = data.get("stats", {})
    non_fresh = [item["state"] for item in freshness if item.get("state") != "fresh"]
    return {
        "context_version": "1.0",
        "context_type": "team_capacity",
        "use_case_id": execution_metadata.get("use_case_id", "team-workload-overview"),
        "requested_scope": {
            "team": _filter_value(evidence, "team"),
            "effective_period": "current",
            "requested_output": execution_metadata.get("requested_output", "default"),
        },
        "capacity_summary": {
            "total_members": stats.get("total", 0),
            "available_members": stats.get("available", 0),
            "overloaded_members": stats.get("overloaded", 0),
            "average_load": stats.get("avg_load", 0.0),
            "maximum_load": stats.get("max_load", 0.0),
        },
        "members": context_members,
        "evidence": evidence,
        "freshness": freshness,
        "assumptions": assumptions,
        "warnings": warnings,
        "alternatives": alternatives,
        "calculation": {
            "rule_version": RULE_VERSION,
            "calculation_basis": "active_assignments",
            "freshness_state": "fresh" if not non_fresh else "qualified",
        },
        "truncation": {
            "is_truncated": len(members) > MAX_CONTEXT_MEMBERS,
            "omitted_member_count": max(0, len(members) - MAX_CONTEXT_MEMBERS),
            "maximum_members": MAX_CONTEXT_MEMBERS,
        },
        "execution_metadata": execution_metadata,
    }


def _availability_classification(current_load: float) -> str:
    if current_load >= 1.0:
        return "overloaded"
    if current_load < 0.8:
        return "available"
    return "allocated"


def _filter_value(evidence: list[dict[str, Any]], name: str) -> Any:
    if not evidence:
        return None
    return evidence[0].get("applied_filters", {}).get(name)
