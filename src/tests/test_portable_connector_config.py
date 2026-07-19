from __future__ import annotations

import pytest

from pm_agent.config import settings
from pm_agent.connectors.confluence import _configured_page_jobs
from pm_agent.connectors.shared import atlassian
from pm_agent.connectors.servicenow import browser_client


def test_servicenow_report_urls_require_local_configuration(monkeypatch) -> None:
    monkeypatch.setattr(settings, "snow_base_url", "")
    monkeypatch.setattr(settings, "snow_report_id", "")

    with pytest.raises(RuntimeError, match="SNOW_BASE_URL and SNOW_REPORT_ID"):
        browser_client._report_urls()


def test_servicenow_report_urls_are_built_from_local_configuration(monkeypatch) -> None:
    monkeypatch.setattr(settings, "snow_base_url", "https://snow.example.invalid/")
    monkeypatch.setattr(settings, "snow_report_id", "report 990001")

    navigation_url, direct_url = browser_client._report_urls()

    assert navigation_url.startswith("https://snow.example.invalid/")
    assert "report%2520990001" in navigation_url
    assert direct_url == "/sys_report_template.do?jvar_report_id=report%20990001&CSV"


def test_project_alias_groups_are_loaded_from_local_json(monkeypatch) -> None:
    monkeypatch.setattr(
        settings,
        "project_alias_groups_json",
        '[["Project Atlas", "Atlas Delivery"], ["Project Beacon"]]',
    )

    assert settings.project_alias_groups() == [
        {"Project Atlas", "Atlas Delivery"},
        {"Project Beacon"},
    ]


def test_project_alias_groups_reject_invalid_shape(monkeypatch) -> None:
    monkeypatch.setattr(settings, "project_alias_groups_json", '{"atlas": []}')

    with pytest.raises(ValueError, match="must be a JSON list"):
        settings.project_alias_groups()


def test_confluence_sync_uses_only_locally_configured_page_registry() -> None:
    pages = [
        ("page-990001", "atlas-board", "Atlas Weekly Status"),
        ("page-990002", "beacon-board", "Beacon Weekly Status"),
    ]

    assert _configured_page_jobs(pages) == {
        "atlas-board": ("page-990001", "Atlas Weekly Status"),
        "beacon-board": ("page-990002", "Beacon Weekly Status"),
    }


def test_atlassian_connector_reads_tokens_only_from_its_local_runtime_state() -> None:
    assert atlassian.TOKEN_PATHS == [atlassian.REPO_TOKEN_PATH]
    assert atlassian.ENV_PATHS == [atlassian.PROJECT_ROOT / ".env"]
