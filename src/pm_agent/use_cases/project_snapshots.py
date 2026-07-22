"""Read-only project snapshot listing through the shared use-case contract."""

from __future__ import annotations

from pm_agent.database import repository
from pm_agent.use_cases.service import UseCaseRequest, UseCaseResult, new_execution_metadata

MAX_LIMIT = 200


def execute_project_snapshot_list(request: UseCaseRequest) -> UseCaseResult:
    params = request.parameters
    limit = _limit(params.get("limit"))
    filters = {"project_id": _text(params.get("project_id")), "artifact_kind": _text(params.get("artifact_kind")), "artifact_state": _text(params.get("artifact_state")), "health": _text(params.get("health")), "horizon": _text(params.get("horizon"))}
    snapshots = repository.get_project_snapshots(limit=limit, **filters)
    result = UseCaseResult(status="success", data={"snapshots": snapshots}, evidence=[{"evidence_id": "project-snapshot-list", "source_kind": "local_sqlite", "entity_kind": "project_snapshots", "record_count": len(snapshots), "applied_filters": {**filters, "limit": limit}}], assumptions=[{"code": "stored_snapshots_only", "statement": "The list contains only locally stored project snapshots matching the requested filters.", "impact": "It does not create, update, or infer a project snapshot."}], execution_metadata=new_execution_metadata(request))
    result.context = {"context_version": "1.0", "context_type": "project_snapshot_list", "snapshot_count": len(snapshots), "evidence": result.evidence, "assumptions": result.assumptions, "calculation": {"rule_version": "project-snapshot-list-v1", "calculation_basis": "stored_project_snapshots"}, "execution_metadata": result.execution_metadata}
    return result


def _text(value: object) -> str | None:
    result = str(value or "").strip()
    return result or None


def _limit(value: object) -> int:
    try: return max(1, min(int(value or 20), MAX_LIMIT))
    except (TypeError, ValueError): return 20
