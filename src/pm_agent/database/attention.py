"""SQLite persistence boundary for the Delivery Attention foundation."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator

from pm_agent.config import settings


@contextmanager
def attention_connection(
    *,
    immediate: bool = False,
    db_path: str | Path | None = None,
) -> Generator[sqlite3.Connection, None, None]:
    connection = sqlite3.connect(
        Path(db_path or settings.database_path),
        timeout=10,
        isolation_level=None,
    )
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 10000")
    try:
        connection.execute("BEGIN IMMEDIATE" if immediate else "BEGIN")
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def load_rules(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT rule_key, rule_version, enabled, parameters_json
        FROM attention_rules
        WHERE is_current = 1
        ORDER BY rule_key
        """
    ).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        item["enabled"] = bool(item["enabled"])
        item["parameters"] = json.loads(item.pop("parameters_json"))
        result.append(item)
    return result


def get_current_project_health_rule(
    connection: sqlite3.Connection,
) -> dict[str, Any] | None:
    row = connection.execute(
        """
        SELECT rule_key, rule_version, enabled, parameters_json,
               created_at, updated_at
        FROM attention_rules
        WHERE rule_key = 'project_health_attention' AND is_current = 1
        """
    ).fetchone()
    if not row:
        return None
    item = dict(row)
    item["enabled"] = bool(item["enabled"])
    item["parameters"] = json.loads(item.pop("parameters_json"))
    return item


def load_project_health_inputs(
    connection: sqlite3.Connection,
) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT
            p.id AS project_id,
            b.id AS board_id,
            h.id AS health_snapshot_id,
            h.snapshot_date AS health_snapshot_date,
            h.overall_grade,
            cs.id AS status_snapshot_id,
            cs.snapshot_date AS status_snapshot_date,
            cs.rag_status
        FROM projects p
        LEFT JOIN jira_board_configs b
          ON b.pm_project_id = p.id AND b.active = 1
        LEFT JOIN jira_health_snapshots h
          ON h.id = (
              SELECT h2.id
              FROM jira_health_snapshots h2
              WHERE h2.board_id = b.id
              ORDER BY h2.snapshot_date DESC, h2.id DESC
              LIMIT 1
          )
        LEFT JOIN confluence_status_snapshots cs
          ON cs.id = (
              SELECT cs2.id
              FROM confluence_status_snapshots cs2
              WHERE cs2.board_id = b.id
              ORDER BY cs2.snapshot_date DESC, cs2.id DESC
              LIMIT 1
          )
        WHERE p.status = 'active'
        ORDER BY p.id, b.id
        """
    ).fetchall()
    grouped: dict[str, dict[str, Any]] = {}
    for row in rows:
        project = grouped.setdefault(row["project_id"], {"project_id": row["project_id"], "boards": []})
        if row["board_id"]:
            project["boards"].append(
                {
                    "board_id": row["board_id"],
                    "health_snapshot_id": row["health_snapshot_id"],
                    "health_snapshot_date": row["health_snapshot_date"],
                    "overall_grade": row["overall_grade"],
                    "status_snapshot_id": row["status_snapshot_id"],
                    "status_snapshot_date": row["status_snapshot_date"],
                    "rag_status": row["rag_status"],
                }
            )
    return list(grouped.values())


def load_action_inputs(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    return [
        dict(row)
        for row in connection.execute(
            """
            SELECT id, status, priority, due_date, owner_id
            FROM action_items
            ORDER BY id
            """
        ).fetchall()
    ]


def load_source_inputs(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    return [
        dict(row)
        for row in connection.execute(
            """
            SELECT
                ds.id, ds.active, ds.refresh_sla_hours,
                sr.id AS latest_run_id,
                sr.started_at AS latest_started_at,
                sr.finished_at AS latest_finished_at,
                sr.status AS latest_status
            FROM data_sources ds
            LEFT JOIN sync_runs sr
              ON sr.id = (
                  SELECT sr2.id
                  FROM sync_runs sr2
                  WHERE sr2.source_id = ds.id
                  ORDER BY
                      CASE
                          WHEN COALESCE(sr2.finished_at, '') != ''
                          THEN sr2.finished_at
                          ELSE sr2.started_at
                      END DESC,
                      sr2.started_at DESC
                  LIMIT 1
              )
            ORDER BY ds.id
            """
        ).fetchall()
    ]


def load_member_inputs(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    return [
        dict(row)
        for row in connection.execute(
            """
            SELECT id, current_load, active_projects
            FROM v_member_load
            ORDER BY id
            """
        ).fetchall()
    ]


def load_expected_source_ids(connection: sqlite3.Connection) -> list[str]:
    rows = connection.execute(
        """
        SELECT b.id
        FROM jira_board_configs b
        JOIN projects p ON p.id = b.pm_project_id
        WHERE b.active = 1 AND p.status = 'active'
        ORDER BY b.id
        """
    ).fetchall()
    return [
        "confluence-status-batch",
        *(f"jira-health-{row['id']}" for row in rows),
    ]


def create_operation(
    connection: sqlite3.Connection,
    record: dict[str, Any],
) -> None:
    connection.execute(
        """
        INSERT INTO attention_operations
            (operation_id, action, actor, status, scope_json, token_hash,
             proposed_json, created_at, expires_at)
        VALUES (?, ?, ?, 'proposed', ?, ?, ?, ?, ?)
        """,
        [
            record["operation_id"],
            record["action"],
            record["actor"],
            _json(record["scope"]),
            record["token_hash"],
            _json(record["proposed"]),
            record["created_at"],
            record["expires_at"],
        ],
    )


def get_configuration_operation(
    connection: sqlite3.Connection,
    operation_id: str,
) -> dict[str, Any] | None:
    row = connection.execute(
        """
        SELECT *
        FROM attention_configuration_operations
        WHERE operation_id = ?
        """,
        [operation_id],
    ).fetchone()
    if not row:
        return None
    item = dict(row)
    item["proposed"] = json.loads(item.pop("proposed_json"))
    item["result"] = json.loads(item.pop("result_json"))
    return item


def get_operation(
    connection: sqlite3.Connection,
    operation_id: str,
) -> dict[str, Any] | None:
    row = connection.execute(
        "SELECT * FROM attention_operations WHERE operation_id = ?",
        [operation_id],
    ).fetchone()
    if not row:
        return None
    item = dict(row)
    item["scope"] = json.loads(item.pop("scope_json"))
    item["proposed"] = json.loads(item.pop("proposed_json"))
    item["result"] = json.loads(item.pop("result_json"))
    return item


def claim_operation(
    connection: sqlite3.Connection,
    *,
    operation_id: str,
    claimed_at: str,
) -> bool:
    cursor = connection.execute(
        """
        UPDATE attention_operations
        SET status = 'claimed', claimed_at = ?
        WHERE operation_id = ? AND status = 'proposed'
        """,
        [claimed_at, operation_id],
    )
    return cursor.rowcount == 1


def expire_operation(
    connection: sqlite3.Connection,
    *,
    operation_id: str,
    finished_at: str,
) -> None:
    connection.execute(
        """
        UPDATE attention_operations
        SET status = 'expired',
            failure_code = 'ATTENTION_CONFIRMATION_EXPIRED',
            finished_at = ?
        WHERE operation_id = ? AND status = 'proposed'
        """,
        [finished_at, operation_id],
    )


def finish_operation(
    connection: sqlite3.Connection,
    *,
    operation_id: str,
    success: bool,
    result: dict[str, Any],
    finished_at: str,
    failure_code: str = "",
) -> None:
    connection.execute(
        """
        UPDATE attention_operations
        SET status = ?, result_json = ?, failure_code = ?, finished_at = ?
        WHERE operation_id = ? AND status = 'claimed'
        """,
        [
            "success" if success else "failed",
            _json(result),
            failure_code,
            finished_at,
            operation_id,
        ],
    )


def fail_operation(
    connection: sqlite3.Connection,
    *,
    operation_id: str,
    failure_code: str,
    finished_at: str,
) -> None:
    connection.execute(
        """
        UPDATE attention_operations
        SET status = 'failed', failure_code = ?, finished_at = ?
        WHERE operation_id = ? AND status IN ('proposed', 'claimed')
        """,
        [failure_code, finished_at, operation_id],
    )


def list_signals(
    connection: sqlite3.Connection,
    *,
    rule_keys: list[str] | None = None,
    subject_kind: str | None = None,
    subject_id: str | None = None,
) -> list[dict[str, Any]]:
    clauses = []
    parameters: list[Any] = []
    if rule_keys:
        clauses.append(f"rule_key IN ({','.join('?' for _ in rule_keys)})")
        parameters.extend(rule_keys)
    if subject_kind:
        clauses.append("subject_kind = ?")
        parameters.append(subject_kind)
    if subject_id:
        clauses.append("subject_id = ?")
        parameters.append(subject_id)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = connection.execute(
        f"""
        SELECT *
        FROM attention_signals
        {where}
        ORDER BY rule_key, subject_kind, subject_id
        """,
        parameters,
    ).fetchall()
    return [_signal_dict(row) for row in rows]


def get_signal(
    connection: sqlite3.Connection,
    attention_id: str,
) -> dict[str, Any] | None:
    row = connection.execute(
        "SELECT * FROM attention_signals WHERE attention_id = ?",
        [attention_id],
    ).fetchone()
    return _signal_dict(row) if row else None


def list_center_signals(
    connection: sqlite3.Connection,
    *,
    attention_states: list[str],
    rule_key: str | None = None,
    subject_kind: str | None = None,
    subject_id: str | None = None,
) -> list[dict[str, Any]]:
    clauses = [
        f"attention_state IN ({','.join('?' for _ in attention_states)})"
    ]
    parameters: list[Any] = list(attention_states)
    if rule_key:
        clauses.append("rule_key = ?")
        parameters.append(rule_key)
    if subject_kind:
        clauses.append("subject_kind = ?")
        parameters.append(subject_kind)
    if subject_id:
        clauses.append("subject_id = ?")
        parameters.append(subject_id)
    rows = connection.execute(
        f"""
        SELECT *
        FROM attention_signals
        WHERE {' AND '.join(clauses)}
        ORDER BY
            CASE severity
                WHEN 'critical' THEN 0
                WHEN 'high' THEN 1
                WHEN 'medium' THEN 2
                WHEN 'low' THEN 3
                WHEN 'none' THEN 4
                ELSE 5
            END,
            CASE attention_state
                WHEN 'open' THEN 0
                WHEN 'acknowledged' THEN 1
                WHEN 'snoozed' THEN 2
                WHEN 'resolved' THEN 3
                ELSE 4
            END,
            last_seen_at DESC,
            attention_id
        """,
        parameters,
    ).fetchall()
    return [_signal_dict(row) for row in rows]


def list_recent_history(
    connection: sqlite3.Connection,
    *,
    attention_id: str,
    limit: int,
) -> list[dict[str, Any]]:
    if limit <= 0:
        return []
    rows = connection.execute(
        """
        SELECT
            event_id, event_type, prior_rule_state, new_rule_state,
            prior_attention_state, new_attention_state, severity,
            rule_version, actor, reconciliation_id, created_at
        FROM attention_history
        WHERE attention_id = ?
        ORDER BY created_at DESC, rowid DESC
        LIMIT ?
        """,
        [attention_id, limit],
    ).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        item["timestamp"] = item.pop("created_at")
        result.append(item)
    return result


def get_latest_limited_observation(
    connection: sqlite3.Connection,
    *,
    attention_id: str,
) -> dict[str, Any] | None:
    row = connection.execute(
        """
        SELECT observation_json
        FROM attention_history
        WHERE attention_id = ? AND event_type = 'evaluation_limited'
        ORDER BY created_at DESC, rowid DESC
        LIMIT 1
        """,
        [attention_id],
    ).fetchone()
    return json.loads(row["observation_json"]) if row else None


def list_reconciliations(
    connection: sqlite3.Connection,
) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT
            r.reconciliation_id, r.status, r.finished_at,
            r.rule_set_version, r.warning_codes_json, o.scope_json
        FROM attention_reconciliations r
        JOIN attention_operations o ON o.operation_id = r.operation_id
        ORDER BY r.finished_at DESC, r.rowid DESC
        """
    ).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        item["warning_codes"] = json.loads(item.pop("warning_codes_json"))
        item["scope"] = json.loads(item.pop("scope_json"))
        result.append(item)
    return result


def insert_reconciliation(
    connection: sqlite3.Connection,
    record: dict[str, Any],
) -> None:
    connection.execute(
        """
        INSERT INTO attention_reconciliations
            (reconciliation_id, operation_id, status, actor, started_at,
             finished_at, rule_set_version, warning_codes_json, candidate_count,
             created_count, updated_count, cleared_count, reopened_count)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            record["reconciliation_id"],
            record["operation_id"],
            record["status"],
            record["actor"],
            record["started_at"],
            record["finished_at"],
            record["rule_set_version"],
            _json(record["warning_codes"]),
            record["candidate_count"],
            record["created_count"],
            record["updated_count"],
            record["cleared_count"],
            record["reopened_count"],
        ],
    )


def insert_signal(
    connection: sqlite3.Connection,
    record: dict[str, Any],
) -> None:
    connection.execute(
        """
        INSERT INTO attention_signals
            (attention_id, rule_key, rule_version, subject_kind, subject_id,
             rule_state, attention_state, evaluation_status, severity,
             first_seen_at, last_seen_at, last_reconciliation_id,
             observation_hash, last_evaluation_hash, observation_json,
             created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            record["attention_id"],
            record["rule_key"],
            record["rule_version"],
            record["subject_kind"],
            record["subject_id"],
            record["rule_state"],
            record["attention_state"],
            record["evaluation_status"],
            record["severity"],
            record["first_seen_at"],
            record["last_seen_at"],
            record["last_reconciliation_id"],
            record["observation_hash"],
            record["last_evaluation_hash"],
            _json(record["observation"]),
            record["created_at"],
            record["updated_at"],
        ],
    )


def update_signal(
    connection: sqlite3.Connection,
    attention_id: str,
    values: dict[str, Any],
) -> None:
    allowed = {
        "rule_version",
        "rule_state",
        "attention_state",
        "evaluation_status",
        "severity",
        "last_seen_at",
        "last_reconciliation_id",
        "acknowledged_at",
        "acknowledged_by",
        "snoozed_until",
        "snoozed_by",
        "resolved_at",
        "resolved_by",
        "resolution_reason",
        "observation_hash",
        "last_evaluation_hash",
        "observation",
        "observation_json",
        "updated_at",
    }
    unknown = set(values) - allowed
    if unknown:
        raise ValueError("Unsupported Attention signal update")
    normalized = dict(values)
    if "observation" in normalized:
        normalized["observation_json"] = _json(normalized.pop("observation"))
    assignments = ", ".join(f"{column} = ?" for column in normalized)
    connection.execute(
        f"UPDATE attention_signals SET {assignments} WHERE attention_id = ?",
        [*normalized.values(), attention_id],
    )


def insert_history(
    connection: sqlite3.Connection,
    record: dict[str, Any],
) -> None:
    connection.execute(
        """
        INSERT INTO attention_history
            (event_id, attention_id, operation_id, reconciliation_id, event_type,
             prior_rule_state, new_rule_state, prior_attention_state,
             new_attention_state, severity, rule_version, actor,
             observation_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            record["event_id"],
            record["attention_id"],
            record["operation_id"],
            record.get("reconciliation_id"),
            record["event_type"],
            record.get("prior_rule_state", ""),
            record.get("new_rule_state", ""),
            record.get("prior_attention_state", ""),
            record.get("new_attention_state", ""),
            record["severity"],
            record["rule_version"],
            record["actor"],
            _json(record.get("observation", {})),
            record["created_at"],
        ],
    )


def _signal_dict(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    item["observation"] = json.loads(item.pop("observation_json"))
    return item


def _json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
