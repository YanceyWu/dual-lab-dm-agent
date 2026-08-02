from __future__ import annotations

import os
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from pm_agent.config import settings
from pm_agent.dashboard import server as dashboard_server
from pm_agent.database import repository
from pm_agent.use_cases import use_case_executor
from pm_agent.use_cases.service import UseCaseRequest
from tools.check_synthetic_samples import validate_text


ROOT = Path(__file__).resolve().parents[1]
DEMO_PROJECT = "project-synthetic-atlas"
CAPACITY_PARAMS = {
    "year": 2026,
    "month": 8,
    "plan_version_id": "plan-synthetic-baseline-001",
}


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
            "--force",
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


def _count(db_path: Path, table: str) -> int:
    with sqlite3.connect(db_path) as connection:
        return connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]


def test_clean_demo_build_has_expected_clean_import_counts(demo_db: Path) -> None:
    counts = {
        table: _count(demo_db, table)
        for table in (
            "employees",
            "projects",
            "assignments",
            "monthly_allocations",
            "plan_versions",
            "hiref",
            "jira_board_configs",
            "confluence_pages",
        )
    }
    assert counts == {
        "employees": 2,
        "projects": 2,
        "assignments": 2,
        "monthly_allocations": 2,
        "plan_versions": 2,
        "hiref": 0,
        "jira_board_configs": 1,
        "confluence_pages": 0,
    }
    assert _count(demo_db, "action_items") == 1
    assert _count(demo_db, "source_evidence_runs") == 2
    assert _count(demo_db, "jira_issues") == 3
    assert _count(demo_db, "jira_stream_versions") == 1
    assert _count(demo_db, "jira_sprints") == 1
    assert _count(demo_db, "jira_health_snapshots") == 1
    assert _count(demo_db, "confluence_status_snapshots") == 1


def test_demo_identity_is_explicitly_synthetic(demo_db: Path) -> None:
    with sqlite3.connect(demo_db) as connection:
        people = connection.execute("SELECT id, name FROM employees ORDER BY id").fetchall()
        projects = connection.execute("SELECT id, name, status FROM projects ORDER BY id").fetchall()
    assert people == [
        ("member-synthetic-001", "Synthetic Member 001"),
        ("member-synthetic-002", "Synthetic Member 002"),
    ]
    assert projects == [
        ("project-synthetic-atlas", "Synthetic Project Atlas", "active"),
        ("project-synthetic-beacon", "Synthetic Project Beacon", "inactive"),
    ]
    assert validate_text("SYNTHETIC_DATASET_V1 " + repr(people + projects), "demo") == []


def test_demo_clean_import_capacity_semantics(demo_db: Path) -> None:
    with sqlite3.connect(demo_db) as connection:
        rows = connection.execute(
            """
            SELECT employee_id, allocation
            FROM monthly_allocations
            WHERE year = 2026 AND month = 8
            ORDER BY employee_id
            """
        ).fetchall()
    assert rows == [("member-synthetic-001", 0.5), ("member-synthetic-002", 0.0)]

    heatmap = use_case_executor.execute(
        UseCaseRequest(
            use_case_id="resource-capacity-heatmap",
            parameters=dict(CAPACITY_PARAMS),
        )
    )
    assert heatmap.status == "success"
    assert [row["member_id"] for row in heatmap.data["rows"]] == [
        "member-synthetic-001",
        "member-synthetic-002",
    ]
    assert {row["state"] for row in heatmap.data["rows"]} == {"known"}


def test_demo_five_capability_commands_return_nonempty_contract_results(demo_db: Path) -> None:
    layered = use_case_executor.execute(
        UseCaseRequest(
            use_case_id="layered-project-health-review",
            parameters={"project_id": DEMO_PROJECT},
        )
    )
    assert layered.status == "success"
    assert layered.data["assessments"]
    assert layered.data["assessments"][0]["project_id"] == DEMO_PROJECT
    assert layered.data["assessments"][0]["state"] == "red"
    assert layered.signals
    assert layered.signals[0].signal_type == "layered_project_health_state"

    execution = use_case_executor.execute(
        UseCaseRequest(
            use_case_id="delivery-execution-review",
            parameters={"project_id": DEMO_PROJECT},
        )
    )
    assert execution.status == "success"
    assert execution.data["sprint_execution"]
    assert len(execution.data["release_milestone"]) >= 7
    assert {"milestone", "release"} <= {item["subject"]["kind"] for item in execution.data["release_milestone"]}
    assert execution.signals

    attention = use_case_executor.execute(
        UseCaseRequest(use_case_id="delivery-attention-center")
    )
    assert attention.status == "success"
    assert attention.data["items"]
    assert attention.data["reconciliation_coverage"]["status"] in {"complete", "partial"}
    rule_keys = {item["rule_key"] for item in attention.data["items"]}
    assert len(attention.data["items"]) >= 5
    assert {
        "project_health_attention",
        "critical_milestone_overdue_attention",
        "resource_overload_attention",
        "overdue_action_attention",
        "source_freshness_attention",
    } <= rule_keys

    heatmap = use_case_executor.execute(
        UseCaseRequest(
            use_case_id="resource-capacity-heatmap",
            parameters=dict(CAPACITY_PARAMS),
        )
    )
    assert heatmap.status == "success"
    assert len(heatmap.data["rows"]) == 2

    brief = use_case_executor.execute(
        UseCaseRequest(
            contract_version="2.0",
            use_case_id="weekly-dm-brief-v2",
            parameters={},
        )
    )
    assert brief.status == "success"
    assert brief.contract_version == "2.0"
    assert brief.data["summary"]["project_count"] == 1
    assert brief.data["summary"]["overall_state"] == "red"
    assert brief.data["sections"]["highest_attention_signals"]["items"]
    assert len(brief.data["sections"]["highest_attention_signals"]["items"]) >= 5
    assert brief.data["sections"]["next_actions"]["items"]


def test_demo_reimport_produces_completed_assessment(demo_db: Path) -> None:
    assert _count(demo_db, "project_health_reimport_assessments") == 1
    assert _count(demo_db, "project_health_assessment_runs") == 1
    layered = use_case_executor.execute(
        UseCaseRequest(
            use_case_id="layered-project-health-review",
            parameters={"project_id": DEMO_PROJECT},
        )
    )
    assert layered.data["assessments"][0]["state"] == "red"
    assert layered.data["assessments"][0]["dimensions"] == {
        "schedule": "red",
        "delivery": "not_available",
        "scope": "amber",
        "quality": "not_available",
        "resource": "not_available",
        "dependency": "unknown",
        "governance": "not_available",
    }


def test_demo_replay_is_idempotent(built_demo_db: Path, tmp_path: Path) -> None:
    replay_db = tmp_path / "replay.db"
    shutil.copy2(built_demo_db, replay_db)
    environment = {
        "PATH": os.environ.get("PATH", ""),
        "PYTHONPATH": str(ROOT),
        "DATABASE_PATH": str(replay_db),
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    tables = (
        "project_health_reimport_assessments",
        "project_health_assessment_runs",
        "attention_signals",
        "execution_derivation_runs",
        "execution_milestones",
        "weekly_brief_snapshot_operations",
        "workforce_planning_import_sessions",
        "resource_capacity_import_sessions",
        "project_health_reimport_sessions",
        "milestone_import_operations",
        "source_evidence_runs",
        "jira_issue_events",
        "jira_issues",
        "action_items",
        "assignments",
        "projects",
    )
    before = {table: _count(replay_db, table) for table in tables}
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "load_sample_data.py"),
            "--db",
            str(replay_db),
            "--replay",
        ],
        cwd=ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    after = {table: _count(replay_db, table) for table in tables}
    assert before == after
    with sqlite3.connect(replay_db) as connection:
        confirmed = connection.execute(
            "SELECT COUNT(*) FROM weekly_brief_snapshot_operations WHERE status='confirmed'"
        ).fetchone()[0]
    assert confirmed == 1


def test_demo_use_case_catalog_and_project_list_semantics(demo_db: Path) -> None:
    projects = repository.get_all_projects()
    assert [project["name"] for project in projects] == [
        "Synthetic Project Atlas",
        "Synthetic Project Beacon",
    ]

    use_case_ids = {item.use_case_id for item in use_case_executor.list_descriptors()}
    assert {
        "layered-project-health-review",
        "delivery-execution-review",
        "delivery-attention-center",
        "resource-capacity-heatmap",
        "weekly-dm-brief-v2",
    } <= use_case_ids


def test_demo_dashboard_summary_and_health_are_offline(demo_db: Path) -> None:
    client = dashboard_server.app.test_client()
    summary = client.get("/api/summary")
    health = client.get("/api/project-health")
    assert summary.status_code == 200
    assert health.status_code == 200
    assert summary.get_json()["total_staff"] == 2
    health_payload = health.get_json()
    assert isinstance(health_payload, list)
    assert health_payload
    assert health_payload[0]["health"]["board_id"] == "atlas-board"
