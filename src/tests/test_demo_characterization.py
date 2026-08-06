from __future__ import annotations

import os
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

from contract_coverage_test_helpers import publish_contract_coverage_from_legacy

import pytest

from current_state_staffing_test_helpers import publish_current_state_staffing_from_legacy
from pm_agent.attention import AttentionService
from pm_agent.config import settings
from pm_agent.dashboard import server as dashboard_server
from pm_agent.database import repository
from pm_agent.use_cases import use_case_executor
from pm_agent.use_cases.hiref_management import HirefManagementService
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
    publish_current_state_staffing_from_legacy(
        db_path,
        package_id="package-demo-current-state-r1",
    )
    attention_preview = AttentionService().preview_reconciliation(actor="demo-fixture")
    AttentionService().confirm(
        operation_id=attention_preview["operation_id"],
        confirmation_token=attention_preview["confirmation_token"],
    )
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
        "employees": 3,
        "projects": 2,
        "assignments": 3,
        "monthly_allocations": 6,
        "plan_versions": 2,
        "hiref": 4,
        "jira_board_configs": 2,
        "confluence_pages": 0,
    }
    assert _count(demo_db, "action_items") == 1
    assert _count(demo_db, "source_evidence_runs") == 2
    assert _count(demo_db, "jira_issues") == 3
    assert _count(demo_db, "jira_stream_versions") == 1
    assert _count(demo_db, "jira_sprints") == 1
    assert _count(demo_db, "jira_health_snapshots") == 2
    assert _count(demo_db, "confluence_status_snapshots") == 2
    assert _count(demo_db, "hiref") == 4
    assert _count(demo_db, "staffing_placeholders") == 1


def test_load_sample_data_honors_db_argument_without_database_path_env(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "argument-only-demo.db"
    environment = {
        "PATH": os.environ.get("PATH", ""),
        "PYTHONPATH": str(ROOT),
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
    assert _count(db_path, "plan_versions") == 2


def test_demo_identity_is_explicitly_synthetic(demo_db: Path) -> None:
    with sqlite3.connect(demo_db) as connection:
        people = connection.execute("SELECT id, name FROM employees ORDER BY id").fetchall()
        projects = connection.execute("SELECT id, name, status FROM projects ORDER BY id").fetchall()
    assert people == [
        ("member-synthetic-001", "Synthetic Member 001"),
        ("member-synthetic-002", "Synthetic Member 002"),
        ("member-synthetic-003", "Synthetic Member 003"),
    ]
    assert projects == [
        ("project-synthetic-atlas", "Synthetic Project Atlas", "active"),
        ("project-synthetic-beacon", "Synthetic Project Beacon", "active"),
    ]
    assert validate_text("SYNTHETIC_DATASET_V1 " + repr(people + projects), "demo") == []


def test_demo_clean_import_capacity_semantics(demo_db: Path) -> None:
    with sqlite3.connect(demo_db) as connection:
        allocations = connection.execute(
            """
            SELECT employee_id, project_id, allocation
            FROM monthly_allocations
            WHERE year = 2026 AND month = 8
            ORDER BY employee_id, project_id
            """
        ).fetchall()
    assert allocations == [
        ("member-synthetic-001", "project-synthetic-atlas", 0.5),
        ("member-synthetic-001", "project-synthetic-beacon", 0.0),
        ("member-synthetic-002", "project-synthetic-atlas", 0.0),
        ("member-synthetic-002", "project-synthetic-beacon", 0.0),
        ("member-synthetic-003", "project-synthetic-atlas", 0.6),
        ("member-synthetic-003", "project-synthetic-beacon", 0.6),
    ]
    with sqlite3.connect(demo_db) as connection:
        loads = connection.execute(
            """
            SELECT employee_id, ROUND(SUM(allocation), 2)
            FROM assignments WHERE status = 'active'
            GROUP BY employee_id ORDER BY employee_id
            """
        ).fetchall()
    assert loads == [
        ("member-synthetic-001", 0.5),
        ("member-synthetic-003", 1.2),
    ]

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
        "member-synthetic-003",
    ]
    assert {row["state"] for row in heatmap.data["rows"]} == {"known"}
    by_member = {row["member_id"]: row for row in heatmap.data["rows"]}
    assert by_member["member-synthetic-003"]["overload_state"] == "red"
    assert by_member["member-synthetic-001"]["overload_state"] == "clear"


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
    all_assessments = use_case_executor.execute(
        UseCaseRequest(use_case_id="layered-project-health-review")
    )
    assert {item["project_id"] for item in all_assessments.data["assessments"]} == {
        "project-synthetic-atlas",
        "project-synthetic-beacon",
    }

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
    assert len(attention.data["items"]) >= 7
    assert {
        "project_health_attention",
        "critical_milestone_overdue_attention",
        "resource_overload_attention",
        "overdue_action_attention",
        "source_freshness_attention",
    } <= rule_keys
    assert {
        item["subject"]["id"]
        for item in attention.data["items"]
        if item["rule_key"] == "project_health_attention"
    } == {"project-synthetic-atlas", "project-synthetic-beacon"}

    heatmap = use_case_executor.execute(
        UseCaseRequest(
            use_case_id="resource-capacity-heatmap",
            parameters=dict(CAPACITY_PARAMS),
        )
    )
    assert heatmap.status == "success"
    assert len(heatmap.data["rows"]) == 3

    brief = use_case_executor.execute(
        UseCaseRequest(
            contract_version="2.0",
            use_case_id="weekly-dm-brief-v2",
            parameters={},
        )
    )
    assert brief.status == "success"
    assert brief.contract_version == "2.0"
    assert brief.data["summary"]["project_count"] == 2
    assert brief.data["summary"]["overall_state"] == "red"
    assert brief.data["sections"]["highest_attention_signals"]["items"]
    assert len(brief.data["sections"]["highest_attention_signals"]["items"]) >= 7
    assert brief.data["sections"]["next_actions"]["items"]


def test_demo_reimport_produces_completed_assessment(demo_db: Path) -> None:
    assert _count(demo_db, "project_health_reimport_assessments") == 2
    assert _count(demo_db, "project_health_assessment_runs") == 2
    layered = use_case_executor.execute(
        UseCaseRequest(use_case_id="layered-project-health-review")
    )
    atlas = next(item for item in layered.data["assessments"] if item["project_id"] == DEMO_PROJECT)
    beacon = next(item for item in layered.data["assessments"] if item["project_id"] == "project-synthetic-beacon")
    assert atlas["state"] == "red"
    assert atlas["dimensions"] == {
        "schedule": "red",
        "delivery": "not_available",
        "scope": "amber",
        "quality": "not_available",
        "resource": "not_available",
        "dependency": "unknown",
        "governance": "not_available",
    }
    assert beacon["state"] == "unknown"
    assert beacon["dimensions"]["schedule"] == "unknown"


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
        "jira_health_snapshots",
        "confluence_status_snapshots",
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
    assert summary.get_json()["total_staff"] == 3
    assert summary.get_json()["current_state_staffing_state"] == "known"
    assert summary.get_json()["current_state_staffing_freshness_state"] == "fresh"
    health_payload = health.get_json()
    assert isinstance(health_payload, list)
    assert health_payload
    assert {item["health"]["board_id"] for item in health_payload} == {
        "atlas-board",
        "beacon-board",
    }


def test_demo_hiref_and_contract_continuity_show_multiple_states(demo_db: Path) -> None:
    publish_contract_coverage_from_legacy(
        demo_db,
        package_id="package-demo-contract-coverage-r1",
    )
    summary = HirefManagementService().summary(days=180)
    assert summary.success is True
    stats = summary.data["summary"]
    assert summary.data["freshness"]["state"] == "partial"
    assert stats["active_stfte"] is None
    assert stats["missing_current_hiref"] is None
    assert stats["expiring_without_next"] is None
    assert stats["expiring_with_next"] is None
    assert stats["free_slots"] is None
    assert stats["open_placeholders"] >= 1

    review = HirefManagementService().review(days=180)
    assert review.success is True
    assert review.data["rows"]
    assert any(row["requires_action"] for row in review.data["rows"])

    slots = HirefManagementService().slots()
    assert slots.success is True
    assert any(row["occupancy_status"] == "unknown" for row in slots.data["rows"])

    placeholders = HirefManagementService().placeholders()
    assert placeholders.success is True
    assert placeholders.data["rows"]

    continuity = use_case_executor.execute(
        UseCaseRequest(use_case_id="contract-continuity-review")
    )
    assert continuity.status == "success"
    assert continuity.freshness[0]["state"] == "partial"
    assert continuity.data["contracts"]
    assert continuity.data["summary"]["attention_count"] is None
    assert continuity.data["summary"]["reviewed_count"] is None
