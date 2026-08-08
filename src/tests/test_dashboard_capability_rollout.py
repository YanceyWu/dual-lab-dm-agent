from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

from pm_agent.dashboard import server as dashboard_server
from pm_agent.dashboard.surface_manifest import (
    EXPERIMENTAL_TAB_IDS,
    PHASE1_LEGACY_DASHBOARD_TRIAL,
    surface_config_payload,
    visible_tab_labels,
)
from pm_agent.database.bootstrap import main as init_db


def test_dashboard_shell_marks_phase1_legacy_surface_as_the_default_trial() -> None:
    index_path = (
        Path(__file__).resolve().parents[1]
        / "pm_agent"
        / "dashboard"
        / "web"
        / "index.html"
    )
    html = index_path.read_text(encoding="utf-8")
    config_js = (
        Path(__file__).resolve().parents[1]
        / "pm_agent"
        / "dashboard"
        / "web"
        / "js"
        / "config.js"
    ).read_text(encoding="utf-8")
    app_js = (
        Path(__file__).resolve().parents[1]
        / "pm_agent"
        / "dashboard"
        / "web"
        / "js"
        / "app.js"
    ).read_text(encoding="utf-8")
    legacy_surface_js = (
        Path(__file__).resolve().parents[1]
        / "pm_agent"
        / "dashboard"
        / "web"
        / "js"
        / "surface-legacy.js"
    ).read_text(encoding="utf-8")
    experimental_surface_js = (
        Path(__file__).resolve().parents[1]
        / "pm_agent"
        / "dashboard"
        / "web"
        / "js"
        / "surface-experimental.js"
    ).read_text(encoding="utf-8")

    assert "PRODUCT_SURFACE" not in config_js
    assert "/dashboard-config.js" in html
    assert "/js/surface-legacy.js" in html
    assert "/js/surface-experimental.js" in html
    for tab_id in PHASE1_LEGACY_DASHBOARD_TRIAL.visible_tab_ids:
        assert f'data-tab="{tab_id}"' in html
        assert f'id: "{tab_id}"' in legacy_surface_js
    for label in visible_tab_labels():
        assert f">{label}<" in html
    for tab_id in EXPERIMENTAL_TAB_IDS:
        assert f'data-tab="{tab_id}"' in html
        assert f'id: "{tab_id}"' in experimental_surface_js
        assert re.search(
            rf'data-tab="{re.escape(tab_id)}"[^>]*hidden',
            html,
        )
        assert re.search(
            rf'id="section-{re.escape(tab_id)}"[^>]*hidden',
            html,
        )
    assert 'data-surface-group="experimental"' in html
    assert 'data-surface-group="experimental" hidden' in html
    assert "/js/section-intelligence.js" in html
    assert "LegacyDashboardSurface" in app_js
    assert "ExperimentalDashboardSurface" in app_js
    assert "App._surfaceAssemblies()" in app_js
    assert "App._buildTabRegistry();" in app_js
    assert 'typeof ExperimentalDashboardSurface !== "undefined"' in app_js
    assert "SectionOverview.load()" not in app_js
    assert "SectionIntelligence.loadAttention()" not in app_js
    assert "if (!App._visibleTabs.has(tab)) return false;" in app_js
    assert 'el.hidden = !visible;' in app_js
    assert 'App._applySurface();' in app_js
    assert 'document.querySelectorAll(".nav-group-label")' in app_js
    assert "SectionIntelligence" not in legacy_surface_js
    assert "SectionOverview" not in experimental_surface_js


def test_dashboard_surface_config_route_uses_phase1_manifest() -> None:
    response = dashboard_server.app.test_client().get("/dashboard-config.js")

    assert response.status_code == 200
    assert response.mimetype == "application/javascript"
    expected_payload = surface_config_payload()
    assert PHASE1_LEGACY_DASHBOARD_TRIAL.surface_id in response.get_data(as_text=True)
    assert json.dumps(expected_payload, ensure_ascii=False, sort_keys=True) in response.get_data(
        as_text=True
    )


def test_legacy_and_experimental_surface_assemblies_are_split() -> None:
    web_js = Path(__file__).resolve().parents[1] / "pm_agent" / "dashboard" / "web" / "js"
    legacy_surface_js = (web_js / "surface-legacy.js").read_text(encoding="utf-8")
    experimental_surface_js = (web_js / "surface-experimental.js").read_text(
        encoding="utf-8"
    )

    for token in (
        'id: "overview"',
        'id: "projects"',
        'id: "team"',
        'id: "hiref"',
        'id: "allocation"',
        'id: "health"',
    ):
        assert token in legacy_surface_js
    for token in (
        'id: "attention"',
        'id: "weekly-brief"',
        'id: "capacity"',
        'id: "execution"',
        'id: "layered-health"',
        'id: "connectors"',
        'id: "snapshots"',
    ):
        assert token in experimental_surface_js


def test_dashboard_bootstrap_treats_experimental_assembly_as_optional() -> None:
    app_js = (
        Path(__file__).resolve().parents[1]
        / "pm_agent"
        / "dashboard"
        / "web"
        / "js"
        / "app.js"
    ).read_text(encoding="utf-8")

    assert 'typeof LegacyDashboardSurface !== "undefined"' in app_js
    assert 'typeof ExperimentalDashboardSurface !== "undefined"' in app_js


def test_legacy_sections_read_through_page_providers() -> None:
    web_root = Path(__file__).resolve().parents[1] / "pm_agent" / "dashboard" / "web"
    web_js = web_root / "js"
    html = (web_root / "index.html").read_text(encoding="utf-8")
    provider_common_js = (web_js / "provider-common.js").read_text(encoding="utf-8")
    provider_overview_js = (web_js / "provider-overview.js").read_text(encoding="utf-8")
    provider_projects_js = (web_js / "provider-projects.js").read_text(encoding="utf-8")
    provider_team_js = (web_js / "provider-team.js").read_text(encoding="utf-8")
    provider_hiref_js = (web_js / "provider-hiref.js").read_text(encoding="utf-8")
    provider_allocation_js = (web_js / "provider-allocation.js").read_text(
        encoding="utf-8"
    )
    provider_health_js = (web_js / "provider-health.js").read_text(encoding="utf-8")
    section_overview_js = (web_js / "section-overview.js").read_text(encoding="utf-8")
    section_projects_js = (web_js / "section-projects.js").read_text(encoding="utf-8")
    section_team_js = (web_js / "section-team.js").read_text(encoding="utf-8")
    section_hiref_js = (web_js / "section-hiref.js").read_text(encoding="utf-8")
    section_allocation_js = (web_js / "section-allocation.js").read_text(encoding="utf-8")
    section_health_js = (web_js / "section-health.js").read_text(encoding="utf-8")

    assert "/js/provider-common.js" in html
    assert "/js/provider-overview.js" in html
    assert "/js/provider-projects.js" in html
    assert "/js/provider-team.js" in html
    assert "/js/provider-hiref.js" in html
    assert "/js/provider-allocation.js" in html
    assert "/js/provider-health.js" in html
    assert html.index("/js/provider-health.js") < html.index("/js/section-overview.js")

    assert "LegacyPageProviderSupport" in provider_common_js
    assert "Promise.allSettled" in provider_overview_js
    assert "Promise.allSettled" in provider_projects_js
    assert "_teamDisplayContract" in provider_projects_js
    assert "_healthDisplayContract" in provider_projects_js
    assert 'LegacyPageProviderSupport.meta("overview", issues)' in provider_overview_js
    assert 'LegacyPageProviderSupport.meta("projects", issues)' in provider_projects_js
    assert "TeamPageProvider._loadBucket" in provider_team_js
    assert "TeamPageProvider._loadDisplay" in provider_team_js
    assert "TeamPageProvider._hirefDisplay" in provider_team_js
    assert "contract_review_counts_available" in provider_team_js
    assert "_signalBadges" in provider_hiref_js
    assert "_normalizeAllHirefRow" in provider_hiref_js
    assert "_normalizeExpiringStaffRow" in provider_hiref_js
    assert "HirefPageProvider._coverageSubtitle" in provider_hiref_js
    assert "review_counts_available" in provider_hiref_js
    assert "expiringStaffState" in provider_hiref_js
    assert "expiringStaffMessage" in provider_hiref_js
    assert "MonthlyPlanPageProvider._pivot" in provider_allocation_js
    assert "employeeView" in provider_allocation_js
    assert "projectView" in provider_allocation_js
    assert "_buildEmployeeView" in provider_allocation_js
    assert "_buildProjectView" in provider_allocation_js
    assert "employeeIssueSummary" in provider_allocation_js
    assert "zeroAllocationEmployees" in provider_allocation_js
    assert "zeroAllocationProjects" in provider_allocation_js
    assert "ProjectHealthPageProvider._analyzeProject" in provider_health_js
    assert "previewBoardSync" in provider_health_js
    assert "previewStaleSync" in provider_health_js
    assert "confirmSync" in provider_health_js
    assert "_normalizePreview" in provider_health_js
    assert "_normalizeTargets" in provider_health_js
    assert "_pageSummary" in provider_health_js
    assert "confirmationMessage" in provider_health_js
    assert "boardName" in provider_health_js
    assert "jiraSummary" in provider_health_js
    assert "signalSummary" in provider_health_js
    assert "freshnessSummary" in provider_health_js
    assert "if (!summary && !projects && !employees && !hiref)" in provider_overview_js
    assert "_isHirefAlert" in provider_overview_js
    assert "review_counts_available" in provider_overview_js
    assert "current_state_staffing_state" in provider_overview_js
    assert "projectsTone" in provider_overview_js
    assert "teamTone" in provider_overview_js
    assert "staffingFreshnessState" in provider_overview_js
    assert 'loadDistribution.message || "Load distribution unavailable"' in section_overview_js
    assert "_badgeClass" in section_overview_js
    assert "LegacyPageProviderSupport.issueFromRejection" in provider_projects_js
    assert '"project health"' in provider_projects_js

    assert "OverviewPageProvider.load()" in section_overview_js
    assert "ProjectsPageProvider.load()" in section_projects_js
    assert "TeamPageProvider.load()" in section_team_js
    assert "HirefPageProvider.load()" in section_hiref_js
    assert "MonthlyPlanPageProvider.load()" in section_allocation_js
    assert "ProjectHealthPageProvider.load()" in section_health_js
    assert "ProjectHealthPageProvider.previewBoardSync" in section_health_js
    assert "ProjectHealthPageProvider.previewStaleSync" in section_health_js
    assert "ProjectHealthPageProvider.confirmSync" in section_health_js
    assert "model.summary" in section_health_js
    assert "confirmationMessage" in section_health_js
    assert "previewAction.requiresConfirmation" in section_health_js
    assert "requires_confirmation" not in section_health_js
    assert "board_name" not in section_health_js
    assert "result.message" in section_health_js
    assert "item.jira." not in section_health_js
    assert "item.confluence." not in section_health_js
    assert "SectionAllocation._data = model;" in section_allocation_js
    assert "by_employee" not in section_allocation_js
    assert "by_project" not in section_allocation_js
    assert "employeeIssueSummary" not in section_allocation_js
    assert "zeroAllocationEmployees" not in section_allocation_js
    assert "zeroAllocationProjects" not in section_allocation_js
    assert "r.months" not in section_allocation_js
    assert "r.projects" not in section_allocation_js
    assert "r.employees" not in section_allocation_js
    assert "SectionHealth._analyzeProject" not in section_health_js
    assert "memberRows" in provider_projects_js
    assert "healthDisplay" in provider_projects_js
    assert "loadDisplayState" in provider_team_js
    assert "hirefDisplayMessage" in provider_team_js
    assert "projectAssignments" in provider_team_js
    assert "signalBadges" in provider_hiref_js
    for section_js in (
        section_overview_js,
        section_projects_js,
        section_team_js,
        section_hiref_js,
        section_allocation_js,
        section_health_js,
    ):
        assert "DataService." not in section_js
    assert "var memberRows = p.memberRows || [];" in (
        web_js / "components.js"
    ).read_text(encoding="utf-8")
    assert "p.health ||" not in (web_js / "components.js").read_text(encoding="utf-8")
    assert "current_state_staffing_state === 'known'" not in (
        web_js / "components.js"
    ).read_text(encoding="utf-8")
    assert "next_hiref || item.assigned_next_hiref" not in (
        web_js / "components.js"
    ).read_text(encoding="utf-8")
    assert "e.current_hiref" not in (web_js / "components.js").read_text(encoding="utf-8")
    assert "hirefDisplayState === 'degraded'" in (
        web_js / "components.js"
    ).read_text(encoding="utf-8")


def test_allocations_route_includes_plan_version_id_for_capacity_defaults(
    isolated_db,
    monkeypatch,
) -> None:
    init_db(quiet=True)
    with sqlite3.connect(isolated_db) as connection:
        connection.execute(
            "INSERT INTO employees (id, name, status) VALUES ('member-dashboard-1', 'Synthetic Member', 'active')"
        )
        connection.execute(
            "INSERT INTO projects (id, name, status) VALUES ('project-dashboard-1', 'Synthetic Project', 'active')"
        )
        connection.execute(
            """
            INSERT INTO monthly_allocations
                (employee_id, project_id, year, month, allocation, plan_version_id)
            VALUES ('member-dashboard-1', 'project-dashboard-1', 2026, 8, 0.6, 'plan-dashboard-001')
            """
        )
        connection.commit()

    monkeypatch.setattr(dashboard_server, "DB", str(isolated_db))

    response = dashboard_server.app.test_client().get("/api/allocations")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload == [
        {
            "allocation": 0.6,
            "employee_id": "member-dashboard-1",
            "month": 8,
            "name": "Synthetic Member",
            "plan_version_id": "plan-dashboard-001",
            "project_id": "project-dashboard-1",
            "project_name": "Synthetic Project",
            "wd_id": "",
            "year": 2026,
        }
    ]


def test_dashboard_query_route_defaults_to_descriptor_contract_for_weekly_brief_v2(
    isolated_db,
    monkeypatch,
) -> None:
    init_db(quiet=True)
    monkeypatch.setattr(dashboard_server, "DB", str(isolated_db))

    response = dashboard_server.app.test_client().post(
        "/api/tool/query/weekly-dm-brief-v2",
        json={"parameters": {}},
    )

    assert response.status_code == 200
    assert response.headers["X-DM-Interface-Contract"] == "use-case-result-v1"
    payload = response.get_json()
    assert payload["contract_version"] == "2.0"
    assert payload["status"] == "success"
    assert payload["data"]["brief_version"] == "2.0"
