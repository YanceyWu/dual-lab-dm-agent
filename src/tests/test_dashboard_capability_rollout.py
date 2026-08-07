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

    assert "PRODUCT_SURFACE" not in config_js
    assert "/dashboard-config.js" in html
    for tab_id in PHASE1_LEGACY_DASHBOARD_TRIAL.visible_tab_ids:
        assert f'data-tab="{tab_id}"' in html
    for label in visible_tab_labels():
        assert f">{label}<" in html
    for tab_id in EXPERIMENTAL_TAB_IDS:
        assert f'data-tab="{tab_id}"' in html
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
    assert "if (!App._visibleTabs.has(tab)) return false;" in app_js
    assert 'el.hidden = !visible;' in app_js
    assert 'App._applySurface();' in app_js
    assert 'document.querySelectorAll(".nav-group-label")' in app_js


def test_dashboard_surface_config_route_uses_phase1_manifest() -> None:
    response = dashboard_server.app.test_client().get("/dashboard-config.js")

    assert response.status_code == 200
    assert response.mimetype == "application/javascript"
    expected_payload = surface_config_payload()
    assert PHASE1_LEGACY_DASHBOARD_TRIAL.surface_id in response.get_data(as_text=True)
    assert json.dumps(expected_payload, ensure_ascii=False, sort_keys=True) in response.get_data(
        as_text=True
    )


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
