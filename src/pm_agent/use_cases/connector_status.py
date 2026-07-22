"""Structured, credential-free connector readiness and freshness review."""

from __future__ import annotations

from pm_agent.connectors import registry
from pm_agent.database import repository
from pm_agent.use_cases.service import UseCaseRequest, UseCaseResult, new_execution_metadata


def execute_connector_status_review(request: UseCaseRequest) -> UseCaseResult:
    requested = str(request.parameters.get("connector") or "").strip().lower() or None
    try:
        rows = registry.get_connector_status_rows(name=requested)
    except ValueError:
        return UseCaseResult(status="unavailable", warnings=[f"Unknown connector: {requested}"], execution_metadata=new_execution_metadata(request))
    sources = repository.get_data_source_freshness(active_only=False)
    data = []
    warnings = []
    for row in rows:
        item = {"connector": row.name, "display_name": row.display_name, "enabled": row.enabled, "ready": row.ready, "auth_mode": row.auth_mode, "active_sources": row.active_sources, "stale_sources": row.stale_sources, "latest_run_at": row.latest_run_at, "freshness_state": row.freshness_summary}
        data.append(item)
        if not row.ready or row.freshness_summary not in {"fresh", "inactive", "no-data-sources"}:
            warnings.append(f"connector:{row.name}:{row.freshness_summary}")
    result = UseCaseResult(status="success", data={"connectors": data}, evidence=[{"evidence_id": "connector-status-source-registry", "source_kind": "local_sqlite", "entity_kind": "data_sources_sync_runs", "record_count": len(sources), "applied_filters": {"connector": requested}}], freshness=[{"source_id": row["id"], "state": row["freshness_state"], "observed_at": row.get("latest_finished_at"), "refresh_sla_hours": row.get("refresh_sla_hours")} for row in sources], assumptions=[{"code": "credential_free_status", "statement": "Readiness uses connector validation and local source/sync metadata only.", "impact": "Credentials, endpoints, and network calls are not exposed or performed."}], warnings=warnings, execution_metadata=new_execution_metadata(request))
    result.context = {"context_version": "1.0", "context_type": "connector_status", "connectors": data, "evidence": result.evidence, "freshness": result.freshness, "assumptions": result.assumptions, "warnings": warnings, "calculation": {"rule_version": "connector-status-v1", "calculation_basis": "validation_source_freshness"}, "execution_metadata": result.execution_metadata}
    return result
