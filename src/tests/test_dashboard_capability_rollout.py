from __future__ import annotations

import sqlite3
from pathlib import Path

from pm_agent.dashboard import server as dashboard_server
from pm_agent.database.bootstrap import main as init_db


def test_dashboard_shell_lists_promoted_capability_sections() -> None:
    index_path = (
        Path(__file__).resolve().parents[1]
        / "pm_agent"
        / "dashboard"
        / "web"
        / "index.html"
    )
    html = index_path.read_text(encoding="utf-8")

    for token in (
        "section-attention",
        "section-weekly-brief",
        "section-capacity",
        "section-execution",
        "section-layered-health",
        "section-connectors",
        "section-snapshots",
        "/js/usecase-components.js",
        "/js/section-intelligence.js",
    ):
        assert token in html


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
