from __future__ import annotations

import hashlib
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pytest

from current_state_staffing_test_helpers import publish_current_state_staffing_from_legacy
from pm_agent.attention import AttentionService
from pm_agent.database.bootstrap import (
    _migrate_attention_signal_evaluation_hash,
    main as init_db,
)


def _now_text() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _seed_attention_scenario(database_path) -> None:
    init_db(quiet=True)
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            INSERT INTO employees (id, wd_id, name, status)
            VALUES ('member-990101', 'member-990101', 'Synthetic Member', 'active')
            """
        )
        connection.executemany(
            """
            INSERT INTO projects (id, name, status, priority)
            VALUES (?, ?, 'active', ?)
            """,
            [
                ("project-990001", "Synthetic Project 1", 1),
                ("project-990002", "Synthetic Project 2", 2),
            ],
        )
        connection.execute(
            """
            INSERT INTO projects (id, name, status, priority)
            VALUES (
                'project-990003', 'Synthetic Inactive Project', 'done', 3
            )
            """
        )
        connection.execute(
            """
            INSERT INTO jira_board_configs
                (id, name, project_key, base_jql, pm_project_id, active)
            VALUES (
                'board-990001', 'Synthetic Board', 'SYN',
                'project = SYN', 'project-990001', 1
            )
            """
        )
        connection.execute(
            """
            INSERT INTO jira_health_snapshots
                (board_id, snapshot_date, overall_grade)
            VALUES ('board-990001', '2026-07-28', 'RED')
            """
        )
        connection.execute(
            """
            INSERT INTO jira_board_configs
                (id, name, project_key, base_jql, pm_project_id, active)
            VALUES (
                'board-990003', 'Synthetic Inactive Board', 'OLD',
                'project = OLD', 'project-990003', 1
            )
            """
        )
        connection.execute(
            """
            INSERT INTO action_items
                (title, owner_id, priority, status, due_date)
            VALUES (
                'Synthetic overdue follow-up', 'member-990101',
                'high', 'open', '2000-01-01'
            )
            """
        )
        connection.executemany(
            """
            INSERT INTO assignments
                (employee_id, project_id, allocation, status)
            VALUES ('member-990101', ?, ?, 'active')
            """,
            [
                ("project-990001", 0.6),
                ("project-990002", 0.5),
            ],
        )
        connection.execute(
            """
            INSERT INTO data_sources
                (id, source_type, source_name, refresh_sla_hours, active)
            VALUES (
                'jira-health-board-990001', 'jira',
                'Synthetic Jira Health', 24, 1
            )
            ON CONFLICT(id) DO UPDATE SET active = 1, refresh_sla_hours = 24
            """
        )
        connection.executemany(
            """
            INSERT INTO sync_runs
                (id, source_id, started_at, finished_at, status)
            VALUES (?, ?, ?, ?, 'success')
            """,
            [
                (
                    "sync-confluence-fresh-990001",
                    "confluence-status-batch",
                    _now_text(),
                    _now_text(),
                ),
                (
                    "sync-jira-stale-990001",
                    "jira-health-board-990001",
                    "2000-01-01T00:00:00+00:00",
                    "2000-01-01T00:00:01+00:00",
                ),
            ],
        )
        connection.execute(
            """
            INSERT INTO decision_log
                (type, description, context, chosen, outcome, created_by)
            VALUES (
                'manual', 'Synthetic decision', '{}', '{}',
                'pending', 'synthetic-user'
            )
            """
        )
    publish_current_state_staffing_from_legacy(
        database_path,
        package_id="package-attention-scenario-current-state-r1",
    )


def _confirm_reconciliation(
    service: AttentionService,
    *,
    actor: str = "manager-990001",
    rule_keys: list[str] | None = None,
) -> dict:
    preview = service.preview_reconciliation(actor=actor, rule_keys=rule_keys)
    assert preview["status"] == "proposed"
    result = service.confirm(
        operation_id=preview["operation_id"],
        confirmation_token=preview["confirmation_token"],
    )
    assert result["status"] == "success"
    return result


def _restore_history_schema_without_rule_changed(
    connection: sqlite3.Connection,
) -> None:
    """Simulate the original Batch B history schema for migration coverage."""
    connection.execute(
        "ALTER TABLE attention_history RENAME TO attention_history_v2"
    )
    connection.execute(
        """
        CREATE TABLE attention_history (
            event_id              TEXT PRIMARY KEY,
            attention_id          TEXT NOT NULL
                                  REFERENCES attention_signals(attention_id),
            operation_id          TEXT NOT NULL
                                  REFERENCES attention_operations(operation_id),
            reconciliation_id     TEXT
                                  REFERENCES attention_reconciliations(
                                      reconciliation_id
                                  ),
            event_type            TEXT NOT NULL CHECK(
                event_type IN (
                    'detected', 'observed_again', 'cleared', 'reopened',
                    'acknowledged', 'snoozed', 'snooze_expired', 'resolved',
                    'evaluation_limited', 'rule_disabled'
                )
            ),
            prior_rule_state      TEXT NOT NULL DEFAULT '',
            new_rule_state        TEXT NOT NULL DEFAULT '',
            prior_attention_state TEXT NOT NULL DEFAULT '',
            new_attention_state   TEXT NOT NULL DEFAULT '',
            severity              TEXT NOT NULL,
            rule_version          TEXT NOT NULL,
            actor                 TEXT NOT NULL,
            observation_json      TEXT NOT NULL DEFAULT '{}'
                                  CHECK(json_valid(observation_json)),
            created_at            TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        INSERT INTO attention_history
        SELECT * FROM attention_history_v2
        """
    )
    connection.execute("DROP TABLE attention_history_v2")
    connection.execute(
        """
        CREATE INDEX idx_attention_history_attention_recent
        ON attention_history(attention_id, created_at DESC)
        """
    )
    connection.execute(
        """
        CREATE INDEX idx_attention_history_reconciliation
        ON attention_history(reconciliation_id, created_at)
        """
    )


def test_bootstrap_adds_attention_schema_without_backfill_and_preserves_legacy(
    isolated_db,
) -> None:
    init_db(quiet=True)
    with sqlite3.connect(isolated_db) as connection:
        connection.execute(
            """
            INSERT INTO projects (id, name, status)
            VALUES ('project-legacy-990001', 'Synthetic Legacy Project', 'active')
            """
        )
        connection.execute(
            """
            CREATE VIEW v_synthetic_legacy_project AS
            SELECT id, status FROM projects WHERE id = 'project-legacy-990001'
            """
        )

    init_db(quiet=True)
    with sqlite3.connect(isolated_db) as connection:
        attention_tables = {
            row[0]
            for row in connection.execute(
                """
                SELECT name FROM sqlite_master
                WHERE type = 'table' AND name LIKE 'attention_%'
                """
            )
        }
        legacy_row = connection.execute(
            "SELECT * FROM v_synthetic_legacy_project"
        ).fetchone()
        counts = {
            table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in (
                "attention_operations",
                "attention_configuration_operations",
                "attention_reconciliations",
                "attention_signals",
                "attention_history",
            )
        }
        violations = connection.execute("PRAGMA foreign_key_check").fetchall()

    assert attention_tables == {
        "attention_rules",
        "attention_operations",
        "attention_configuration_operations",
        "attention_reconciliations",
        "attention_signals",
        "attention_history",
    }
    assert legacy_row == ("project-legacy-990001", "active")
    assert counts == {
        "attention_operations": 0,
        "attention_configuration_operations": 0,
        "attention_reconciliations": 0,
        "attention_signals": 0,
        "attention_history": 0,
    }
    assert violations == []


def test_evaluation_hash_migration_backfills_retained_snapshot_hash() -> None:
    with sqlite3.connect(":memory:") as connection:
        connection.row_factory = sqlite3.Row
        connection.execute(
            """
            CREATE TABLE attention_signals (
                attention_id TEXT PRIMARY KEY,
                observation_hash TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            INSERT INTO attention_signals
                (attention_id, observation_hash)
            VALUES ('attn-990001', 'hash-990001')
            """
        )
        _migrate_attention_signal_evaluation_hash(connection)
        columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(attention_signals)"
            )
        }
        migrated = connection.execute(
            """
            SELECT observation_hash, last_evaluation_hash
            FROM attention_signals
            WHERE attention_id = 'attn-990001'
            """
        ).fetchone()

    assert "last_evaluation_hash" in columns
    assert tuple(migrated) == ("hash-990001", "hash-990001")


def test_bootstrap_migrates_fixed_project_health_v1_to_configurable_v2(
    isolated_db,
) -> None:
    init_db(quiet=True)
    with sqlite3.connect(isolated_db) as connection:
        connection.execute(
            """
            DELETE FROM attention_rules
            WHERE rule_key = 'project_health_attention'
            """
        )
        connection.execute(
            """
            INSERT INTO attention_rules
                (rule_key, rule_version, is_current, enabled, parameters_json,
                 created_at, updated_at)
            VALUES (
                'project_health_attention', 'project-health-attention-v1',
                1, 1, '{"health_states":["red","amber"]}',
                '2026-07-28T00:00:00+00:00',
                '2026-07-28T00:00:00+00:00'
            )
            """
        )

    init_db(quiet=True)
    with sqlite3.connect(isolated_db) as connection:
        rows = connection.execute(
            """
            SELECT rule_version, is_current, parameters_json
            FROM attention_rules
            WHERE rule_key = 'project_health_attention'
            ORDER BY rule_version
            """
        ).fetchall()

    assert [(row[0], row[1]) for row in rows] == [
        ("project-health-attention-v1", 0),
        ("project-health-attention-v2", 1),
    ]
    parameters = json.loads(rows[1][2])
    assert parameters["config_version"] == "1.0"
    assert parameters["project_overrides"] == {}


def test_bootstrap_adds_rule_changed_event_without_losing_history(
    isolated_db,
) -> None:
    _seed_attention_scenario(isolated_db)
    _confirm_reconciliation(AttentionService())
    with sqlite3.connect(isolated_db) as connection:
        history_before = connection.execute(
            "SELECT event_id, event_type FROM attention_history ORDER BY event_id"
        ).fetchall()
        _restore_history_schema_without_rule_changed(connection)

    init_db(quiet=True)
    with sqlite3.connect(isolated_db) as connection:
        history_after = connection.execute(
            "SELECT event_id, event_type FROM attention_history ORDER BY event_id"
        ).fetchall()
        schema_sql = connection.execute(
            """
            SELECT sql FROM sqlite_master
            WHERE type = 'table' AND name = 'attention_history'
            """
        ).fetchone()[0]
        indexes = {
            row[1]
            for row in connection.execute(
                "PRAGMA index_list(attention_history)"
            )
        }
        violations = connection.execute("PRAGMA foreign_key_check").fetchall()

    assert history_after == history_before
    assert "'rule_changed'" in schema_sql
    assert {
        "idx_attention_history_attention_recent",
        "idx_attention_history_reconciliation",
    } <= indexes
    assert violations == []


def test_four_active_rules_deduplicate_and_pending_decision_remains_disabled(
    isolated_db,
) -> None:
    _seed_attention_scenario(isolated_db)
    service = AttentionService()
    first = _confirm_reconciliation(service)

    with sqlite3.connect(isolated_db) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT rule_key, subject_kind, subject_id, rule_state, severity
            FROM attention_signals
            ORDER BY rule_key, subject_id
            """
        ).fetchall()
        first_history_count = connection.execute(
            "SELECT COUNT(*) FROM attention_history"
        ).fetchone()[0]
        pending_rule = connection.execute(
            """
            SELECT enabled FROM attention_rules
            WHERE rule_key = 'pending_decision_attention'
            """
        ).fetchone()[0]
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                UPDATE attention_rules SET enabled = 1
                WHERE rule_key = 'pending_decision_attention'
                """
            )

    assert first["reconciliation_status"] == "partial"
    assert {row["rule_key"] for row in rows} == {
        "project_health_attention",
        "overdue_action_attention",
        "source_freshness_attention",
        "resource_overload_attention",
    }
    assert len(rows) == 4
    assert all(row["rule_state"] == "active" for row in rows)
    assert pending_rule == 0

    second = _confirm_reconciliation(service)
    with sqlite3.connect(isolated_db) as connection:
        signal_count = connection.execute(
            "SELECT COUNT(*) FROM attention_signals"
        ).fetchone()[0]
        history_count = connection.execute(
            "SELECT COUNT(*) FROM attention_history"
        ).fetchone()[0]
    assert second["transitions"]["created_count"] == 0
    assert second["transitions"]["updated_count"] == 0
    assert signal_count == 4
    assert history_count == first_history_count

    with sqlite3.connect(isolated_db) as connection:
        connection.execute(
            """
            UPDATE attention_rules SET enabled = 0
            WHERE rule_key = 'project_health_attention' AND is_current = 1
            """
        )
    disabled = _confirm_reconciliation(
        service,
        rule_keys=["project_health_attention"],
    )
    with sqlite3.connect(isolated_db) as connection:
        disabled_signal = connection.execute(
            """
            SELECT rule_state, attention_state, evaluation_status
            FROM attention_signals
            WHERE rule_key = 'project_health_attention'
            """
        ).fetchone()
        disabled_events = connection.execute(
            """
            SELECT COUNT(*) FROM attention_history h
            JOIN attention_signals s ON s.attention_id = h.attention_id
            WHERE s.rule_key = 'project_health_attention'
              AND h.event_type = 'rule_disabled'
            """
        ).fetchone()[0]
    assert disabled["transitions"]["cleared_count"] == 0
    assert disabled["transitions"]["updated_count"] == 1
    assert disabled["transitions"]["disabled_count"] == 1
    assert disabled_signal == ("active", "open", "disabled")
    assert disabled_events == 1


def test_reconciliation_preview_token_is_hashed_one_time_and_re_evaluated(
    isolated_db,
) -> None:
    init_db(quiet=True)
    service = AttentionService()
    preview = service.preview_reconciliation(
        actor="manager-990001",
        rule_keys=["overdue_action_attention"],
    )
    assert preview["proposed"]["candidate_count"] == 0

    with sqlite3.connect(isolated_db) as connection:
        stored_hash = connection.execute(
            """
            SELECT token_hash FROM attention_operations
            WHERE operation_id = ?
            """,
            [preview["operation_id"]],
        ).fetchone()[0]
        connection.execute(
            """
            INSERT INTO action_items
                (title, priority, status, due_date)
            VALUES ('Synthetic late action', 'medium', 'open', '2000-01-01')
            """
        )
    assert stored_hash == hashlib.sha256(
        preview["confirmation_token"].encode("utf-8")
    ).hexdigest()
    assert stored_hash != preview["confirmation_token"]

    confirmed = service.confirm(
        operation_id=preview["operation_id"],
        confirmation_token=preview["confirmation_token"],
    )
    repeated = service.confirm(
        operation_id=preview["operation_id"],
        confirmation_token=preview["confirmation_token"],
    )

    assert confirmed["status"] == "success"
    assert confirmed["preview_changed"] is True
    assert confirmed["transitions"]["created_count"] == 1
    assert repeated == {
        "status": "failed",
        "failure_code": "ATTENTION_OPERATION_ALREADY_USED",
    }

    expired_preview = service.preview_reconciliation(
        actor="manager-990001",
        rule_keys=["overdue_action_attention"],
    )
    with sqlite3.connect(isolated_db) as connection:
        before_count = connection.execute(
            "SELECT COUNT(*) FROM attention_signals"
        ).fetchone()[0]
        connection.execute(
            """
            UPDATE attention_operations
            SET expires_at = '2000-01-01T00:00:00+00:00'
            WHERE operation_id = ?
            """,
            [expired_preview["operation_id"]],
        )
    expired = service.confirm(
        operation_id=expired_preview["operation_id"],
        confirmation_token=expired_preview["confirmation_token"],
    )
    with sqlite3.connect(isolated_db) as connection:
        after_count = connection.execute(
            "SELECT COUNT(*) FROM attention_signals"
        ).fetchone()[0]
        expired_status = connection.execute(
            """
            SELECT status FROM attention_operations
            WHERE operation_id = ?
            """,
            [expired_preview["operation_id"]],
        ).fetchone()[0]
    assert expired["failure_code"] == "ATTENTION_CONFIRMATION_EXPIRED"
    assert after_count == before_count
    assert expired_status == "expired"


def test_resource_threshold_is_strict_and_semantic_change_keeps_identity(
    isolated_db,
) -> None:
    init_db(quiet=True)
    with sqlite3.connect(isolated_db) as connection:
        connection.execute(
            """
            INSERT INTO employees (id, wd_id, name, status)
            VALUES ('member-990101', 'member-990101', 'Synthetic Member', 'active')
            """
        )
        connection.executemany(
            """
            INSERT INTO projects (id, name, status)
            VALUES (?, ?, 'active')
            """,
            [
                ("project-990001", "Synthetic Project 1"),
                ("project-990002", "Synthetic Project 2"),
            ],
        )
        connection.executemany(
            """
            INSERT INTO assignments
                (employee_id, project_id, allocation, status)
            VALUES ('member-990101', ?, ?, 'active')
            """,
            [("project-990001", 0.5), ("project-990002", 0.5)],
        )
        connection.execute(
            """
            INSERT INTO action_items (title, priority, status, due_date)
            VALUES ('Synthetic late action', 'high', 'open', '2000-01-01')
            """
        )
    publish_current_state_staffing_from_legacy(
        isolated_db,
        package_id="package-attention-resource-threshold-r1",
    )
    service = AttentionService()
    _confirm_reconciliation(
        service,
        rule_keys=[
            "resource_overload_attention",
            "overdue_action_attention",
        ],
    )
    with sqlite3.connect(isolated_db) as connection:
        assert connection.execute(
            """
            SELECT COUNT(*) FROM attention_signals
            WHERE rule_key = 'resource_overload_attention'
            """
        ).fetchone()[0] == 0
        action_before = connection.execute(
            """
            SELECT attention_id FROM attention_signals
            WHERE rule_key = 'overdue_action_attention'
            """
        ).fetchone()[0]
        connection.execute(
            """
            UPDATE assignments SET allocation = 0.6
            WHERE project_id = 'project-990001'
            """
        )
        connection.execute(
            "UPDATE action_items SET priority = 'medium'"
        )
    publish_current_state_staffing_from_legacy(
        isolated_db,
        package_id="package-attention-resource-threshold-r2",
    )

    _confirm_reconciliation(
        service,
        rule_keys=[
            "resource_overload_attention",
            "overdue_action_attention",
        ],
    )
    with sqlite3.connect(isolated_db) as connection:
        overload = connection.execute(
            """
            SELECT rule_state FROM attention_signals
            WHERE rule_key = 'resource_overload_attention'
            """
        ).fetchone()
        action_after = connection.execute(
            """
            SELECT attention_id, severity FROM attention_signals
            WHERE rule_key = 'overdue_action_attention'
            """
        ).fetchone()
        changed_events = connection.execute(
            """
            SELECT COUNT(*) FROM attention_history
            WHERE attention_id = ? AND event_type = 'observed_again'
            """,
            [action_before],
        ).fetchone()[0]
    assert overload == ("active",)
    assert action_after == (action_before, "medium")
    assert changed_events == 1


def test_partial_health_never_clears_until_sources_and_inputs_are_complete(
    isolated_db,
) -> None:
    _seed_attention_scenario(isolated_db)
    service = AttentionService()
    _confirm_reconciliation(service)

    with sqlite3.connect(isolated_db) as connection:
        connection.execute(
            "UPDATE jira_health_snapshots SET overall_grade = 'GREEN'"
        )
    _confirm_reconciliation(service)
    with sqlite3.connect(isolated_db) as connection:
        limited = connection.execute(
            """
            SELECT rule_state, attention_state, evaluation_status
            FROM attention_signals
            WHERE rule_key = 'project_health_attention'
            """
        ).fetchone()
    assert limited == ("active", "open", "partial")

    with sqlite3.connect(isolated_db) as connection:
        connection.execute(
            """
            UPDATE sync_runs
            SET started_at = ?, finished_at = ?
            WHERE id = 'sync-jira-stale-990001'
            """,
            [_now_text(), _now_text()],
        )
    _confirm_reconciliation(service)
    with sqlite3.connect(isolated_db) as connection:
        missing_input = connection.execute(
            """
            SELECT rule_state, attention_state, evaluation_status
            FROM attention_signals
            WHERE rule_key = 'project_health_attention'
            """
        ).fetchone()
    assert missing_input == ("active", "open", "partial")

    with sqlite3.connect(isolated_db) as connection:
        connection.execute(
            """
            INSERT INTO confluence_status_snapshots
                (board_id, snapshot_date, rag_status)
            VALUES ('board-990001', '2026-07-28', 'GREEN')
            """
        )
    _confirm_reconciliation(service)
    with sqlite3.connect(isolated_db) as connection:
        cleared = connection.execute(
            """
            SELECT rule_state, attention_state, resolution_reason
            FROM attention_signals
            WHERE rule_key = 'project_health_attention'
            """
        ).fetchone()
        event_types = [
            row[0]
            for row in connection.execute(
                """
                SELECT event_type FROM attention_history h
                JOIN attention_signals s ON s.attention_id = h.attention_id
                WHERE s.rule_key = 'project_health_attention'
                ORDER BY h.created_at, h.event_id
                """
            )
        ]
    assert cleared == ("clear", "resolved", "rule_clear")
    assert "evaluation_limited" in event_types
    assert "cleared" in event_types


def test_invalid_required_inputs_never_clear_active_attention(
    isolated_db,
) -> None:
    _seed_attention_scenario(isolated_db)
    service = AttentionService()
    _confirm_reconciliation(service)

    with sqlite3.connect(isolated_db) as connection:
        connection.execute(
            "UPDATE action_items SET due_date = 'invalid-date'"
        )
        connection.execute(
            "UPDATE jira_health_snapshots SET overall_grade = 'UNMAPPED'"
        )
    preview = service.preview_reconciliation(
        actor="manager-990001",
        rule_keys=[
            "project_health_attention",
            "overdue_action_attention",
        ],
    )
    assert preview["proposed"]["cleared_count"] == 0
    assert preview["proposed"]["limited_count"] == 2
    confirmed = service.confirm(
        operation_id=preview["operation_id"],
        confirmation_token=preview["confirmation_token"],
    )
    assert confirmed["reconciliation_status"] == "partial"
    repeated_preview = service.preview_reconciliation(
        actor="manager-990001",
        rule_keys=[
            "project_health_attention",
            "overdue_action_attention",
        ],
    )
    assert repeated_preview["proposed"]["updated_count"] == 0
    assert repeated_preview["proposed"]["limited_count"] == 0
    repeated = service.confirm(
        operation_id=repeated_preview["operation_id"],
        confirmation_token=repeated_preview["confirmation_token"],
    )
    assert repeated["transitions"]["updated_count"] == 0
    assert repeated["transitions"]["limited_count"] == 0

    with sqlite3.connect(isolated_db) as connection:
        states = connection.execute(
            """
            SELECT rule_key, rule_state, attention_state, evaluation_status
            FROM attention_signals
            WHERE rule_key IN (
                'project_health_attention',
                'overdue_action_attention'
            )
            ORDER BY rule_key
            """
        ).fetchall()
        limited_events = connection.execute(
            """
            SELECT severity, observation_json
            FROM attention_history
            WHERE event_type = 'evaluation_limited'
              AND attention_id IN (
                  SELECT attention_id
                  FROM attention_signals
                  WHERE rule_key IN (
                      'project_health_attention',
                      'overdue_action_attention'
                  )
              )
            ORDER BY attention_id
            """
        ).fetchall()
        hashes = connection.execute(
            """
            SELECT observation_hash, last_evaluation_hash
            FROM attention_signals
            WHERE rule_key IN (
                'project_health_attention',
                'overdue_action_attention'
            )
            ORDER BY rule_key
            """
        ).fetchall()
    assert states == [
        ("overdue_action_attention", "active", "open", "partial"),
        ("project_health_attention", "active", "open", "partial"),
    ]
    assert len(limited_events) == 2
    assert all(
        severity == json.loads(observation_json)["signal"]["severity"]
        for severity, observation_json in limited_events
    )
    assert all(
        observation_hash != last_evaluation_hash
        for observation_hash, last_evaluation_hash in hashes
    )


def test_malformed_nested_rag_config_fails_preview_safely(isolated_db) -> None:
    init_db(quiet=True)
    with sqlite3.connect(isolated_db) as connection:
        valid_parameters = json.loads(
            connection.execute(
                """
                SELECT parameters_json
                FROM attention_rules
                WHERE rule_key = 'project_health_attention'
                  AND is_current = 1
                """
            ).fetchone()[0            ]
        )
    malformed_parameters = []
    for field, value in (
        ("source_precedence", [["jira_grade"]]),
        ("state_precedence", ["red", ["amber"]]),
    ):
        parameters = json.loads(json.dumps(valid_parameters))
        parameters["default"][field] = value
        malformed_parameters.append(parameters)
    parameters = json.loads(json.dumps(valid_parameters))
    parameters["default"]["jira_grade_mapping"]["GREEN"] = []
    malformed_parameters.append(parameters)

    service = AttentionService()
    for parameters in malformed_parameters:
        with sqlite3.connect(isolated_db) as connection:
            connection.execute(
                """
                UPDATE attention_rules
                SET parameters_json = ?
                WHERE rule_key = 'project_health_attention'
                  AND is_current = 1
                """,
                [json.dumps(parameters, sort_keys=True)],
            )
        preview = service.preview_reconciliation(
            actor="manager-990001",
            rule_keys=["project_health_attention"],
        )
        assert preview == {
            "status": "failed",
            "failure_code": "ATTENTION_PREVIEW_INVALID",
        }


def test_configurable_rag_preserves_default_precedence_and_project_override(
    isolated_db,
) -> None:
    _seed_attention_scenario(isolated_db)
    with sqlite3.connect(isolated_db) as connection:
        connection.execute(
            """
            INSERT INTO confluence_status_snapshots
                (board_id, snapshot_date, rag_status)
            VALUES ('board-990001', '2026-07-28', 'RED')
            """
        )
        connection.execute(
            "UPDATE jira_health_snapshots SET overall_grade = 'YELLOW'"
        )
        connection.execute(
            """
            UPDATE sync_runs
            SET started_at = ?, finished_at = ?
            WHERE id = 'sync-jira-stale-990001'
            """,
            [_now_text(), _now_text()],
        )
    service = AttentionService()
    _confirm_reconciliation(
        service,
        rule_keys=["project_health_attention"],
    )
    with sqlite3.connect(isolated_db) as connection:
        first = connection.execute(
            """
            SELECT attention_id, severity, rule_version
            FROM attention_signals
            WHERE rule_key = 'project_health_attention'
            """
        ).fetchone()
        current = connection.execute(
            """
            SELECT rule_version, parameters_json
            FROM attention_rules
            WHERE rule_key = 'project_health_attention' AND is_current = 1
            """
        ).fetchone()
        parameters = json.loads(current[1])
        parameters["project_overrides"]["project-990001"] = {
            "jira_grade_mapping": {"YELLOW": "red"}
        }
        connection.execute(
            """
            UPDATE attention_rules
            SET is_current = 0
            WHERE rule_key = 'project_health_attention' AND is_current = 1
            """
        )
        connection.execute(
            """
            INSERT INTO attention_rules
                (rule_key, rule_version, is_current, enabled, parameters_json,
                 created_at, updated_at)
            VALUES (
                'project_health_attention', 'project-health-attention-v3',
                1, 1, ?, ?, ?
            )
            """,
            [
                json.dumps(parameters, sort_keys=True),
                _now_text(),
                _now_text(),
            ],
        )

    assert first[1:] == ("high", "project-health-attention-v2")
    _confirm_reconciliation(
        service,
        rule_keys=["project_health_attention"],
    )
    with sqlite3.connect(isolated_db) as connection:
        current_signal = connection.execute(
            """
            SELECT attention_id, severity, rule_version
            FROM attention_signals
            WHERE rule_key = 'project_health_attention'
            """
        ).fetchone()
        history = connection.execute(
            """
            SELECT severity, rule_version, observation_json
            FROM attention_history
            WHERE attention_id = ? AND event_type = 'rule_changed'
            """,
            [first[0]],
        ).fetchone()
        observed_again = connection.execute(
            """
            SELECT COUNT(*)
            FROM attention_history
            WHERE attention_id = ? AND event_type = 'observed_again'
            """,
            [first[0]],
        ).fetchone()[0]

    assert current_signal == (
        first[0],
        "critical",
        "project-health-attention-v3",
    )
    assert history[:2] == ("critical", "project-health-attention-v3")
    assert json.loads(history[2])["signal"]["severity"] == "critical"
    assert observed_again == 0


def test_lifecycle_preview_confirm_snooze_expiry_and_resolve_validation(
    isolated_db,
) -> None:
    _seed_attention_scenario(isolated_db)
    service = AttentionService()
    _confirm_reconciliation(service)
    with sqlite3.connect(isolated_db) as connection:
        attention_id = connection.execute(
            """
            SELECT attention_id FROM attention_signals
            WHERE rule_key = 'overdue_action_attention'
            """
        ).fetchone()[0]

    acknowledge = service.preview_acknowledgement(
        attention_id=attention_id,
        actor="manager-990001",
    )
    assert acknowledge["status"] == "proposed"
    assert service.confirm(
        operation_id=acknowledge["operation_id"],
        confirmation_token=acknowledge["confirmation_token"],
    )["attention_state"] == "acknowledged"

    snooze = service.preview_snooze(
        attention_id=attention_id,
        actor="manager-990001",
        snoozed_until=(
            datetime.now(timezone.utc) + timedelta(hours=2)
        ).isoformat(),
    )
    assert snooze["status"] == "proposed"
    assert service.confirm(
        operation_id=snooze["operation_id"],
        confirmation_token=snooze["confirmation_token"],
    )["attention_state"] == "snoozed"

    with sqlite3.connect(isolated_db) as connection:
        connection.execute(
            """
            UPDATE attention_signals
            SET snoozed_until = '2000-01-01T00:00:00+00:00'
            WHERE attention_id = ?
            """,
            [attention_id],
        )
    expiry_preview = service.preview_reconciliation(
        actor="manager-990001",
        rule_keys=["overdue_action_attention"],
    )
    assert expiry_preview["proposed"]["updated_count"] == 1
    assert expiry_preview["proposed"]["lifecycle_count"] == 1
    expiry_result = service.confirm(
        operation_id=expiry_preview["operation_id"],
        confirmation_token=expiry_preview["confirmation_token"],
    )
    assert expiry_result["transitions"]["lifecycle_count"] == 1
    with sqlite3.connect(isolated_db) as connection:
        state = connection.execute(
            """
            SELECT attention_state, snoozed_until
            FROM attention_signals WHERE attention_id = ?
            """,
            [attention_id],
        ).fetchone()
        event_types = [
            row[0]
            for row in connection.execute(
                """
                SELECT event_type FROM attention_history
                WHERE attention_id = ?
                """,
                [attention_id],
            )
        ]
    assert state == ("open", "")
    assert {"acknowledged", "snoozed", "snooze_expired"} <= set(event_types)

    active_resolve = service.preview_resolution(
        attention_id=attention_id,
        actor="manager-990001",
    )
    assert active_resolve["failure_code"] == "ATTENTION_STILL_ACTIVE"

    with sqlite3.connect(isolated_db) as connection:
        connection.execute(
            "UPDATE action_items SET status = 'done'"
        )
    _confirm_reconciliation(
        service,
        rule_keys=["overdue_action_attention"],
    )
    resolved_preview = service.preview_resolution(
        attention_id=attention_id,
        actor="manager-990001",
    )
    assert resolved_preview == {
        "status": "failed",
        "failure_code": "ATTENTION_ALREADY_RESOLVED",
    }


def test_concurrent_confirmation_applies_lifecycle_once(
    isolated_db,
) -> None:
    _seed_attention_scenario(isolated_db)
    service = AttentionService()
    _confirm_reconciliation(service)
    with sqlite3.connect(isolated_db) as connection:
        attention_id = connection.execute(
            "SELECT attention_id FROM attention_signals LIMIT 1"
        ).fetchone()[0]
    preview = service.preview_acknowledgement(
        attention_id=attention_id,
        actor="manager-990001",
    )

    def confirm_once(_index):
        return service.confirm(
            operation_id=preview["operation_id"],
            confirmation_token=preview["confirmation_token"],
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(confirm_once, range(2)))

    assert sum(result["status"] == "success" for result in results) == 1
    assert sum(
        result.get("failure_code") == "ATTENTION_OPERATION_ALREADY_USED"
        for result in results
    ) == 1
    with sqlite3.connect(isolated_db) as connection:
        event_count = connection.execute(
            """
            SELECT COUNT(*) FROM attention_history
            WHERE attention_id = ? AND event_type = 'acknowledged'
            """,
            [attention_id],
        ).fetchone()[0]
    assert event_count == 1


def test_invalid_catalog_and_transaction_failure_do_not_partially_mutate(
    isolated_db,
) -> None:
    init_db(quiet=True)
    service = AttentionService()
    with sqlite3.connect(isolated_db) as connection:
        connection.execute(
            """
            UPDATE attention_rules
            SET parameters_json = '{"unsupported":true}'
            WHERE rule_key = 'resource_overload_attention'
            """
        )
    invalid = service.preview_reconciliation(actor="manager-990001")
    assert invalid == {
        "status": "failed",
        "failure_code": "ATTENTION_PREVIEW_INVALID",
    }
    with sqlite3.connect(isolated_db) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM attention_operations"
        ).fetchone()[0] == 0
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO attention_operations
                    (operation_id, action, actor, status, scope_json, token_hash,
                     created_at, expires_at)
                VALUES (
                    'attop-invalid-json', 'reconcile', 'manager-990001',
                    'proposed', '{invalid', 'synthetic-hash',
                    '2026-07-28T00:00:00+00:00',
                    '2026-07-28T00:05:00+00:00'
                )
                """
            )
        connection.execute(
            """
            UPDATE attention_rules
            SET parameters_json =
                '{"active_assignment_load_strictly_greater_than":1.0}'
            WHERE rule_key = 'resource_overload_attention'
            """
        )

    preview = service.preview_reconciliation(actor="manager-990001")
    with sqlite3.connect(isolated_db) as connection:
        connection.execute(
            """
            UPDATE attention_rules
            SET parameters_json = '{"unsupported":true}'
            WHERE rule_key = 'resource_overload_attention'
            """
        )
    catalog_changed = service.confirm(
        operation_id=preview["operation_id"],
        confirmation_token=preview["confirmation_token"],
    )
    assert catalog_changed == {
        "status": "failed",
        "failure_code": "ATTENTION_RULE_CATALOG_INVALID",
    }
    with sqlite3.connect(isolated_db) as connection:
        catalog_operation_status = connection.execute(
            """
            SELECT status FROM attention_operations
            WHERE operation_id = ?
            """,
            [preview["operation_id"]],
        ).fetchone()[0]
        assert connection.execute(
            "SELECT COUNT(*) FROM attention_signals"
        ).fetchone()[0] == 0
        connection.execute(
            """
            UPDATE attention_rules
            SET parameters_json =
                '{"active_assignment_load_strictly_greater_than":1.0}'
            WHERE rule_key = 'resource_overload_attention'
            """
        )
    assert catalog_operation_status == "failed"

    preview = service.preview_reconciliation(actor="manager-990001")
    with sqlite3.connect(isolated_db) as connection:
        connection.execute(
            """
            CREATE TRIGGER synthetic_attention_history_failure
            BEFORE INSERT ON attention_history
            BEGIN
                SELECT RAISE(ABORT, 'synthetic failure');
            END
            """
        )
        connection.execute(
            """
            INSERT INTO action_items
                (title, priority, status, due_date)
            VALUES ('Synthetic late action', 'high', 'open', '2000-01-01')
            """
        )
    failed = service.confirm(
        operation_id=preview["operation_id"],
        confirmation_token=preview["confirmation_token"],
    )
    assert failed == {"status": "failed", "failure_code": "DATA_ACCESS_FAILED"}
    with sqlite3.connect(isolated_db) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM attention_signals"
        ).fetchone()[0] == 0
        assert connection.execute(
            "SELECT COUNT(*) FROM attention_reconciliations"
        ).fetchone()[0] == 0
        assert connection.execute(
            """
            SELECT status FROM attention_operations
            WHERE operation_id = ?
            """,
            [preview["operation_id"]],
        ).fetchone()[0] == "failed"
