"""Read-only interaction-memory context resolution for one Copilot chat turn."""

from __future__ import annotations

from pm_agent.interaction_memory.service import resolve_turn_context
from pm_agent.use_cases.service import UseCaseRequest, UseCaseResult, new_execution_metadata

_WARNING_BY_STATE = {
    "scope_unknown": {"code": "INTERACTION_MEMORY_SCOPE_UNKNOWN"},
    "disabled": {"code": "INTERACTION_MEMORY_DISABLED"},
    "empty": {"code": "INTERACTION_MEMORY_EMPTY"},
    "unavailable": {"code": "INTERACTION_MEMORY_UNAVAILABLE"},
}


def execute_interaction_memory_context(request: UseCaseRequest) -> UseCaseResult:
    """Resolve repo-scoped interaction memory and compose one bounded turn context."""
    payload = resolve_turn_context(
        message=str(request.parameters.get("message") or ""),
        project_id=str(request.parameters.get("project_id") or "") or None,
        repo_root=str(request.parameters.get("repo_root") or "") or None,
    )
    warning = _WARNING_BY_STATE.get(payload["capability_state"])
    result = UseCaseResult(
        status="success",
        data=payload,
        evidence=[
            {
                "evidence_id": "interaction-memory-local-scope",
                "source_kind": "local_sqlite",
                "entity_kind": "interaction_memory_entries",
                "record_count": payload["summary"]["total_entries"],
                "applied_filters": {
                    "scope_id": payload["scope"]["scope_id"]
                    if payload.get("scope")
                    else "",
                    "intent_tags": payload["turn"]["intent_tags"],
                },
            }
        ],
        assumptions=[
            {
                "code": "interaction_memory_not_authoritative_business_fact",
                "statement": "Interaction memory shapes local context and answer style only.",
                "impact": "Business facts still come from existing deterministic pm query and controlled write paths.",
            }
        ],
        warnings=[warning] if warning else [],
        execution_metadata=new_execution_metadata(request),
    )
    result.context = {
        "context_version": "1.0",
        "context_type": "interaction_memory_context",
        "turn": payload["turn"],
        "working_context": payload["working_context"],
        "execution_metadata": result.execution_metadata,
    }
    return result
