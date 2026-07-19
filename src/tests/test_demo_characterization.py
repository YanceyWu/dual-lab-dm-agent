from __future__ import annotations

import os
import shutil
import sqlite3
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

from pm_agent.config import settings
from pm_agent.dashboard import server as dashboard_server
from pm_agent.database import repository
from pm_agent.use_cases.hiref_management import HirefManagementService
from pm_agent.use_cases.team_workload import TeamWorkloadService
from pm_agent.use_cases.weekly_report import WeeklyReportService
from tools.check_synthetic_samples import validate_text


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def built_demo_db(tmp_path_factory: pytest.TempPathFactory) -> Path:
    build_root = tmp_path_factory.mktemp("synthetic-demo-build")
    db_path = build_root / "sample_pm.db"
    environment = {
        "PATH": os.environ.get("PATH", ""),
        "PYTHONPATH": str(ROOT),
        "DATABASE_PATH": str(db_path),
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "load_sample_data.py"),
            "--db",
            str(db_path),
        ],
        cwd=ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    return db_path


@pytest.fixture
def demo_db(
    built_demo_db: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    db_path = tmp_path / "characterization.db"
    shutil.copy2(built_demo_db, db_path)
    monkeypatch.setattr(settings, "database_path", str(db_path))
    monkeypatch.setattr(dashboard_server, "DB", str(db_path))
    return db_path


def test_clean_demo_build_has_expected_canonical_counts(demo_db: Path) -> None:
    connection = sqlite3.connect(demo_db)
    try:
        counts = {
            table: connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
            for table in (
                "employees",
                "projects",
                "assignments",
                "monthly_allocations",
                "hiref",
                "change_requests",
                "jira_board_configs",
                "confluence_pages",
            )
        }
    finally:
        connection.close()

    assert counts == {
        "employees": 4,
        "projects": 3,
        "assignments": 4,
        "monthly_allocations": 48,
        "hiref": 2,
        "change_requests": 3,
        "jira_board_configs": 3,
        "confluence_pages": 3,
    }


def test_demo_identity_and_project_language_is_explicitly_synthetic(demo_db: Path) -> None:
    connection = sqlite3.connect(demo_db)
    try:
        people = connection.execute("SELECT id, name, email FROM employees ORDER BY id").fetchall()
        projects = connection.execute("SELECT id, name FROM projects ORDER BY id").fetchall()
    finally:
        connection.close()

    assert people == [
        ("990001", "Alex Example", "alex.example@example.invalid"),
        ("990002", "Blair Example", "blair.example@example.invalid"),
        ("990003", "Casey Example", "casey.example@example.invalid"),
        ("990004", "Drew Example", "drew.example@example.invalid"),
    ]
    assert projects == [
        ("project-atlas-9901001", "Project Atlas"),
        ("project-beacon-9901002", "Project Beacon"),
        ("project-cedar-9901003", "Project Cedar"),
    ]
    assert validate_text("SYNTHETIC_DATASET_V1 " + repr(people + projects), "demo") == []


def test_demo_workload_and_monthly_capacity_semantics(demo_db: Path) -> None:
    response = TeamWorkloadService().overview()
    assert response.success is True
    assert response.data["stats"] == {
        "total": 4,
        "available": 2,
        "overloaded": 0,
        "avg_load": 0.68,
        "max_load": 0.8,
    }

    connection = sqlite3.connect(demo_db)
    try:
        july = connection.execute(
            """
            SELECT employee_id, allocation
            FROM monthly_allocations
            WHERE month = 7
            ORDER BY employee_id
            """
        ).fetchall()
    finally:
        connection.close()
    assert july == [("990001", 0.8), ("990002", 0.5), ("990003", 0.8), ("990004", 0.6)]


def test_demo_hiref_and_weekly_report_semantics(demo_db: Path) -> None:
    hiref = HirefManagementService().summary(days=365)
    assert hiref.success is True
    assert hiref.data["summary"]["active_stfte"] == 2
    assert hiref.data["summary"]["open_placeholders"] == 1

    weekly = WeeklyReportService().weekly(reference_date=date(2026, 7, 19))
    assert weekly.success is True
    assert weekly.data["week"] == "2026-W29"
    assert len(weekly.data["raw"]["projects"]) == 3
    assert len(weekly.data["raw"]["members"]) == 4
    for project_name in ("Project Atlas", "Project Beacon", "Project Cedar"):
        assert project_name in weekly.data["report"]


def test_demo_use_case_catalog_and_project_list_semantics(demo_db: Path) -> None:
    projects = repository.get_all_projects()
    assert [project["name"] for project in projects] == [
        "Project Atlas",
        "Project Beacon",
        "Project Cedar",
    ]

    use_cases = repository.get_use_cases(status="active")
    use_case_ids = {item["id"] for item in use_cases}
    assert {"resource-allocation", "weekly-project-status", "hiref-renewal"} <= use_case_ids


def test_demo_dashboard_summary_and_health_are_offline(demo_db: Path) -> None:
    client = dashboard_server.app.test_client()
    summary = client.get("/api/summary")
    health = client.get("/api/project-health")

    assert summary.status_code == 200
    assert health.status_code == 200
    assert summary.get_json()["total_staff"] == 4
    health_payload = health.get_json()
    assert {item["name"] for item in health_payload} >= {
        "Project Atlas",
        "Project Beacon",
        "Project Cedar",
    }
