"""
database/repository.py — Single place for SQLite reads and writes.

Rules:
- Keep SQL in this layer or other database helpers, not in use-case services.
- Return plain dicts or simple values, not raw sqlite3.Row objects.
- Never raise on missing data — return None / empty list.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Generator

from pm_agent.config import settings
from pm_agent.rules.hiref import days_until, hiref_urgency, project_alignment_status
from pm_agent.rules.identity import slugify_text


# ──────────────────────────────────────────────
# Connection helper
# ──────────────────────────────────────────────

@contextmanager
def _conn() -> Generator[sqlite3.Connection, None, None]:
    path = Path(settings.database_path)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def _row_to_dict(row: sqlite3.Row | None) -> dict | None:
    return dict(row) if row else None


def _rows_to_list(rows: list[sqlite3.Row]) -> list[dict]:
    return [dict(r) for r in rows]


def _json_loads_or(value: Any, default: Any) -> Any:
    if isinstance(value, (list, dict)):
        return value
    if value in (None, ""):
        return json.loads(json.dumps(default))
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return json.loads(json.dumps(default))


_GROUP_JOIN_SEPARATOR = "|||"
_FIELD_JOIN_SEPARATOR = ":::"
EXECUTION_TRACE_RETENTION = 500


def _split_joined_values(value: Any, separator: str = _GROUP_JOIN_SEPARATOR) -> list[str]:
    if value in (None, ""):
        return []
    return [item.strip() for item in str(value).split(separator) if item and item.strip()]


def _unique_preserving_order(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def _split_grouped_records(value: Any, field_names: list[str]) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    for item in _split_joined_values(value):
        parts = item.split(_FIELD_JOIN_SEPARATOR)
        if len(parts) < len(field_names):
            parts.extend([""] * (len(field_names) - len(parts)))
        result.append({field: parts[idx] for idx, field in enumerate(field_names)})
    return result


def _table_exists(con: sqlite3.Connection, table_name: str) -> bool:
    row = con.execute(
        "SELECT 1 FROM sqlite_master WHERE type IN ('table','view') AND name=?",
        [table_name],
    ).fetchone()
    return row is not None


def _resolve_employee_id(
    con: sqlite3.Connection,
    employee_id: str | None,
) -> str | None:
    candidate = (employee_id or "").strip()
    if not candidate:
        return None

    row = con.execute(
        "SELECT id FROM employees WHERE id = ?",
        [candidate],
    ).fetchone()
    if row:
        return row["id"]

    if not _table_exists(con, "employee_external_ids"):
        return None

    row = con.execute(
        """
        SELECT employee_id
        FROM employee_external_ids
        WHERE lower(external_id) = lower(?)
        ORDER BY
            CASE system_name
                WHEN 'resource_portal' THEN 0
                WHEN 'jira' THEN 1
                ELSE 2
            END,
            employee_id
        LIMIT 1
        """,
        [candidate],
    ).fetchone()
    return row["employee_id"] if row else None


def resolve_employee_id(employee_id: str | None) -> str | None:
    with _conn() as con:
        return _resolve_employee_id(con, employee_id)


# ──────────────────────────────────────────────
# Employees
# ──────────────────────────────────────────────

def get_all_members() -> list[dict]:
    """Return all active employees with current load (from v_member_load)."""
    with _conn() as con:
        rows = con.execute("SELECT * FROM v_member_load").fetchall()
    members = _rows_to_list(rows)
    # Deserialise skills JSON
    for m in members:
        m["skills"] = json.loads(m.get("skills") or "{}")
    return members


def get_member(member_id: str) -> dict | None:
    with _conn() as con:
        resolved_id = _resolve_employee_id(con, member_id)
        if not resolved_id:
            return None
        row = con.execute(
            "SELECT * FROM v_member_load WHERE id = ?",
            [resolved_id],
        ).fetchone()
    if not row:
        return None
    m = dict(row)
    m["skills"] = json.loads(m.get("skills") or "{}")
    return m


def get_member_projects(member_id: str) -> list[str]:
    """Return list of active project_ids for a member."""
    with _conn() as con:
        resolved_id = _resolve_employee_id(con, member_id)
        if not resolved_id:
            return []
        rows = con.execute(
            "SELECT project_id FROM assignments WHERE employee_id=? AND status='active'",
            [resolved_id],
        ).fetchall()
    return [r["project_id"] for r in rows]


def upsert_member(data: dict) -> None:
    """Insert or replace a member record."""
    data = dict(data)
    data["wd_id"] = data.get("wd_id") or data["id"]
    data["resource_type"] = data.get("resource_type", "")
    data["billing_rate"] = data.get("billing_rate", "")
    data["billing_end_date"] = data.get("billing_end_date", "")
    data["hiref_id"] = data.get("hiref_id", "")
    data["current_hiref"] = data.get("current_hiref", "")
    data["next_hiref"] = data.get("next_hiref", "")
    data["skills"] = json.dumps(data.get("skills", {}))
    data["metadata"] = json.dumps(data.get("metadata", {}))
    data["updated_at"] = datetime.now().isoformat()
    with _conn() as con:
        con.execute(
            """
            INSERT INTO employees
                (id, wd_id, name, email, role, level, team, lead_id, max_parallel,
                 status, notes, skills, metadata, resource_type, billing_rate,
                 billing_end_date, hiref_id, current_hiref, next_hiref, updated_at)
            VALUES
                (:id,:wd_id,:name,:email,:role,:level,:team,:lead_id,:max_parallel,
                 :status,:notes,:skills,:metadata,:resource_type,:billing_rate,
                 :billing_end_date,:hiref_id,:current_hiref,:next_hiref,:updated_at)
            ON CONFLICT(id) DO UPDATE SET
                wd_id=excluded.wd_id,
                name=excluded.name, email=excluded.email, role=excluded.role,
                level=excluded.level, team=excluded.team, lead_id=excluded.lead_id,
                max_parallel=excluded.max_parallel, skills=excluded.skills,
                metadata=excluded.metadata, status=excluded.status, notes=excluded.notes,
                resource_type=excluded.resource_type,
                billing_rate=excluded.billing_rate,
                billing_end_date=excluded.billing_end_date,
                hiref_id=excluded.hiref_id,
                current_hiref=excluded.current_hiref,
                next_hiref=excluded.next_hiref,
                updated_at=excluded.updated_at
            """,
            data,
        )


def get_employee_external_ids(
    employee_id: str | None = None,
    system_name: str | None = None,
) -> list[dict]:
    with _conn() as con:
        if not _table_exists(con, "employee_external_ids"):
            return []
        clauses = []
        params: list[Any] = []
        if employee_id:
            resolved_id = _resolve_employee_id(con, employee_id)
            if not resolved_id:
                return []
            clauses.append("employee_id=?")
            params.append(resolved_id)
        if system_name:
            clauses.append("system_name=?")
            params.append(system_name)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        rows = con.execute(
            f"""
            SELECT *
            FROM employee_external_ids
            {where}
            ORDER BY employee_id, system_name, id_type
            """,
            params,
        ).fetchall()
    return _rows_to_list(rows)


# ──────────────────────────────────────────────
# HIREF / staffing placeholders
# ──────────────────────────────────────────────

def get_hiref_contracts() -> list[dict]:
    with _conn() as con:
        if not _table_exists(con, "hiref"):
            return []

        rows = con.execute(
            """
            SELECT
                h.id,
                h.project,
                h.request_type,
                h.start_date,
                h.end_date,
                h.notes,
                cur.id AS assigned_employee_id,
                cur.wd_id AS assigned_wd_id,
                cur.name AS assigned_to,
                cur.resource_type AS assigned_resource_type,
                cur.next_hiref AS assigned_next_hiref,
                nh.project AS assigned_next_hiref_project,
                nh.start_date AS assigned_next_hiref_start_date,
                nh.end_date AS assigned_next_hiref_end_date,
                nxt.id AS reserved_employee_id,
                nxt.wd_id AS reserved_wd_id,
                nxt.name AS reserved_for_next,
                sp.placeholder_id,
                sp.display_name AS placeholder_name,
                sp.status AS placeholder_status,
                sp.linked_employee_id AS placeholder_linked_employee_id,
                ap.actual_project_ids_joined,
                ap.actual_project_names_joined,
                ap.actual_project_keys_joined
            FROM hiref h
            LEFT JOIN employees cur
              ON cur.current_hiref = h.id
             AND cur.status = 'active'
            LEFT JOIN hiref nh
              ON nh.id = cur.next_hiref
            LEFT JOIN employees nxt
              ON nxt.next_hiref = h.id
             AND nxt.status = 'active'
            LEFT JOIN staffing_placeholders sp
              ON sp.hiref_id = h.id
             AND COALESCE(sp.status, 'planned') != 'closed'
            LEFT JOIN (
                SELECT
                    a.employee_id,
                    GROUP_CONCAT(p.id, '|||') AS actual_project_ids_joined,
                    GROUP_CONCAT(p.name, '|||') AS actual_project_names_joined,
                    GROUP_CONCAT(COALESCE(p.jira_key, ''), '|||') AS actual_project_keys_joined
                FROM assignments a
                LEFT JOIN projects p ON p.id = a.project_id
                WHERE a.status = 'active'
                GROUP BY a.employee_id
            ) ap
              ON ap.employee_id = cur.id
            ORDER BY COALESCE(h.end_date, '9999-12-31'), h.id
            """
        ).fetchall()

    result = []
    for item in _rows_to_list(rows):
        actual_project_ids = _unique_preserving_order(_split_joined_values(item.pop("actual_project_ids_joined", "")))
        actual_project_names = _unique_preserving_order(_split_joined_values(item.pop("actual_project_names_joined", "")))
        actual_project_keys = _unique_preserving_order(_split_joined_values(item.pop("actual_project_keys_joined", "")))

        item["actual_project_ids"] = actual_project_ids
        item["actual_project_names"] = actual_project_names
        item["actual_project_keys"] = actual_project_keys
        item["actual_project_display"] = " / ".join(actual_project_names) if actual_project_names else "-"
        expiry_days = days_until(item.get("end_date"))
        occupancy_status = _hiref_occupancy_status(item)
        item["days_until_expiry"] = expiry_days
        item["occupancy_status"] = occupancy_status
        item["is_free"] = occupancy_status == "free"
        item["has_next_hiref"] = bool(item.get("assigned_next_hiref"))
        item["has_reservation"] = item["has_next_hiref"] or occupancy_status in {
            "reserved_for_next",
            "placeholder_reserved",
        }
        item["urgency"] = hiref_urgency(expiry_days, item["has_reservation"])
        if item.get("assigned_to"):
            item["project_alignment_status"] = project_alignment_status(
                item.get("project"),
                actual_project_names=actual_project_names,
                actual_project_ids=actual_project_ids,
                actual_project_keys=actual_project_keys,
            )
        else:
            item["project_alignment_status"] = "unknown"
        result.append(item)
    return result


def get_hiref_staff_review(days: int | None = 180) -> list[dict]:
    with _conn() as con:
        if not _table_exists(con, "employees"):
            return []

        where_clauses = [
            "e.status = 'active'",
            "e.resource_type = 'STFTE'",
        ]
        params: list[Any] = []
        if days is not None:
            where_clauses.append(
                "(COALESCE(e.current_hiref, '') = '' OR COALESCE(h.end_date, '') = '' OR h.end_date <= date('now', ?))"
            )
            params.append(f"+{days} days")

        rows = con.execute(
            f"""
            SELECT
                e.id AS employee_id,
                e.wd_id,
                e.name,
                e.team,
                e.level,
                e.billing_end_date,
                e.current_hiref,
                e.next_hiref,
                h.project AS hiref_project,
                h.start_date,
                h.end_date,
                h.request_type,
                h.notes AS hiref_notes,
                nh.project AS next_hiref_project,
                nh.start_date AS next_hiref_start_date,
                nh.end_date AS next_hiref_end_date,
                ap.actual_project_ids_joined,
                ap.actual_project_names_joined,
                ap.actual_project_keys_joined,
                ap.current_load
            FROM employees e
            LEFT JOIN hiref h
              ON e.current_hiref = h.id
            LEFT JOIN hiref nh
              ON e.next_hiref = nh.id
            LEFT JOIN (
                SELECT
                    a.employee_id,
                    GROUP_CONCAT(p.id, '{_GROUP_JOIN_SEPARATOR}') AS actual_project_ids_joined,
                    GROUP_CONCAT(p.name, '{_GROUP_JOIN_SEPARATOR}') AS actual_project_names_joined,
                    GROUP_CONCAT(COALESCE(p.jira_key, ''), '{_GROUP_JOIN_SEPARATOR}') AS actual_project_keys_joined,
                    COALESCE(SUM(a.allocation), 0.0) AS current_load
                FROM assignments a
                LEFT JOIN projects p ON p.id = a.project_id
                WHERE a.status = 'active'
                GROUP BY a.employee_id
            ) ap
              ON ap.employee_id = e.id
            WHERE {" AND ".join(where_clauses)}
            ORDER BY
                CASE WHEN COALESCE(h.end_date, '') = '' THEN 0 ELSE 1 END,
                COALESCE(h.end_date, '9999-12-31'),
                e.name
            """,
            params,
        ).fetchall()

    result = []
    for item in _rows_to_list(rows):
        actual_project_ids = _unique_preserving_order(_split_joined_values(item.pop("actual_project_ids_joined", "")))
        actual_project_names = _unique_preserving_order(_split_joined_values(item.pop("actual_project_names_joined", "")))
        actual_project_keys = _unique_preserving_order(_split_joined_values(item.pop("actual_project_keys_joined", "")))

        item["actual_project_ids"] = actual_project_ids
        item["actual_project_names"] = actual_project_names
        item["actual_project_keys"] = actual_project_keys
        item["actual_project_display"] = " / ".join(actual_project_names) if actual_project_names else "-"

        expiry_days = days_until(item.get("end_date"))
        current_hiref_missing = not (item.get("current_hiref") or "").strip()
        if current_hiref_missing:
            alignment_status = "missing_current_hiref"
            urgency_value = "critical"
        else:
            alignment_status = project_alignment_status(
                item.get("hiref_project"),
                actual_project_names=actual_project_names,
                actual_project_ids=actual_project_ids,
                actual_project_keys=actual_project_keys,
            )
            urgency_value = hiref_urgency(expiry_days, bool(item.get("next_hiref")))

        item["days_until_expiry"] = expiry_days
        item["current_hiref_missing"] = current_hiref_missing
        item["project_alignment_status"] = alignment_status
        item["project_aligned"] = alignment_status == "aligned"
        item["urgency"] = urgency_value
        item["requires_action"] = (
            current_hiref_missing
            or alignment_status in {"mismatch", "no_active_assignment"}
            or urgency_value in {"expired", "critical", "high"}
        )
        result.append(item)
    return result


def get_staffing_placeholders(plan_version_id: str | None = None) -> list[dict]:
    with _conn() as con:
        if not _table_exists(con, "staffing_placeholders"):
            return []

        plan_version_filter = plan_version_id
        if not plan_version_filter and _table_exists(con, "plan_versions"):
            row = con.execute(
                """
                SELECT plan_version_id
                FROM plan_versions
                WHERE version_status = 'active'
                ORDER BY
                    CASE scenario_type
                        WHEN 'forecast' THEN 0
                        WHEN 'baseline' THEN 1
                        WHEN 'approved' THEN 2
                        WHEN 'what_if' THEN 3
                        ELSE 4
                    END,
                    COALESCE(as_of_date, '') DESC,
                    plan_version_id
                LIMIT 1
                """
            ).fetchone()
            if row:
                plan_version_filter = row["plan_version_id"]

        current_period = datetime.now().year * 100 + datetime.now().month
        has_placeholder_allocations = _table_exists(con, "placeholder_monthly_allocations")

        if has_placeholder_allocations:
            rows = con.execute(
                f"""
                SELECT
                    sp.placeholder_id,
                    sp.display_name,
                    sp.source_system,
                    sp.source_employee_id,
                    sp.hiref_id,
                    sp.linked_employee_id,
                    linked.name AS linked_employee_name,
                    sp.resource_type,
                    sp.status,
                    sp.notes,
                    CASE WHEN h.id IS NULL THEN 0 ELSE 1 END AS slot_registered,
                    GROUP_CONCAT(p.id, '{_GROUP_JOIN_SEPARATOR}') AS project_ids_joined,
                    GROUP_CONCAT(p.name, '{_GROUP_JOIN_SEPARATOR}') AS project_names_joined,
                    MIN(
                        CASE
                            WHEN pma.allocation > 0 AND (pma.year * 100 + pma.month) >= ?
                            THEN printf('%04d-%02d', pma.year, pma.month)
                        END
                    ) AS next_demand_month,
                    COALESCE(MAX(pma.allocation), 0.0) AS peak_allocation,
                    COALESCE(SUM(CASE WHEN pma.allocation > 0 THEN 1 ELSE 0 END), 0) AS demand_months,
                    COALESCE(SUM(COALESCE(pma.allocation, 0.0)), 0.0) AS total_allocation
                FROM staffing_placeholders sp
                LEFT JOIN employees linked
                  ON linked.id = sp.linked_employee_id
                LEFT JOIN placeholder_monthly_allocations pma
                  ON pma.placeholder_id = sp.placeholder_id
                 AND (? = '' OR COALESCE(pma.plan_version_id, '') = ?)
                LEFT JOIN projects p
                  ON p.id = pma.project_id
                LEFT JOIN hiref h
                  ON h.id = sp.hiref_id
                WHERE COALESCE(sp.status, 'planned') != 'closed'
                GROUP BY
                    sp.placeholder_id,
                    sp.display_name,
                    sp.source_system,
                    sp.source_employee_id,
                    sp.hiref_id,
                    sp.linked_employee_id,
                    linked.name,
                    sp.resource_type,
                    sp.status,
                    sp.notes,
                    h.id
                ORDER BY
                    CASE WHEN next_demand_month IS NULL OR next_demand_month = '' THEN 1 ELSE 0 END,
                    next_demand_month,
                    sp.placeholder_id
                """,
                [current_period, plan_version_filter or "", plan_version_filter or ""],
            ).fetchall()
        else:
            rows = con.execute(
                """
                SELECT
                    sp.placeholder_id,
                    sp.display_name,
                    sp.source_system,
                    sp.source_employee_id,
                    sp.hiref_id,
                    sp.linked_employee_id,
                    linked.name AS linked_employee_name,
                    sp.resource_type,
                    sp.status,
                    sp.notes,
                    CASE WHEN h.id IS NULL THEN 0 ELSE 1 END AS slot_registered,
                    '' AS project_ids_joined,
                    '' AS project_names_joined,
                    '' AS next_demand_month,
                    0.0 AS peak_allocation,
                    0 AS demand_months,
                    0.0 AS total_allocation
                FROM staffing_placeholders sp
                LEFT JOIN employees linked
                  ON linked.id = sp.linked_employee_id
                LEFT JOIN hiref h
                  ON h.id = sp.hiref_id
                WHERE COALESCE(sp.status, 'planned') != 'closed'
                ORDER BY sp.placeholder_id
                """
            ).fetchall()

    result = []
    for item in _rows_to_list(rows):
        item["project_ids"] = _unique_preserving_order(_split_joined_values(item.pop("project_ids_joined", "")))
        item["project_names"] = _unique_preserving_order(_split_joined_values(item.pop("project_names_joined", "")))
        item["project_display"] = " / ".join(item["project_names"]) if item["project_names"] else "-"
        item["slot_registered"] = bool(item.get("slot_registered"))
        item["has_linked_employee"] = bool(item.get("linked_employee_id"))
        result.append(item)
    return result


def _hiref_occupancy_status(item: dict) -> str:
    if item.get("assigned_employee_id"):
        return "assigned"
    if item.get("reserved_employee_id"):
        return "reserved_for_next"
    if item.get("placeholder_id"):
        return "placeholder_reserved"
    return "free"


# ──────────────────────────────────────────────
# Weekly report fusion inputs
# ──────────────────────────────────────────────

def get_project_confluence_signals() -> dict[str, dict]:
    result: dict[str, dict] = {}
    with _conn() as con:
        if not _table_exists(con, "jira_board_configs"):
            return result

        if _table_exists(con, "confluence_status_snapshots"):
            rows = con.execute(
                """
                SELECT
                    bc.pm_project_id AS project_id,
                    bc.name AS board_name,
                    cs.board_id,
                    cs.snapshot_date,
                    cs.rag_status,
                    cs.status_as_of,
                    cs.owner,
                    cs.summary_text,
                    cs.risks_text,
                    cs.sprint_iteration
                FROM confluence_status_snapshots cs
                JOIN jira_board_configs bc ON bc.id = cs.board_id
                WHERE COALESCE(bc.pm_project_id, '') != ''
                  AND cs.snapshot_date = (
                      SELECT MAX(cs2.snapshot_date)
                      FROM confluence_status_snapshots cs2
                      WHERE cs2.board_id = cs.board_id
                  )
                ORDER BY COALESCE(cs.status_as_of, cs.snapshot_date, '') DESC, cs.board_id
                """
            ).fetchall()
            for row in rows:
                item = dict(row)
                project_id = item["project_id"]
                if project_id and project_id not in result:
                    item["source"] = "snapshot"
                    result[project_id] = item

        if _table_exists(con, "confluence_pages"):
            rows = con.execute(
                """
                SELECT
                    bc.pm_project_id AS project_id,
                    bc.name AS board_name,
                    cp.board_id,
                    cp.title,
                    cp.last_modified,
                    cp.last_synced,
                    cp.content_summary
                FROM confluence_pages cp
                JOIN jira_board_configs bc ON bc.id = cp.board_id
                WHERE COALESCE(bc.pm_project_id, '') != ''
                  AND cp.page_type = 'weekly_status'
                ORDER BY COALESCE(cp.last_modified, cp.last_synced, '') DESC, cp.id DESC
                """
            ).fetchall()
            for row in rows:
                item = dict(row)
                project_id = item["project_id"]
                if project_id and project_id not in result:
                    item["source"] = "page_registry"
                    result[project_id] = item

    return result


def get_project_change_request_summaries() -> dict[str, dict]:
    with _conn() as con:
        if not _table_exists(con, "change_requests"):
            return {}

        rows = con.execute(
            f"""
            SELECT
                p.id AS project_id,
                COUNT(cr.id) AS total_changes,
                COALESCE(SUM(
                    CASE
                        WHEN cr.id IS NOT NULL
                         AND LOWER(COALESCE(cr.state, '')) NOT IN ('closed', 'cancelled')
                        THEN 1
                        ELSE 0
                    END
                ), 0) AS open_changes,
                COALESCE(SUM(
                    CASE
                        WHEN cr.id IS NOT NULL
                         AND LOWER(COALESCE(cr.state, '')) NOT IN ('closed', 'cancelled')
                         AND SUBSTR(TRIM(COALESCE(cr.priority, '')), 1, 1) IN ('1', '2')
                        THEN 1
                        ELSE 0
                    END
                ), 0) AS high_priority_changes,
                MIN(
                    CASE
                        WHEN cr.id IS NOT NULL
                         AND LOWER(COALESCE(cr.state, '')) NOT IN ('closed', 'cancelled')
                         AND COALESCE(cr.planned_start, '') != ''
                        THEN cr.planned_start
                    END
                ) AS next_change_start,
                GROUP_CONCAT(
                    CASE
                        WHEN cr.id IS NOT NULL
                         AND LOWER(COALESCE(cr.state, '')) NOT IN ('closed', 'cancelled')
                        THEN
                            COALESCE(cr.id, '')
                            || '{_FIELD_JOIN_SEPARATOR}' || COALESCE(cr.state, '')
                            || '{_FIELD_JOIN_SEPARATOR}' || COALESCE(cr.short_desc, '')
                    END,
                    '{_GROUP_JOIN_SEPARATOR}'
                ) AS open_change_items_joined
            FROM projects p
            LEFT JOIN change_requests cr
              ON COALESCE(p.jira_key, '') != ''
             AND COALESCE(cr.project_code, '') LIKE '%' || p.jira_key || '%'
            GROUP BY p.id
            ORDER BY p.id
            """
        ).fetchall()

    result: dict[str, dict] = {}
    for item in _rows_to_list(rows):
        item["open_change_items"] = _split_grouped_records(
            item.pop("open_change_items_joined", ""),
            ["id", "state", "summary"],
        )
        result[item["project_id"]] = item
    return result


def get_latest_action_tracker_summary() -> dict | None:
    with _conn() as con:
        if not _table_exists(con, "action_tracker"):
            return None
        latest_synced = con.execute(
            "SELECT MAX(synced_date) FROM action_tracker"
        ).fetchone()[0]
        if not latest_synced:
            return None
        rows = con.execute(
            """
            SELECT COALESCE(status, 'Unknown') AS status, COUNT(*) AS cnt
            FROM action_tracker
            WHERE synced_date = ?
            GROUP BY status
            """,
            [latest_synced],
        ).fetchall()

    counts = {row["status"]: row["cnt"] for row in rows}
    total = sum(counts.values())
    done = counts.get("Done", 0)
    blocked = counts.get("Blocked", 0)
    in_progress = counts.get("In Progress", 0)
    todo = counts.get("To Do", 0)
    return {
        "synced_date": latest_synced,
        "total": total,
        "done": done,
        "blocked": blocked,
        "in_progress": in_progress,
        "todo": todo,
        "open": total - done,
    }


# ──────────────────────────────────────────────
# Use cases / data sources / sync runs
# ──────────────────────────────────────────────

def get_use_cases(
    status: str | None = None,
    use_case_type: str | None = None,
) -> list[dict]:
    with _conn() as con:
        if not _table_exists(con, "use_cases"):
            return []

        clauses = []
        params: list[Any] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        if use_case_type:
            clauses.append("use_case_type = ?")
            params.append(use_case_type)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        rows = con.execute(
            f"""
            SELECT *
            FROM use_cases
            {where}
            ORDER BY priority, use_case_type, name
            """,
            params,
        ).fetchall()

    result = _rows_to_list(rows)
    for item in result:
        item["source_systems"] = _json_loads_or(item.pop("source_systems_json", "[]"), [])
        item["core_tables"] = _json_loads_or(item.pop("core_tables_json", "[]"), [])
        item["outputs"] = _json_loads_or(item.pop("outputs_json", "[]"), [])
    return result


def get_use_case(use_case_id: str) -> dict | None:
    matches = [row for row in get_use_cases() if row["id"] == use_case_id]
    return matches[0] if matches else None


def upsert_data_source(data: dict) -> None:
    payload = {
        "id": data["id"],
        "source_type": data["source_type"],
        "source_name": data["source_name"],
        "ingestion_mode": data.get("ingestion_mode", "manual"),
        "refresh_sla_hours": data.get("refresh_sla_hours", 24),
        "active": 1 if data.get("active", True) else 0,
        "config_json": json.dumps(data.get("config", {}), ensure_ascii=False),
        "notes": data.get("notes", ""),
    }
    with _conn() as con:
        if not _table_exists(con, "data_sources"):
            raise RuntimeError("data_sources table is not initialized")
        con.execute(
            """
            INSERT INTO data_sources
                (id, source_type, source_name, ingestion_mode, refresh_sla_hours,
                 active, config_json, notes)
            VALUES
                (:id, :source_type, :source_name, :ingestion_mode, :refresh_sla_hours,
                 :active, :config_json, :notes)
            ON CONFLICT(id) DO UPDATE SET
                source_type = excluded.source_type,
                source_name = excluded.source_name,
                ingestion_mode = excluded.ingestion_mode,
                refresh_sla_hours = excluded.refresh_sla_hours,
                active = excluded.active,
                config_json = excluded.config_json,
                notes = excluded.notes,
                updated_at = datetime('now')
            """,
            payload,
        )


def get_data_sources(
    active: bool | None = None,
    source_type: str | None = None,
) -> list[dict]:
    with _conn() as con:
        if not _table_exists(con, "data_sources"):
            return []

        clauses = []
        params: list[Any] = []
        if active is not None:
            clauses.append("active = ?")
            params.append(1 if active else 0)
        if source_type:
            clauses.append("source_type = ?")
            params.append(source_type)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        rows = con.execute(
            f"""
            SELECT *
            FROM data_sources
            {where}
            ORDER BY source_type, source_name, id
            """,
            params,
        ).fetchall()

    result = _rows_to_list(rows)
    for item in result:
        item["config"] = _json_loads_or(item.pop("config_json", "{}"), {})
        item["active"] = bool(item.get("active"))
    return result


def get_data_source(source_id: str) -> dict | None:
    matches = [row for row in get_data_sources(active=None) if row["id"] == source_id]
    return matches[0] if matches else None


def start_sync_run(
    source_id: str,
    run_type: str = "manual",
    target_tables: list[str] | None = None,
    artifact_path: str = "",
    triggered_by: str = "cli",
    notes: str = "",
) -> str:
    run_id = f"sync-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"
    with _conn() as con:
        if not _table_exists(con, "sync_runs") or not _table_exists(con, "data_sources"):
            raise RuntimeError("sync tracking tables are not initialized")
        row = con.execute("SELECT 1 FROM data_sources WHERE id = ?", [source_id]).fetchone()
        if not row:
            raise ValueError(f"Data source '{source_id}' is not registered")
        con.execute(
            """
            INSERT INTO sync_runs
                (id, source_id, run_type, target_tables_json, artifact_path, triggered_by, notes)
            VALUES
                (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                run_id,
                source_id,
                run_type,
                json.dumps(target_tables or [], ensure_ascii=False),
                artifact_path,
                triggered_by,
                notes,
            ],
        )
    return run_id


def finish_sync_run(
    run_id: str,
    status: str = "success",
    rows_in: int = 0,
    rows_changed: int = 0,
    error_message: str = "",
    notes: str | None = None,
) -> None:
    with _conn() as con:
        if not _table_exists(con, "sync_runs"):
            raise RuntimeError("sync_runs table is not initialized")
        if notes is None:
            con.execute(
                """
                UPDATE sync_runs
                SET finished_at = datetime('now'),
                    status = ?,
                    rows_in = ?,
                    rows_changed = ?,
                    error_message = ?
                WHERE id = ?
                """,
                [status, rows_in, rows_changed, error_message, run_id],
            )
        else:
            con.execute(
                """
                UPDATE sync_runs
                SET finished_at = datetime('now'),
                    status = ?,
                    rows_in = ?,
                    rows_changed = ?,
                    error_message = ?,
                    notes = ?
                WHERE id = ?
                """,
                [status, rows_in, rows_changed, error_message, notes, run_id],
            )


def fail_sync_run(
    run_id: str,
    error_message: str,
    rows_in: int = 0,
    rows_changed: int = 0,
    notes: str | None = None,
) -> None:
    finish_sync_run(
        run_id,
        status="failed",
        rows_in=rows_in,
        rows_changed=rows_changed,
        error_message=error_message,
        notes=notes,
    )


def get_sync_runs(
    source_id: str | None = None,
    status: str | None = None,
    limit: int = 20,
) -> list[dict]:
    with _conn() as con:
        if not _table_exists(con, "sync_runs"):
            return []

        clauses = []
        params: list[Any] = []
        if source_id:
            clauses.append("sr.source_id = ?")
            params.append(source_id)
        if status:
            clauses.append("sr.status = ?")
            params.append(status)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        rows = con.execute(
            f"""
            SELECT sr.*, ds.source_name, ds.source_type
            FROM sync_runs sr
            LEFT JOIN data_sources ds ON ds.id = sr.source_id
            {where}
            ORDER BY
                CASE
                    WHEN COALESCE(sr.finished_at, '') != '' THEN sr.finished_at
                    ELSE sr.started_at
                END DESC,
                sr.started_at DESC
            LIMIT ?
            """,
            params + [limit],
        ).fetchall()

    result = _rows_to_list(rows)
    for item in result:
        item["target_tables"] = _json_loads_or(item.pop("target_tables_json", "[]"), [])
    return result


def get_data_source_freshness(active_only: bool = True) -> list[dict]:
    with _conn() as con:
        if not _table_exists(con, "data_sources"):
            return []

        rows = con.execute(
            """
            SELECT
                ds.*,
                sr.id AS latest_run_id,
                sr.run_type AS latest_run_type,
                sr.started_at AS latest_started_at,
                sr.finished_at AS latest_finished_at,
                sr.status AS latest_status,
                sr.rows_in AS latest_rows_in,
                sr.rows_changed AS latest_rows_changed,
                sr.target_tables_json AS latest_target_tables_json,
                sr.artifact_path AS latest_artifact_path,
                sr.triggered_by AS latest_triggered_by,
                sr.error_message AS latest_error_message,
                sr.notes AS latest_notes
            FROM data_sources ds
            LEFT JOIN sync_runs sr
              ON sr.id = (
                  SELECT sr2.id
                  FROM sync_runs sr2
                  WHERE sr2.source_id = ds.id
                  ORDER BY
                      CASE
                          WHEN COALESCE(sr2.finished_at, '') != '' THEN sr2.finished_at
                          ELSE sr2.started_at
                      END DESC,
                      sr2.started_at DESC
                  LIMIT 1
              )
            WHERE (? = 0 OR ds.active = 1)
            ORDER BY ds.source_type, ds.source_name, ds.id
            """,
            [1 if active_only else 0],
        ).fetchall()

    now = datetime.now()
    result = []
    for row in _rows_to_list(rows):
        row["config"] = _json_loads_or(row.pop("config_json", "{}"), {})
        row["active"] = bool(row.get("active"))
        row["latest_target_tables"] = _json_loads_or(
            row.pop("latest_target_tables_json", "[]"),
            [],
        )

        timestamp_text = row.get("latest_finished_at") or row.get("latest_started_at") or ""
        age_hours: float | None = None
        if timestamp_text:
            try:
                age_hours = round((now - datetime.fromisoformat(timestamp_text)).total_seconds() / 3600, 1)
            except ValueError:
                age_hours = None
        row["age_hours"] = age_hours

        freshness_state = "inactive"
        is_stale = False
        if row["active"]:
            latest_status = row.get("latest_status") or ""
            if not timestamp_text:
                freshness_state = "never_synced"
                is_stale = True
            elif latest_status == "running":
                freshness_state = "running"
            elif latest_status == "failed":
                freshness_state = "failed"
                is_stale = True
            elif latest_status == "partial":
                freshness_state = "partial"
                is_stale = age_hours is not None and age_hours > float(row.get("refresh_sla_hours") or 0)
            else:
                is_stale = age_hours is not None and age_hours > float(row.get("refresh_sla_hours") or 0)
                freshness_state = "stale" if is_stale else "fresh"

        row["freshness_state"] = freshness_state
        row["is_stale"] = is_stale
        result.append(row)
    return result


# ──────────────────────────────────────────────
# Safe use-case execution traces
# ──────────────────────────────────────────────

def save_execution_trace(trace: dict[str, Any]) -> None:
    """Persist a bounded, payload-free execution trace when storage is available."""
    with _conn() as con:
        if not _table_exists(con, "execution_traces"):
            return
        con.execute(
            """
            INSERT OR REPLACE INTO execution_traces
                (execution_id, use_case_id, operation, actor, correlation_id, status,
                 started_at, finished_at, duration_ms, evidence_summary_json,
                 freshness_summary_json, warning_codes_json, proposed_write_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                trace["execution_id"],
                trace["use_case_id"],
                trace["operation"],
                trace.get("actor", ""),
                trace.get("correlation_id") or "",
                trace["status"],
                trace["started_at"],
                trace["finished_at"],
                trace["duration_ms"],
                json.dumps(trace.get("evidence_summary", []), ensure_ascii=False),
                json.dumps(trace.get("freshness_summary", []), ensure_ascii=False),
                json.dumps(trace.get("warning_codes", []), ensure_ascii=False),
                trace.get("proposed_write_count", 0),
            ],
        )
        con.execute(
            """
            DELETE FROM execution_traces
            WHERE execution_id NOT IN (
                SELECT execution_id
                FROM execution_traces
                ORDER BY finished_at DESC, execution_id DESC
                LIMIT ?
            )
            """,
            [EXECUTION_TRACE_RETENTION],
        )


def get_execution_trace(execution_id: str) -> dict | None:
    """Return a persisted trace without business payloads or connector configuration."""
    with _conn() as con:
        if not _table_exists(con, "execution_traces"):
            return None
        row = con.execute(
            "SELECT * FROM execution_traces WHERE execution_id = ?",
            [execution_id],
        ).fetchone()
    if not row:
        return None
    result = dict(row)
    result["evidence_summary"] = _json_loads_or(result.pop("evidence_summary_json"), [])
    result["freshness_summary"] = _json_loads_or(result.pop("freshness_summary_json"), [])
    result["warning_codes"] = _json_loads_or(result.pop("warning_codes_json"), [])
    return result


# ──────────────────────────────────────────────
# Projects
# ──────────────────────────────────────────────

def get_all_projects(status: str | None = None) -> list[dict]:
    with _conn() as con:
        if status:
            rows = con.execute(
                "SELECT * FROM projects WHERE status=? ORDER BY priority",
                [status],
            ).fetchall()
        else:
            rows = con.execute(
                "SELECT * FROM projects ORDER BY priority"
            ).fetchall()
    projects = _rows_to_list(rows)
    for p in projects:
        p["tech_stack"] = json.loads(p.get("tech_stack") or "[]")
    return projects


def get_project(project_id: str) -> dict | None:
    with _conn() as con:
        row = con.execute(
            "SELECT * FROM projects WHERE id=?", [project_id]
        ).fetchone()
    if not row:
        return None
    p = dict(row)
    p["tech_stack"] = json.loads(p.get("tech_stack") or "[]")
    return p


def get_project_health_facts(project_id: str | None = None) -> list[dict]:
    """Return the latest local health observations without triggering a sync."""
    with _conn() as con:
        clauses = ["p.status = 'active'"]
        params: list[Any] = []
        if project_id:
            clauses.append("p.id = ?")
            params.append(project_id)
        rows = con.execute(
            f"""
            SELECT
                p.id AS project_id, p.name AS project_name, p.status AS project_status,
                p.priority AS project_priority, p.jira_key,
                b.id AS board_id, b.name AS board_name,
                h.id AS health_snapshot_id, h.snapshot_date AS health_snapshot_date,
                h.overall_score, h.overall_grade, h.velocity_score, h.sprint_score,
                h.defect_score, h.scope_score, h.sprint_name, h.risks_json,
                cs.id AS status_snapshot_id, cs.snapshot_date AS status_snapshot_date,
                cs.rag_status, cs.risks_text, cs.impact_text
            FROM projects p
            LEFT JOIN jira_board_configs b
              ON b.pm_project_id = p.id AND b.active = 1
            LEFT JOIN jira_health_snapshots h
              ON h.id = (
                SELECT latest_h.id FROM jira_health_snapshots latest_h
                WHERE latest_h.board_id = b.id
                ORDER BY latest_h.snapshot_date DESC, latest_h.id DESC LIMIT 1
              )
            LEFT JOIN confluence_status_snapshots cs
              ON cs.id = (
                SELECT latest_cs.id FROM confluence_status_snapshots latest_cs
                WHERE latest_cs.board_id = b.id
                ORDER BY latest_cs.snapshot_date DESC, latest_cs.id DESC LIMIT 1
              )
            WHERE {' AND '.join(clauses)}
            ORDER BY p.priority, p.name, b.name
            """,
            params,
        ).fetchall()

    grouped: dict[str, dict] = {}
    for row in _rows_to_list(rows):
        project = grouped.setdefault(
            row["project_id"],
            {
                "project_id": row["project_id"],
                "project_name": row["project_name"],
                "project_status": row["project_status"],
                "project_priority": row["project_priority"],
                "jira_key": row["jira_key"],
                "boards": [],
            },
        )
        if not row.get("board_id"):
            continue
        project["boards"].append(
            {
                "board_id": row["board_id"],
                "board_name": row["board_name"],
                "health_snapshot_id": row["health_snapshot_id"],
                "health_snapshot_date": row["health_snapshot_date"],
                "overall_score": row["overall_score"],
                "overall_grade": row["overall_grade"],
                "velocity_score": row["velocity_score"],
                "sprint_score": row["sprint_score"],
                "defect_score": row["defect_score"],
                "scope_score": row["scope_score"],
                "sprint_name": row["sprint_name"],
                "risks": _json_loads_or(row["risks_json"], []),
                "status_snapshot_id": row["status_snapshot_id"],
                "status_snapshot_date": row["status_snapshot_date"],
                "rag_status": row["rag_status"],
                "risks_text": row["risks_text"] or "",
                "impact_text": row["impact_text"] or "",
            }
        )
    return list(grouped.values())


def upsert_project(data: dict) -> None:
    data["tech_stack"] = json.dumps(data.get("tech_stack", []))
    data["updated_at"] = datetime.now().isoformat()
    with _conn() as con:
        con.execute(
            """
            INSERT INTO projects
                (id, name, jira_key, status, priority, lead_id, tech_stack,
                 start_date, target_end, notes, updated_at)
            VALUES
                (:id,:name,:jira_key,:status,:priority,:lead_id,:tech_stack,
                 :start_date,:target_end,:notes,:updated_at)
            ON CONFLICT(id) DO UPDATE SET
                name=excluded.name, status=excluded.status,
                priority=excluded.priority, tech_stack=excluded.tech_stack,
                target_end=excluded.target_end, notes=excluded.notes,
                updated_at=excluded.updated_at
            """,
            data,
        )


def get_plan_versions(status: str | None = None) -> list[dict]:
    with _conn() as con:
        if not _table_exists(con, "plan_versions"):
            return []
        if status:
            rows = con.execute(
                """
                SELECT *
                FROM plan_versions
                WHERE version_status=?
                ORDER BY
                    CASE scenario_type
                        WHEN 'forecast' THEN 0
                        WHEN 'baseline' THEN 1
                        WHEN 'approved' THEN 2
                        WHEN 'what_if' THEN 3
                        ELSE 4
                    END,
                    COALESCE(as_of_date, '') DESC,
                    plan_version_id
                """,
                [status],
            ).fetchall()
        else:
            rows = con.execute(
                """
                SELECT *
                FROM plan_versions
                ORDER BY
                    CASE version_status
                        WHEN 'active' THEN 0
                        WHEN 'draft' THEN 1
                        ELSE 2
                    END,
                    CASE scenario_type
                        WHEN 'forecast' THEN 0
                        WHEN 'baseline' THEN 1
                        WHEN 'approved' THEN 2
                        WHEN 'what_if' THEN 3
                        ELSE 4
                    END,
                    COALESCE(as_of_date, '') DESC,
                    plan_version_id
                """
            ).fetchall()
    return _rows_to_list(rows)


def get_default_plan_version() -> dict | None:
    versions = get_plan_versions(status="active")
    return versions[0] if versions else None


def get_capacity_rows(
    year: int,
    month: int,
    plan_version_id: str | None = None,
) -> tuple[list[dict], dict | None]:
    with _conn() as con:
        default_version = None
        plan_version_filter = plan_version_id

        if _table_exists(con, "plan_versions") and _table_exists(con, "monthly_allocations"):
            if not plan_version_filter:
                row = con.execute(
                    """
                    SELECT *
                    FROM plan_versions
                    WHERE version_status='active'
                    ORDER BY
                        CASE scenario_type
                            WHEN 'forecast' THEN 0
                            WHEN 'baseline' THEN 1
                            WHEN 'approved' THEN 2
                            WHEN 'what_if' THEN 3
                            ELSE 4
                        END,
                        COALESCE(as_of_date, '') DESC,
                        plan_version_id
                    LIMIT 1
                    """
                ).fetchone()
                if row:
                    default_version = dict(row)
                    plan_version_filter = row["plan_version_id"]
            elif _table_exists(con, "plan_versions"):
                row = con.execute(
                    "SELECT * FROM plan_versions WHERE plan_version_id=?",
                    [plan_version_filter],
                ).fetchone()
                default_version = dict(row) if row else None

        if _table_exists(con, "monthly_allocations") and _table_exists(con, "plan_versions") and plan_version_filter:
            rows = con.execute(
                """
                SELECT
                    e.id,
                    e.name,
                    e.level,
                    e.team,
                    COALESCE(SUM(ma.allocation), 0.0) AS month_load,
                    COUNT(ma.project_id)              AS proj_count,
                    GROUP_CONCAT(p.name, ' / ')       AS projects,
                    ma.plan_version_id
                FROM employees e
                LEFT JOIN monthly_allocations ma
                       ON e.id = ma.employee_id
                      AND ma.year = ?
                      AND ma.month = ?
                      AND COALESCE(ma.plan_version_id, '') = ?
                LEFT JOIN projects p ON ma.project_id = p.id
                WHERE e.status = 'active'
                GROUP BY e.id
                ORDER BY month_load ASC, e.name
                """,
                [year, month, plan_version_filter],
            ).fetchall()
        else:
            rows = con.execute(
                """
                SELECT
                    e.id,
                    e.name,
                    e.level,
                    e.team,
                    COALESCE(SUM(ma.allocation), 0.0) AS month_load,
                    COUNT(ma.project_id)              AS proj_count,
                    GROUP_CONCAT(p.name, ' / ')       AS projects
                FROM employees e
                LEFT JOIN monthly_allocations ma
                       ON e.id = ma.employee_id
                      AND ma.year = ?
                      AND ma.month = ?
                LEFT JOIN projects p ON ma.project_id = p.id
                WHERE e.status = 'active'
                GROUP BY e.id
                ORDER BY month_load ASC, e.name
                """,
                [year, month],
            ).fetchall()

    return _rows_to_list(rows), default_version


def get_staffing_facts(
    year: int,
    month: int,
    plan_version_id: str | None = None,
) -> tuple[list[dict], dict | None]:
    """Return period-aware member, allocation, and contract facts for staffing rules."""
    rows, plan_version = get_capacity_rows(year, month, plan_version_id)
    with _conn() as con:
        facts: list[dict] = []
        for row in rows:
            employee = con.execute(
                "SELECT * FROM employees WHERE id = ?",
                [row["id"]],
            ).fetchone()
            if not employee:
                continue
            item = dict(employee)
            item["skills"] = _json_loads_or(item.get("skills"), {})
            item["month_load"] = float(row.get("month_load") or 0.0)
            item["plan_version_id"] = (plan_version or {}).get("plan_version_id")
            hiref_id = item.get("current_hiref") or ""
            hiref = None
            if hiref_id:
                hiref_row = con.execute("SELECT * FROM hiref WHERE id = ?", [hiref_id]).fetchone()
                hiref = dict(hiref_row) if hiref_row else None
            item["contract"] = hiref
            next_hiref_id = item.get("next_hiref") or ""
            next_hiref = None
            if next_hiref_id:
                next_hiref_row = con.execute(
                    "SELECT * FROM hiref WHERE id = ?",
                    [next_hiref_id],
                ).fetchone()
                next_hiref = dict(next_hiref_row) if next_hiref_row else None
            item["next_contract"] = next_hiref
            facts.append(item)
    return facts, plan_version


def create_staffing_proposal(record: dict[str, Any]) -> None:
    with _conn() as con:
        con.execute(
            """
            INSERT INTO staffing_proposals
                (proposal_id, expires_at, confirmation_token, request_json, evidence_json, proposal_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                record["proposal_id"], record["expires_at"], record["confirmation_token"],
                json.dumps(record["request"], ensure_ascii=False),
                json.dumps(record["evidence"], ensure_ascii=False),
                json.dumps(record["proposal"], ensure_ascii=False),
            ],
        )


def get_staffing_proposal(proposal_id: str) -> dict | None:
    with _conn() as con:
        if not _table_exists(con, "staffing_proposals"):
            return None
        row = con.execute("SELECT * FROM staffing_proposals WHERE proposal_id = ?", [proposal_id]).fetchone()
    if not row:
        return None
    item = dict(row)
    for key in ("request", "evidence", "proposal"):
        item[key] = _json_loads_or(item.pop(f"{key}_json"), {})
    return item


def confirm_staffing_proposal(
    proposal_id: str,
    confirmation_token: str,
    revalidated_proposal: dict[str, Any],
) -> dict:
    """Atomically persist planned assignments, monthly allocations, and a decision record."""
    with _conn() as con:
        row = con.execute("SELECT * FROM staffing_proposals WHERE proposal_id = ?", [proposal_id]).fetchone()
        if not row:
            raise ValueError("Unknown staffing proposal")
        stored = dict(row)
        if stored["confirmation_token"] != confirmation_token:
            raise ValueError("Invalid confirmation token")
        if stored["status"] == "confirmed":
            return {"status": "confirmed", "decision_id": stored["decision_id"], "idempotent": True}
        if stored["status"] != "proposed":
            raise ValueError(f"Proposal is not confirmable: {stored['status']}")
        if datetime.fromisoformat(stored["expires_at"]) <= datetime.now():
            con.execute("UPDATE staffing_proposals SET status='expired' WHERE proposal_id=?", [proposal_id])
            return {"status": "expired", "decision_id": None, "idempotent": False}

        request = _json_loads_or(stored["request_json"], {})
        project = con.execute("SELECT name FROM projects WHERE id = ?", [request["project_id"]]).fetchone()
        if not project:
            raise ValueError("Target project no longer exists")
        selections = revalidated_proposal["selections"]
        for selection in selections:
            con.execute(
                """
                INSERT INTO assignments (employee_id, project_id, role, allocation, start_date, status)
                VALUES (?, ?, ?, ?, ?, 'planned')
                ON CONFLICT(employee_id, project_id, status) DO UPDATE SET
                    role=excluded.role, allocation=excluded.allocation, start_date=excluded.start_date
                """,
                [selection["member_id"], request["project_id"], request.get("role") or "developer",
                 selection["allocation"], request["start_period"] + "-01"],
            )
            for period in revalidated_proposal["periods"]:
                con.execute(
                    """
                    INSERT INTO monthly_allocations (employee_id, project_id, year, month, allocation, plan_version_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    [selection["member_id"], request["project_id"], period["year"], period["month"],
                     selection["allocation"], revalidated_proposal.get("plan_version_id") or ""],
                )
        decision = con.execute(
            """
            INSERT INTO decision_log (type, description, context, candidates, chosen, alternatives, project_id, member_ids)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                "staffing_proposal",
                f"Confirmed staffing proposal {proposal_id} for [{project['name']}]",
                json.dumps(request, ensure_ascii=False),
                json.dumps(revalidated_proposal.get("candidates", []), ensure_ascii=False),
                json.dumps(
                    {
                        "selections": selections,
                        "decision_safety": {
                            "decision_fingerprint": revalidated_proposal.get(
                                "decision_fingerprint"
                            ),
                            "rule_version": revalidated_proposal.get("rule_version"),
                            "source_states": revalidated_proposal.get(
                                "source_states", []
                            ),
                            "freshness_override": revalidated_proposal.get(
                                "freshness_override"
                            ),
                            "hiref_action_acknowledgement": (
                                revalidated_proposal.get(
                                    "hiref_action_acknowledgement"
                                )
                            ),
                            "role_policy": revalidated_proposal.get("role_policy"),
                        },
                    },
                    ensure_ascii=False,
                ),
                json.dumps([], ensure_ascii=False), request["project_id"],
                json.dumps([selection["member_id"] for selection in selections], ensure_ascii=False),
            ],
        )
        decision_id = decision.lastrowid
        con.execute(
            """UPDATE staffing_proposals SET status='confirmed', confirmed_at=datetime('now'),
               decision_id=? WHERE proposal_id=?""",
            [decision_id, proposal_id],
        )
    return {"status": "confirmed", "decision_id": decision_id, "idempotent": False}


def resolve_staffing_proposal(proposal_id: str, action: str, reason: str = "") -> bool:
    """Cancel or reject a still-unconfirmed proposal without touching domain allocations."""
    if action not in {"cancelled", "rejected"}:
        raise ValueError("Proposal action must be cancelled or rejected")
    with _conn() as con:
        cur = con.execute(
            """UPDATE staffing_proposals SET status=?, failure_reason=?
               WHERE proposal_id=? AND status='proposed'""",
            [action, reason, proposal_id],
        )
    return cur.rowcount == 1


# ──────────────────────────────────────────────
# Project snapshots
# ──────────────────────────────────────────────

def _normalize_string_list(values: Any) -> list[str]:
    if not values:
        return []
    if isinstance(values, str):
        stripped = values.strip()
        return [stripped] if stripped else []
    if not isinstance(values, list):
        return []
    result: list[str] = []
    for value in values:
        stripped = str(value).strip()
        if stripped:
            result.append(stripped)
    return result


def _normalize_project_snapshot(item: dict) -> dict:
    item["priorities"] = _json_loads_or(item.pop("priorities_json", "[]"), [])
    item["milestones"] = _json_loads_or(item.pop("milestones_json", "[]"), [])
    item["actions"] = _json_loads_or(item.pop("actions_json", "[]"), [])
    item["risks"] = _json_loads_or(item.pop("risks_json", "[]"), [])
    item["assumptions"] = _json_loads_or(item.pop("assumptions_json", "[]"), [])
    item["decisions"] = _json_loads_or(item.pop("decisions_json", "[]"), [])
    item["dependencies"] = _json_loads_or(item.pop("dependencies_json", "[]"), [])
    item["changes"] = _json_loads_or(item.pop("changes_json", "[]"), [])
    return item


def _legacy_plan_type_to_snapshot_shape(
    plan_type: str | None,
    origin_context: str | None,
    created_by: str | None,
) -> tuple[str, str, str]:
    legacy_type = (plan_type or "").strip()
    artifact_kind = "plan"
    horizon = "ad_hoc"
    generation_mode = "ai" if (created_by or "").strip().lower() == "ai" else "user"

    if legacy_type == "weekly_plan":
        horizon = "weekly"
        if (origin_context or "").strip() == "weekly-project-status":
            artifact_kind = "status"
    elif legacy_type == "milestone_plan":
        horizon = "milestone"
    elif legacy_type == "recovery_plan":
        artifact_kind = "recovery"
    elif legacy_type == "ai_draft":
        generation_mode = "ai"

    return artifact_kind, horizon, generation_mode


def _snapshot_to_legacy(item: dict) -> dict:
    legacy = dict(item)
    if legacy["artifact_kind"] == "recovery":
        plan_type = "recovery_plan"
    elif legacy["generation_mode"] == "ai":
        plan_type = "ai_draft"
    elif legacy["horizon"] == "milestone":
        plan_type = "milestone_plan"
    elif legacy["horizon"] == "weekly":
        plan_type = "weekly_plan"
    else:
        plan_type = legacy["artifact_kind"]

    legacy["use_case_id"] = legacy.get("origin_context") or None
    legacy["plan_version_id"] = legacy.get("staffing_scenario_id")
    legacy["supersedes_id"] = legacy.get("supersedes_snapshot_id")
    legacy["plan_type"] = plan_type
    legacy["as_of_date"] = legacy["snapshot_date"]
    legacy["status"] = legacy["artifact_state"]
    legacy["summary_text"] = legacy["summary"]
    legacy["plan"] = {
        "items": legacy.get("priorities", []),
        "milestones": legacy.get("milestones", []),
        "actions": legacy.get("actions", []),
        "decisions": legacy.get("decisions", []),
        "dependencies": legacy.get("dependencies", []),
        "changes": legacy.get("changes", []),
    }
    return legacy


def create_project_snapshot(data: dict) -> str:
    snapshot_id = data.get("id")
    if not snapshot_id:
        project_slug = slugify_text(str(data.get("project_id", "snapshot")))[:24] or "snapshot"
        snapshot_id = (
            f"snapshot-{project_slug}-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
        )

    staffing_scenario_id = (data.get("staffing_scenario_id") or "").strip() or None
    source_run_id = (data.get("source_run_id") or "").strip() or None
    supersedes_snapshot_id = (data.get("supersedes_snapshot_id") or "").strip() or None
    payload = {
        "id": snapshot_id,
        "project_id": data["project_id"],
        "snapshot_date": data.get("snapshot_date") or datetime.today().date().isoformat(),
        "artifact_kind": data.get("artifact_kind", "plan"),
        "horizon": data.get("horizon", "ad_hoc"),
        "artifact_state": data.get("artifact_state", "draft"),
        "health": data.get("health", "unknown"),
        "title": data.get("title", ""),
        "summary": data.get("summary", ""),
        "priorities_json": json.dumps(_normalize_string_list(data.get("priorities")), ensure_ascii=False),
        "milestones_json": json.dumps(_normalize_string_list(data.get("milestones")), ensure_ascii=False),
        "actions_json": json.dumps(_normalize_string_list(data.get("actions")), ensure_ascii=False),
        "risks_json": json.dumps(_normalize_string_list(data.get("risks")), ensure_ascii=False),
        "assumptions_json": json.dumps(_normalize_string_list(data.get("assumptions")), ensure_ascii=False),
        "decisions_json": json.dumps(_normalize_string_list(data.get("decisions")), ensure_ascii=False),
        "dependencies_json": json.dumps(_normalize_string_list(data.get("dependencies")), ensure_ascii=False),
        "changes_json": json.dumps(_normalize_string_list(data.get("changes")), ensure_ascii=False),
        "staffing_scenario_id": staffing_scenario_id,
        "supersedes_snapshot_id": supersedes_snapshot_id,
        "origin_context": data.get("origin_context", ""),
        "generation_mode": data.get("generation_mode", "user"),
        "source_run_id": source_run_id,
        "created_by": data.get("created_by", "user"),
    }

    with _conn() as con:
        if not _table_exists(con, "project_snapshots"):
            raise RuntimeError("project_snapshots table is not initialized")
        con.execute(
            """
            INSERT INTO project_snapshots
                (id, project_id, snapshot_date, artifact_kind, horizon, artifact_state, health,
                 title, summary, priorities_json, milestones_json, actions_json, risks_json,
                 assumptions_json, decisions_json, dependencies_json, changes_json,
                 staffing_scenario_id, supersedes_snapshot_id, origin_context, generation_mode,
                 source_run_id, created_by)
            VALUES
                (:id, :project_id, :snapshot_date, :artifact_kind, :horizon, :artifact_state, :health,
                 :title, :summary, :priorities_json, :milestones_json, :actions_json, :risks_json,
                 :assumptions_json, :decisions_json, :dependencies_json, :changes_json,
                 :staffing_scenario_id, :supersedes_snapshot_id, :origin_context, :generation_mode,
                 :source_run_id, :created_by)
            """,
            payload,
        )
    return snapshot_id


def get_project_snapshots(
    project_id: str | None = None,
    artifact_kind: str | None = None,
    artifact_state: str | None = None,
    health: str | None = None,
    horizon: str | None = None,
    generation_mode: str | None = None,
    limit: int = 20,
) -> list[dict]:
    with _conn() as con:
        if not _table_exists(con, "project_snapshots"):
            return []

        clauses = []
        params: list[Any] = []
        if project_id:
            clauses.append("ps.project_id = ?")
            params.append(project_id)
        if artifact_kind:
            clauses.append("ps.artifact_kind = ?")
            params.append(artifact_kind)
        if artifact_state:
            clauses.append("ps.artifact_state = ?")
            params.append(artifact_state)
        if health:
            clauses.append("ps.health = ?")
            params.append(health)
        if horizon:
            clauses.append("ps.horizon = ?")
            params.append(horizon)
        if generation_mode:
            clauses.append("ps.generation_mode = ?")
            params.append(generation_mode)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        rows = con.execute(
            f"""
            SELECT
                ps.*,
                p.name AS project_name
            FROM project_snapshots ps
            JOIN projects p ON p.id = ps.project_id
            {where}
            ORDER BY ps.snapshot_date DESC, ps.created_at DESC
            LIMIT ?
            """,
            params + [limit],
        ).fetchall()

    result = _rows_to_list(rows)
    return [_normalize_project_snapshot(item) for item in result]


def get_project_snapshot(snapshot_id: str) -> dict | None:
    with _conn() as con:
        if not _table_exists(con, "project_snapshots"):
            return None
        row = con.execute(
            """
            SELECT
                ps.*,
                p.name AS project_name
            FROM project_snapshots ps
            JOIN projects p ON p.id = ps.project_id
            WHERE ps.id = ?
            """,
            [snapshot_id],
        ).fetchone()
    if not row:
        return None
    return _normalize_project_snapshot(dict(row))


def create_project_plan_snapshot(data: dict) -> str:
    artifact_kind, horizon, generation_mode = _legacy_plan_type_to_snapshot_shape(
        data.get("plan_type"),
        data.get("use_case_id"),
        data.get("created_by"),
    )
    plan = _json_loads_or(data.get("plan_json", {}), {})
    priorities = []
    if isinstance(plan, dict):
        priorities = _normalize_string_list(plan.get("items"))
    elif isinstance(plan, list):
        priorities = _normalize_string_list(plan)

    return create_project_snapshot(
        {
            "id": data.get("id"),
            "project_id": data["project_id"],
            "snapshot_date": data.get("as_of_date"),
            "artifact_kind": data.get("artifact_kind", artifact_kind),
            "horizon": data.get("horizon", horizon),
            "artifact_state": data.get("status", "draft"),
            "health": data.get("health", "unknown"),
            "title": data.get("title", ""),
            "summary": data.get("summary_text", ""),
            "priorities": data.get("priorities", priorities),
            "milestones": data.get("milestones", []),
            "actions": data.get("actions", []),
            "risks": data.get("risks_json", []),
            "assumptions": data.get("assumptions_json", []),
            "decisions": data.get("decisions", []),
            "dependencies": data.get("dependencies", []),
            "changes": data.get("changes", []),
            "staffing_scenario_id": data.get("plan_version_id"),
            "supersedes_snapshot_id": data.get("supersedes_id"),
            "origin_context": data.get("use_case_id", ""),
            "generation_mode": data.get("generation_mode", generation_mode),
            "source_run_id": data.get("source_run_id"),
            "created_by": data.get("created_by", "user"),
        }
    )


def get_project_plan_snapshots(
    project_id: str | None = None,
    plan_type: str | None = None,
    status: str | None = None,
    limit: int = 20,
) -> list[dict]:
    snapshots = get_project_snapshots(
        project_id=project_id,
        artifact_state=status,
        limit=limit if not plan_type else max(limit * 3, limit),
    )
    if plan_type:
        snapshots = [
            item for item in snapshots
            if _snapshot_to_legacy(item)["plan_type"] == plan_type
        ]
    return [_snapshot_to_legacy(item) for item in snapshots[:limit]]


def get_project_plan_snapshot(snapshot_id: str) -> dict | None:
    row = get_project_snapshot(snapshot_id)
    return _snapshot_to_legacy(row) if row else None


# ──────────────────────────────────────────────
# Assignments
# ──────────────────────────────────────────────

def get_project_team(project_id: str) -> list[dict]:
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM v_project_team WHERE project_id=?", [project_id]
        ).fetchall()
    return _rows_to_list(rows)


def create_assignment(
    employee_id: str,
    project_id: str,
    role: str,
    allocation: float,
    start_date: str | None = None,
) -> int:
    with _conn() as con:
        resolved_id = _resolve_employee_id(con, employee_id)
        if not resolved_id:
            raise ValueError(f"Employee '{employee_id}' does not exist")
        existing = con.execute(
            """
            SELECT id
            FROM assignments
            WHERE employee_id = ? AND project_id = ? AND status = 'active'
            LIMIT 1
            """,
            [resolved_id, project_id],
        ).fetchone()
        if existing:
            return existing["id"]
        cur = con.execute(
            """
            INSERT INTO assignments (employee_id, project_id, role, allocation, start_date)
            VALUES (?, ?, ?, ?, ?)
            """,
            [resolved_id, project_id, role, allocation, start_date or datetime.today().date().isoformat()],
        )
        return cur.lastrowid  # type: ignore[return-value]


def end_assignment(employee_id: str, project_id: str) -> None:
    with _conn() as con:
        resolved_id = _resolve_employee_id(con, employee_id)
        if not resolved_id:
            raise ValueError(f"Employee '{employee_id}' does not exist")
        con.execute(
            """
            UPDATE assignments SET status='ended', end_date=date('now')
            WHERE employee_id=? AND project_id=? AND status='active'
            """,
            [resolved_id, project_id],
        )


# ──────────────────────────────────────────────
# Action Items
# ──────────────────────────────────────────────

def get_action_items(
    status: str | None = "open",
    owner_id: str | None = None,
    overdue_only: bool = False,
) -> list[dict]:
    if overdue_only:
        with _conn() as con:
            rows = con.execute("SELECT * FROM v_overdue_actions").fetchall()
        return _rows_to_list(rows)

    clauses = []
    params: list[Any] = []
    if status:
        clauses.append("ai.status=?")
        params.append(status)
    if owner_id:
        clauses.append("ai.owner_id=?")
        params.append(owner_id)

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    sql = f"""
        SELECT ai.*, e.name AS owner_name
        FROM action_items ai
        LEFT JOIN employees e ON ai.owner_id = e.id
        {where}
        ORDER BY
            CASE ai.priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
            ai.due_date
    """
    with _conn() as con:
        rows = con.execute(sql, params).fetchall()
    return _rows_to_list(rows)


def create_action_item(data: dict) -> int:
    with _conn() as con:
        cur = con.execute(
            """
            INSERT INTO action_items (title, owner_id, source, priority, due_date, notes)
            VALUES (:title, :owner_id, :source, :priority, :due_date, :notes)
            """,
            data,
        )
        return cur.lastrowid  # type: ignore[return-value]


def complete_action_item(item_id: int) -> None:
    with _conn() as con:
        con.execute(
            "UPDATE action_items SET status='done', completed_at=datetime('now') WHERE id=?",
            [item_id],
        )


# ──────────────────────────────────────────────
# Decision Log queries (read side)
# ──────────────────────────────────────────────

def get_decision_outcomes(member_id: str, task_type: str) -> list[dict]:
    """
    Return resolved decisions where this member was chosen for this task_type.
    Used by scoring.calc_track_record().
    """
    with _conn() as con:
        resolved_id = _resolve_employee_id(con, member_id)
        if not resolved_id:
            return []
        rows = con.execute(
            """
            SELECT outcome FROM decision_log
            WHERE json_extract(member_ids, '$') LIKE ?
              AND json_extract(context, '$.task_type') = ?
              AND outcome != 'pending'
            ORDER BY created_at DESC
            LIMIT 20
            """,
            [f"%{resolved_id}%", task_type],
        ).fetchall()
    return _rows_to_list(rows)


def get_recent_decisions(limit: int = 10) -> list[dict]:
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM decision_log ORDER BY created_at DESC LIMIT ?",
            [limit],
        ).fetchall()
    return _rows_to_list(rows)
