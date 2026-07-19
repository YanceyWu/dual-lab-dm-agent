from __future__ import annotations

from datetime import datetime

from pm_agent.connectors import confluence, jira, servicenow
from pm_agent.connectors.base import ConnectorStatusRow, ConnectorValidationResult
from pm_agent.database import repository

CONNECTOR_MODULES = {
    "jira": jira,
    "confluence": confluence,
    "servicenow": servicenow,
}


def get_connector_module(name: str):
    normalized = name.strip().lower()
    if normalized not in CONNECTOR_MODULES:
        raise ValueError(f"Unknown connector: {name}")
    return CONNECTOR_MODULES[normalized]


def connector_names() -> list[str]:
    return list(CONNECTOR_MODULES.keys())


def validate_connectors(name: str | None = None) -> list[ConnectorValidationResult]:
    if name:
        return [get_connector_module(name).validate_connector()]
    return [module.validate_connector() for module in CONNECTOR_MODULES.values()]


def validate_portable_contracts(name: str | None = None) -> list[ConnectorValidationResult]:
    """Validate connector module contracts without reading runtime configuration."""
    names = [name.strip().lower()] if name else connector_names()
    results: list[ConnectorValidationResult] = []
    required_attributes = ("CONNECTOR_NAME", "DISPLAY_NAME", "SOURCE_TYPE", "validate_connector")

    for connector_name in names:
        module = get_connector_module(connector_name)
        missing = [attribute for attribute in required_attributes if not hasattr(module, attribute)]
        errors = [f"Missing portable connector contract attribute: {attribute}" for attribute in missing]
        results.append(
            ConnectorValidationResult(
                name=connector_name,
                display_name=str(getattr(module, "DISPLAY_NAME", connector_name)),
                enabled=False,
                ready=not errors,
                auth_mode="not-inspected",
                details={
                    "contract": "available" if not errors else "incomplete",
                    "runtime_configuration": "not inspected",
                    "network": "disabled",
                },
                warnings=["Portable validation does not verify credentials or runtime readiness."],
                errors=errors,
            )
        )
    return results


def _latest_timestamp(rows: list[dict]) -> str:
    latest: datetime | None = None
    latest_text = ""
    for row in rows:
        timestamp_text = row.get("latest_finished_at") or row.get("latest_started_at") or ""
        if not timestamp_text:
            continue
        try:
            timestamp = datetime.fromisoformat(timestamp_text)
        except ValueError:
            continue
        if latest is None or timestamp > latest:
            latest = timestamp
            latest_text = timestamp_text
    return latest_text


def _freshness_summary(rows: list[dict]) -> str:
    if not rows:
        return "no-data-sources"
    states = {row.get("freshness_state", "unknown") for row in rows if row.get("active")}
    if not states:
        return "inactive"
    priority = ["failed", "stale", "partial", "never_synced", "running", "fresh", "inactive"]
    for state in priority:
        if state in states:
            return state
    return sorted(states)[0]


def get_connector_status_rows(name: str | None = None) -> list[ConnectorStatusRow]:
    validations = validate_connectors(name=name)
    freshness_rows = repository.get_data_source_freshness(active_only=False)
    status_rows: list[ConnectorStatusRow] = []

    for validation in validations:
        module = get_connector_module(validation.name)
        relevant = [
            row
            for row in freshness_rows
            if row.get("source_type") == module.SOURCE_TYPE
        ]
        active_sources = sum(1 for row in relevant if row.get("active"))
        stale_sources = sum(
            1
            for row in relevant
            if row.get("active") and row.get("freshness_state") in {"failed", "stale", "partial", "never_synced"}
        )
        status_rows.append(
            ConnectorStatusRow(
                name=validation.name,
                display_name=validation.display_name,
                enabled=validation.enabled,
                ready=validation.ready,
                auth_mode=validation.auth_mode,
                active_sources=active_sources,
                stale_sources=stale_sources,
                latest_run_at=_latest_timestamp(relevant) or "-",
                freshness_summary=_freshness_summary(relevant),
            )
        )
    return status_rows
