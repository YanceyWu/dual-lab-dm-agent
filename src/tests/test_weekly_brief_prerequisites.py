from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone

import pytest

from pm_agent.action.read_model import list_action_records
from pm_agent.attention import AttentionService
from pm_agent.attention.read_model import current_attention
from pm_agent.database.bootstrap import main as init_db
from pm_agent.database.execution_review import list_latest_execution_facts
from pm_agent.project_identity.read_model import active_project_manifest
from pm_agent.use_cases import use_case_executor
from pm_agent.use_cases.service import UseCaseRequest


def test_active_project_manifest_is_canonical_bounded_and_fail_closed(isolated_db) -> None:
    init_db(quiet=True)
    with sqlite3.connect(isolated_db) as connection:
        connection.executemany(
            """INSERT INTO projects(id,name,status,priority,updated_at)
               VALUES(?,?,?,?,?)""",
            [
                ("project-brief-1002", "Synthetic Two", "active", 2, "2026-08-01 02:00:00"),
                ("project-brief-1001", "Synthetic One", "active", 1, "2026-08-01 01:00:00"),
                ("project-brief-1003", "Synthetic Done", "done", 1, "2026-08-01 03:00:00"),
            ],
        )

    global_manifest = active_project_manifest(db_path=isolated_db)
    exact_manifest = active_project_manifest(
        project_ids=["project-brief-1002", "project-brief-1001"],
        db_path=isolated_db,
    )

    assert global_manifest["coverage"] == {
        "state": "complete",
        "basis": "canonical_local_project_catalog",
        "active_project_count": 2,
        "selected_project_count": 2,
    }
    assert [item["project_id"] for item in global_manifest["projects"]] == [
        "project-brief-1001",
        "project-brief-1002",
    ]
    assert exact_manifest["scope"]["project_ids"] == [
        "project-brief-1001",
        "project-brief-1002",
    ]
    assert all("name" not in item for item in global_manifest["projects"])
    with pytest.raises(ValueError, match="PROJECT_NOT_FOUND"):
        active_project_manifest(
            project_ids=["project-brief-missing"],
            db_path=isolated_db,
        )
    with sqlite3.connect(isolated_db) as connection:
        connection.executemany(
            "INSERT INTO projects(id,name,status) VALUES(?,?,'active')",
            [
                (f"project-brief-bounded-{index:04d}", "Synthetic Bounded")
                for index in range(199)
            ],
        )
    unavailable = active_project_manifest(db_path=isolated_db)
    assert unavailable["projects"] == []
    assert unavailable["coverage"]["state"] == "unavailable"
    assert unavailable["limitations"] == ["PROJECT_MANIFEST_LIMIT_EXCEEDED"]


def test_action_reader_exposes_completion_and_never_infers_project(isolated_db) -> None:
    init_db(quiet=True)
    with sqlite3.connect(isolated_db) as connection:
        connection.executemany(
            """INSERT INTO action_items
                   (title,priority,status,due_date,created_at,completed_at)
               VALUES(?,?,?,?,?,?)""",
            [
                (
                    "Synthetic overdue action",
                    "high",
                    "open",
                    "2026-07-01",
                    "2026-06-01T00:00:00+00:00",
                    None,
                ),
                (
                    "Synthetic completed action",
                    "medium",
                    "done",
                    "2026-07-20",
                    "2026-06-01T00:00:00+00:00",
                    "2026-07-31T12:00:00+00:00",
                ),
                (
                    "Synthetic missing completion time",
                    "low",
                    "done",
                    "2026-07-20",
                    "2026-06-01T00:00:00+00:00",
                    None,
                ),
                (
                    "Synthetic future completion time",
                    "low",
                    "done",
                    "2026-07-20",
                    "2026-06-01T00:00:00+00:00",
                    "2026-08-02T00:00:00+00:00",
                ),
            ],
        )

    result = list_action_records(
        completed_since="2026-07-28T00:00:00+00:00",
        through="2026-08-01T12:00:00+00:00",
        db_path=isolated_db,
    )

    by_title = {item["title"]: item for item in result["items"]}
    overdue = by_title["Synthetic overdue action"]
    completed = by_title["Synthetic completed action"]
    assert overdue["follow_up_reasons"] == [
        "overdue",
        "missing_owner",
    ]
    assert overdue["severity"] == "high"
    assert completed["completion_state"] == "known"
    assert completed["completed_at"] == "2026-07-31T12:00:00+00:00"
    assert by_title["Synthetic missing completion time"]["completion_state"] == (
        "unavailable"
    )
    assert by_title["Synthetic future completion time"]["limitations"] == [
        "ACTION_COMPLETION_AFTER_BOUNDARY"
    ]
    assert result["coverage"] == {
        "state": "partial",
        "basis": "recorded_action_items",
        "record_count": 4,
        "limitation_codes": [
            "ACTION_COMPLETION_AFTER_BOUNDARY",
            "ACTION_COMPLETION_TIME_INVALID",
        ],
    }
    assert all(
        item["project_association"]["state"] == "unavailable"
        for item in result["items"]
    )
    assert all("owner_name" not in item for item in result["items"])
    with pytest.raises(ValueError, match="ACTION_STATUSES_INVALID"):
        list_action_records(statuses=[], db_path=isolated_db)
    with pytest.raises(ValueError, match="ACTION_COMPLETION_WINDOW_INVALID"):
        list_action_records(
            completed_since="2026-08-02T00:00:00+00:00",
            through="2026-08-01T00:00:00+00:00",
            db_path=isolated_db,
        )
    with pytest.raises(ValueError, match="ACTION_THROUGH_INVALID"):
        list_action_records(through="not-a-time", db_path=isolated_db)


def test_attention_reader_preserves_center_order_coverage_and_history(isolated_db) -> None:
    init_db(quiet=True)
    now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds")
    with sqlite3.connect(isolated_db) as connection:
        connection.execute(
            """INSERT INTO projects(id,name,status,priority)
               VALUES('project-brief-attention','Synthetic Project','active',1)"""
        )
        connection.execute(
            """INSERT INTO jira_board_configs
                   (id,name,project_key,base_jql,pm_project_id,active)
               VALUES('board-brief-attention','Synthetic Board','SYN',
                      'project = SYN','project-brief-attention',1)"""
        )
        connection.execute(
            """INSERT INTO jira_health_snapshots
                   (board_id,snapshot_date,overall_grade)
               VALUES('board-brief-attention','2026-08-01','RED')"""
        )
        connection.executemany(
            """INSERT INTO sync_runs(id,source_id,started_at,finished_at,status)
               VALUES(?,?,?,?, 'success')""",
            [
                ("sync-brief-jira", "jira-health-board-brief-attention", now, now),
                ("sync-brief-confluence", "confluence-status-batch", now, now),
            ],
        )
    service = AttentionService(db_path=isolated_db)
    preview = service.preview_reconciliation(actor="manager-brief-1001")
    confirmed = service.confirm(
        operation_id=preview["operation_id"],
        confirmation_token=preview["confirmation_token"],
    )
    assert confirmed["status"] == "success"

    reader = current_attention(
        include_history=True,
        limit=50,
        db_path=isolated_db,
    )
    center = use_case_executor.execute(
        UseCaseRequest(
            use_case_id="delivery-attention-center",
            parameters={"include_history": True, "limit": 50},
        )
    )

    assert reader["reconciliation_coverage"] == center.data["reconciliation_coverage"]
    assert [item["attention_id"] for item in reader["items"]] == [
        item["attention_id"] for item in center.data["items"]
    ]
    project_item = next(
        item for item in reader["items"] if item["subject"]["kind"] == "project"
    )
    assert project_item["project_association"] == {
        "state": "known",
        "project_id": "project-brief-attention",
        "basis": "project_subject",
    }
    assert project_item["recent_events"]
    assert all("token_hash" not in item for item in reader["items"])
    with pytest.raises(ValueError, match="ATTENTION_STATES_INVALID"):
        current_attention(attention_states=[], db_path=isolated_db)

    with sqlite3.connect(isolated_db) as connection:
        connection.execute(
            """INSERT INTO attention_operations
                   (operation_id,action,actor,status,scope_json,token_hash,
                    created_at,expires_at,finished_at)
               VALUES('attop-brief-failed','reconcile','manager-brief-1001','failed',
                      '{"rule_keys":null,"subject_kind":null,"subject_id":null}',
                      'hash-brief-failed','2026-08-01T10:00:00+00:00',
                      '2026-08-01T10:05:00+00:00','9999-08-01T10:00:01+00:00')"""
        )
        connection.execute(
            """INSERT INTO attention_reconciliations
                   (reconciliation_id,operation_id,status,actor,started_at,
                    finished_at,rule_set_version,warning_codes_json)
               VALUES('rec-brief-failed','attop-brief-failed','failed',
                      'manager-brief-1001','2026-08-01T10:00:00+00:00',
                      '9999-08-01T10:00:01+00:00','attention-rules-v1',
                      '["ATTENTION_DATA_ACCESS_FAILED"]')"""
        )
    failed_reader = current_attention(db_path=isolated_db)
    failed_center = use_case_executor.execute(
        UseCaseRequest(use_case_id="delivery-attention-center")
    )
    assert failed_reader["reconciliation_coverage"]["status"] == "unavailable"
    assert failed_reader["reconciliation_coverage"] == (
        failed_center.data["reconciliation_coverage"]
    )
    assert "ATTENTION_RECONCILIATION_FAILED" in failed_center.warnings


def test_execution_reader_publishes_exact_milestone_event_time(isolated_db) -> None:
    init_db(quiet=True)
    with sqlite3.connect(isolated_db) as connection:
        connection.execute(
            """INSERT INTO projects(id,name,status)
               VALUES('project-brief-execution','Synthetic Project','active')"""
        )
        connection.execute(
            """INSERT INTO execution_milestones
                   (milestone_id,project_id,milestone_type,criticality,lifecycle_state,
                    planned_date,actual_date,authority,completeness_state,observed_at,
                    schema_version)
               VALUES('milestone-brief-1001','project-brief-execution','release','critical',
                      'achieved','2026-07-30','2026-08-02','manager_approved','complete',
                      '2026-08-02T09:00:00+00:00','execution-milestone-import-v1')"""
        )
        connection.execute(
            """INSERT INTO execution_derivation_runs
                   (derivation_run_id,project_id,board_id,rule_version,input_fingerprint,
                    completeness_state,freshness_state,started_at,finished_at)
               VALUES('brief-run-1001','project-brief-execution','board-brief-1001',
                      'execution-foundation-v1','brief-fingerprint-1001','complete','fresh',
                      '2026-07-31T09:01:00+00:00','2026-07-31T09:02:00+00:00')"""
        )
        connection.execute(
            """INSERT INTO execution_facts
                   (fact_id,derivation_run_id,project_id,subject_kind,subject_id,fact_key,
                    value_json,value_state,freshness_state,evidence_json)
               VALUES('brief-fact-1001','brief-run-1001','project-brief-execution',
                      'milestone','milestone-brief-1001','milestone_adherence',?,
                      'known','fresh',?)""",
            [json.dumps("achieved_late"), json.dumps({"actual_date": "2026-07-31"})],
        )

    rows = list_latest_execution_facts(
        "project-brief-execution",
        layer="release_milestone",
        subject_kind="milestone",
        subject_id=None,
        since="2026-07-01T00:00:00+00:00",
        limit=20,
        db_path=isolated_db,
    )
    assert rows[0]["fact_observed_at"] == "2026-07-31T09:02:00+00:00"
    assert rows[0]["event_occurred_at"] == "2026-07-31"
    assert rows[0]["event_time_precision"] == "date"
    assert rows[0]["event_time_basis"] == "fact_derivation_evidence"

    result = use_case_executor.execute(
        UseCaseRequest(
            use_case_id="delivery-execution-review",
            parameters={
                "project_id": "project-brief-execution",
                "layer": "release_milestone",
                "subject_kind": "milestone",
            },
        )
    )
    item = result.data["release_milestone"][0]
    assert item["fact_observed_at"] == "2026-07-31T09:02:00+00:00"
    assert item["event_occurred_at"] == "2026-07-31"
    assert item["event_time_precision"] == "date"
    assert result.evidence[0]["event_time"] == {
        "state": "known",
        "occurred_at": "2026-07-31",
        "precision": "date",
        "basis": "fact_derivation_evidence",
    }
    with sqlite3.connect(isolated_db) as connection:
        connection.execute(
            """UPDATE execution_facts SET evidence_json=?
               WHERE fact_id='brief-fact-1001'""",
            [json.dumps({"actual_date": "not-a-date"})],
        )
    invalid_time = list_latest_execution_facts(
        "project-brief-execution",
        layer="release_milestone",
        subject_kind="milestone",
        subject_id=None,
        since="2026-07-01T00:00:00+00:00",
        limit=20,
        db_path=isolated_db,
    )[0]
    assert invalid_time["event_time_state"] == "not_available"
    assert "EXECUTION_EVENT_TIME_NOT_AVAILABLE" in invalid_time["warning_codes"]
    with sqlite3.connect(isolated_db) as connection:
        connection.execute(
            """UPDATE execution_facts SET evidence_json='[]'
               WHERE fact_id='brief-fact-1001'"""
        )
    non_object_evidence = list_latest_execution_facts(
        "project-brief-execution",
        layer="release_milestone",
        subject_kind="milestone",
        subject_id=None,
        since="2026-07-01T00:00:00+00:00",
        limit=20,
        db_path=isolated_db,
    )[0]
    assert non_object_evidence["event_time_state"] == "not_available"
