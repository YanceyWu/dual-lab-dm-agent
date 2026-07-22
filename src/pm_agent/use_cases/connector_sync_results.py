"""Credential-free normalized view of locally recorded connector sync outcomes."""

from __future__ import annotations

from pm_agent.connectors import registry
from pm_agent.database import repository
from pm_agent.use_cases.service import UseCaseRequest, UseCaseResult, new_execution_metadata

RULE_VERSION = "connector-sync-result-v1"


def execute_connector_sync_results(request: UseCaseRequest) -> UseCaseResult:
    connector = str(request.parameters.get("connector") or "").strip().lower() or None
    if connector and connector not in registry.connector_names():
        return UseCaseResult(status="unavailable", warnings=[f"Unknown connector: {connector}"], execution_metadata=new_execution_metadata(request))
    modules = {name: registry.get_connector_module(name) for name in registry.connector_names()}
    source_rows = repository.get_data_source_freshness(active_only=False)
    results = []
    for source in source_rows:
        matching = [name for name, module in modules.items() if module.SOURCE_TYPE == source.get("source_type")]
        if not matching:
            continue
        name = matching[0]
        if connector and name != connector:
            continue
        results.append(_normalize(name, source))
    results.sort(key=lambda item: (item["connector"], item["source_id"]))
    result = UseCaseResult(
        status="success",
        data={"sync_results": results, "summary": _summary(results)},
        evidence=[{"evidence_id": "connector-sync-run-records", "source_kind": "local_sqlite", "entity_kind": "data_sources_sync_runs", "record_count": len(results), "applied_filters": {"connector": connector}}],
        freshness=[{"source_id": item["source_id"], "state": item["freshness_state"], "observed_at": item["finished_at"], "refresh_sla_hours": item["refresh_sla_hours"]} for item in results],
        assumptions=[{"code": "latest_recorded_run_only", "statement": "Each result represents the latest locally recorded run for one source.", "impact": "It does not invoke a connector, retry a run, or expose raw errors/configuration."}],
        warnings=[f"sync:{item['source_id']}:{item['outcome']}" for item in results if item["outcome"] not in {"success", "never_synced"}],
        execution_metadata=new_execution_metadata(request),
    )
    result.context = {"context_version": "1.0", "context_type": "connector_sync_results", "sync_results": results, "summary": result.data["summary"], "evidence": result.evidence, "freshness": result.freshness, "assumptions": result.assumptions, "warnings": result.warnings, "calculation": {"rule_version": RULE_VERSION, "calculation_basis": "latest_data_source_sync_run"}, "execution_metadata": result.execution_metadata}
    return result


def _normalize(connector: str, source: dict) -> dict:
    latest = source.get("latest_status") or ""
    outcome = {"success": "success", "partial": "partial", "failed": "failed", "running": "running"}.get(latest, "never_synced")
    return {"connector": connector, "source_id": source["id"], "outcome": outcome, "freshness_state": source.get("freshness_state", "unknown"), "started_at": source.get("latest_started_at"), "finished_at": source.get("latest_finished_at"), "rows_observed": int(source.get("latest_rows_in") or 0), "rows_changed": int(source.get("latest_rows_changed") or 0), "target_tables": source.get("latest_target_tables", []), "retry_recommended": outcome in {"failed", "partial"}, "error_present": bool(source.get("latest_error_message")), "refresh_sla_hours": source.get("refresh_sla_hours")}


def _summary(results: list[dict]) -> dict:
    return {"source_count": len(results), "success_count": sum(item["outcome"] == "success" for item in results), "partial_count": sum(item["outcome"] == "partial" for item in results), "failed_count": sum(item["outcome"] == "failed" for item in results), "never_synced_count": sum(item["outcome"] == "never_synced" for item in results)}
