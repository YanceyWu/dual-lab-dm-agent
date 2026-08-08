"""
PM Dashboard API server.

Run:
    pm dashboard serve
    python3 -m pm_agent.dashboard
"""

from __future__ import annotations

import io
import json
import os
import sqlite3
from contextlib import redirect_stdout
from datetime import datetime
from pathlib import Path

from flask import Flask, Response, jsonify, request, send_from_directory

from pm_agent.attention import AttentionService
from pm_agent.config import get_database_path
from pm_agent.connectors import jira as jira_connector
from pm_agent.database import repository
from pm_agent.dashboard.surface_manifest import surface_config_payload
from pm_agent.dashboard.write_operations import (
    claim_sync_operation,
    create_sync_preview,
    finish_sync_operation,
)
from pm_agent.rules.hiref import (
    contract_review_counts_available,
    contract_slot_counts_available,
    days_until,
    hiref_urgency,
)
from pm_agent.use_cases import use_case_executor
from pm_agent.use_cases.service import UseCaseRequest
from pm_agent.weekly_brief.operations import confirm_capture, preview_capture

APP_DIR = Path(__file__).resolve().parent
REPO_ROOT = APP_DIR.parents[1]
WEB_DIR = APP_DIR / "web"


def _resolve_db_path() -> str:
    return str(get_database_path())


# Optional explicit override retained for tests and embedded launchers. Normal
# runtime resolution happens at connection time.
DB: str | None = None
app = Flask(__name__, static_folder=str(WEB_DIR), static_url_path="")

LEGACY_DIRECT_SQL_ROUTES = {
    "/api/use-cases",
    "/api/sync-runs",
    "/api/freshness",
    "/api/allocations",
    "/api/project-plans",
    "/api/project-health",
}
LEGACY_RESULT_PROJECTION_ROUTES = {
    "/api/hiref",
}
CANONICAL_RESULT_PROJECTION_ROUTES = {
    "/api/project-snapshots",
}
CURRENT_STATE_CANONICAL_ROUTES = {
    "/api/summary",
    "/api/projects",
    "/api/employees",
}


@app.after_request
def _mark_legacy_interface(response):
    if request.path in CURRENT_STATE_CANONICAL_ROUTES:
        response.headers["X-DM-Interface-Contract"] = "current-state-staffing-canonical-read"
    elif request.path in CANONICAL_RESULT_PROJECTION_ROUTES:
        response.headers["X-DM-Interface-Contract"] = "project-snapshot-list-projection-v1"
    elif request.path in LEGACY_DIRECT_SQL_ROUTES:
        response.headers["X-DM-Interface-Contract"] = "legacy-direct-read"
    elif request.path in LEGACY_RESULT_PROJECTION_ROUTES:
        response.headers["X-DM-Interface-Contract"] = "legacy-result-projection"
    return response


def db():
    conn = sqlite3.connect(DB or _resolve_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def _current_state_member_coverage(members: list[dict]) -> str:
    if not members:
        return "unknown"
    states = {str(member.get("current_state_staffing_state") or "unknown") for member in members}
    if "unavailable" in states:
        return "unavailable"
    if "unknown" in states:
        return "partial" if "known" in states else "unknown"
    return "known"


def _current_state_publication_freshness() -> dict:
    return repository.get_current_state_staffing_publication_freshness()


def _contract_coverage_publication_freshness() -> dict:
    return repository.get_contract_coverage_publication_freshness()


def _contract_counts_available(freshness_state: str) -> bool:
    return freshness_state in {"fresh", "stale"}


def _contract_review_counts_available_from_publication(
    publication_freshness: dict,
) -> bool:
    return contract_review_counts_available(publication_freshness)


def _contract_slot_counts_available_from_publication(
    publication_freshness: dict,
    slot_rows: list[dict] | None = None,
) -> bool:
    return contract_slot_counts_available(publication_freshness, slot_rows)


def _is_hiref_alert(row: dict) -> bool:
    return bool(row.get("current_hiref_missing")) or (
        not row.get("next_hiref")
        and row.get("urgency") in {"expired", "critical", "high", "medium"}
    )


def jl(text):
    try:
        return json.loads(text or "[]")
    except (TypeError, json.JSONDecodeError):
        return []


def jd(text, default):
    try:
        return json.loads(text or json.dumps(default))
    except (TypeError, json.JSONDecodeError):
        return default


def table_exists(conn, table_name):
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type IN ('table','view') AND name=?",
        [table_name],
    ).fetchone()
    return row is not None


def normalize_project_snapshot(item):
    item["priorities"] = jd(item.pop("priorities_json", "[]"), [])
    item["milestones"] = jd(item.pop("milestones_json", "[]"), [])
    item["actions"] = jd(item.pop("actions_json", "[]"), [])
    item["risks"] = jd(item.pop("risks_json", "[]"), [])
    item["assumptions"] = jd(item.pop("assumptions_json", "[]"), [])
    item["decisions"] = jd(item.pop("decisions_json", "[]"), [])
    item["dependencies"] = jd(item.pop("dependencies_json", "[]"), [])
    item["changes"] = jd(item.pop("changes_json", "[]"), [])
    return item

def get_freshness_rows(conn):
    if not table_exists(conn, "data_sources") or not table_exists(conn, "sync_runs"):
        return []
    rows = conn.execute("""
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
        ORDER BY ds.source_type, ds.source_name, ds.id
    """).fetchall()

    result = []
    now = datetime.now()
    for row in rows:
        item = dict(row)
        item["config"] = jd(item.pop("config_json", "{}"), {})
        item["latest_target_tables"] = jd(item.pop("latest_target_tables_json", "[]"), [])
        item["active"] = bool(item.get("active"))
        timestamp_text = item.get("latest_finished_at") or item.get("latest_started_at") or ""
        age_hours = None
        if timestamp_text:
            try:
                age_hours = round((now - datetime.fromisoformat(timestamp_text)).total_seconds() / 3600, 1)
            except ValueError:
                age_hours = None
        item["age_hours"] = age_hours

        if not item["active"]:
            freshness_state = "inactive"
            is_stale = False
        elif not timestamp_text:
            freshness_state = "never_synced"
            is_stale = True
        elif item.get("latest_status") == "running":
            freshness_state = "running"
            is_stale = False
        elif item.get("latest_status") == "failed":
            freshness_state = "failed"
            is_stale = True
        elif item.get("latest_status") == "partial":
            freshness_state = "partial"
            is_stale = age_hours is not None and age_hours > float(item.get("refresh_sla_hours") or 0)
        else:
            is_stale = age_hours is not None and age_hours > float(item.get("refresh_sla_hours") or 0)
            freshness_state = "stale" if is_stale else "fresh"

        item["freshness_state"] = freshness_state
        item["is_stale"] = is_stale
        result.append(item)
    return result


def _get_active_jira_boards(conn):
    rows = conn.execute(
        """
        SELECT id, name, pm_project_id
        FROM jira_board_configs
        WHERE COALESCE(active, 0) = 1
        ORDER BY name, id
        """
    ).fetchall()
    return [dict(row) for row in rows]


def _needs_jira_refresh(freshness_item):
    if not freshness_item or not freshness_item.get("active"):
        return False
    state = freshness_item.get("freshness_state")
    return state in {"never_synced", "stale", "failed", "partial"}


def _stale_jira_board_ids(conn):
    freshness_rows = get_freshness_rows(conn)
    freshness_map = {row["id"]: row for row in freshness_rows}
    board_ids = []
    for board in _get_active_jira_boards(conn):
        board_id = board["id"]
        release_state = freshness_map.get(f"jira-release-{board_id}")
        health_state = freshness_map.get(f"jira-health-{board_id}")
        if (
            release_state is None
            or health_state is None
            or _needs_jira_refresh(release_state)
            or _needs_jira_refresh(health_state)
        ):
            board_ids.append(board_id)
    return board_ids


def _run_jira_sync(board_id):
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        jira_connector.sync_releases(board=board_id, dry_run=False)
        jira_connector.sync_health(board=board_id, dry_run=False)
    return buffer.getvalue()


def _dashboard_actor() -> str:
    actor = os.getenv("PM_DASHBOARD_ACTOR", "dashboard-local-user").strip()
    return actor[:100] or "dashboard-local-user"


def _safe_sync_error_code(exc: Exception) -> str:
    name = type(exc).__name__.lower()
    text = str(exc).lower()
    if "auth" in name or "auth" in text or "401" in text or "403" in text:
        return "JIRA_AUTH_FAILED"
    if "timeout" in name or "timeout" in text:
        return "JIRA_TIMEOUT"
    if "connection" in name or "network" in text:
        return "JIRA_NETWORK_FAILED"
    return "JIRA_SYNC_FAILED"

def int_arg(name, default=20, minimum=1, maximum=200):
    raw = request.args.get(name, str(default))
    try:
        value = int(raw)
    except (TypeError, ValueError):
        value = default
    return max(minimum, min(maximum, value))

@app.route("/")
def index():
    return send_from_directory(str(WEB_DIR), "index.html")


@app.route("/dashboard-config.js")
def dashboard_config():
    payload = json.dumps(surface_config_payload(), ensure_ascii=False, sort_keys=True)
    return Response(
        f"CONFIG.PRODUCT_SURFACE = {payload};\n",
        mimetype="application/javascript",
    )

@app.route("/api/summary")
def summary():
    c = db()
    members = repository.get_all_members()
    total_staff = len(members)
    active_proj   = c.execute("SELECT COUNT(*) FROM projects  WHERE status='active'").fetchone()[0]
    member_coverage = _current_state_member_coverage(members)
    publication_freshness = _current_state_publication_freshness()
    freshness_state = str(publication_freshness.get("state") or "unknown")
    contract_publication_freshness = _contract_coverage_publication_freshness()
    contract_freshness_state = str(
        contract_publication_freshness.get("state") or "unknown"
    )
    known_members = [
        member for member in members if isinstance(member.get("current_load"), (int, float))
    ]
    avg_load = (
        round((sum(float(member["current_load"]) for member in known_members) / len(known_members)) * 100, 1)
        if member_coverage == "known" and freshness_state in {"fresh", "stale"} and known_members
        else None
    )
    overloaded = (
        sum(1 for member in known_members if float(member["current_load"]) > 1.0)
        if member_coverage == "known" and freshness_state in {"fresh", "stale"}
        else None
    )
    hiref_slots = repository.get_hiref_contracts()
    if _contract_review_counts_available_from_publication(
        contract_publication_freshness
    ):
        hiref_review_rows = repository.get_hiref_staff_review(days=60)
        hiref_60d = sum(
            1
            for row in hiref_review_rows
            if _is_hiref_alert(row)
        )
    else:
        hiref_60d = None
    if _contract_slot_counts_available_from_publication(
        contract_publication_freshness,
        hiref_slots,
    ):
        free_hiref = sum(
            1 for row in hiref_slots if row.get("is_free")
        )
    else:
        free_hiref = None
    focus_proj    = c.execute("SELECT COUNT(*) FROM project_profiles WHERE is_focus=1").fetchone()[0]
    stfte_count   = c.execute("SELECT COUNT(*) FROM employees WHERE status='active' AND resource_type='STFTE'").fetchone()[0]
    ltfte_count   = c.execute("SELECT COUNT(*) FROM employees WHERE status='active' AND resource_type='LTFTE'").fetchone()[0]
    freshness_rows = get_freshness_rows(c)
    stale_sources  = sum(1 for row in freshness_rows if row.get("active") and row.get("is_stale"))
    last_success_sync = None
    active_project_snapshots = 0
    if table_exists(c, "sync_runs"):
        last_success_sync = c.execute(
            "SELECT MAX(finished_at) FROM sync_runs WHERE status = 'success'"
        ).fetchone()[0]
    if table_exists(c, "project_snapshots"):
        active_project_snapshots = c.execute(
            "SELECT COUNT(*) FROM project_snapshots WHERE artifact_state IN ('draft','active')"
        ).fetchone()[0]
    c.close()
    return jsonify({
        "total_staff": total_staff, "ltfte": ltfte_count, "stfte": stfte_count,
        "active_projects": active_proj, "focus_projects": focus_proj,
        "avg_load": avg_load, "overloaded": overloaded,
        "current_state_staffing_state": member_coverage,
        "current_state_staffing_freshness_state": freshness_state,
        "current_state_staffing_freshness_reason": publication_freshness.get("state_reason"),
        "current_state_staffing_publication_id": publication_freshness.get("publication_id"),
        "contract_coverage_freshness_state": contract_freshness_state,
        "contract_coverage_freshness_reason": contract_publication_freshness.get("state_reason"),
        "contract_coverage_publication_id": contract_publication_freshness.get("publication_id"),
        "hiref_alerts_60d": hiref_60d, "free_hiref_slots": free_hiref,
        "last_successful_sync": last_success_sync,
        "stale_sources_count": stale_sources,
        "active_project_snapshots": active_project_snapshots,
        "active_plan_snapshots": active_project_snapshots,
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

@app.route("/api/use-cases")
def use_cases():
    c = db()
    if not table_exists(c, "use_cases"):
        c.close()
        return jsonify([])
    rows = c.execute("""
        SELECT *
        FROM use_cases
        ORDER BY priority, use_case_type, name
    """).fetchall()
    c.close()
    result = []
    for row in rows:
        item = dict(row)
        item["source_systems"] = jd(item.pop("source_systems_json", "[]"), [])
        item["core_tables"] = jd(item.pop("core_tables_json", "[]"), [])
        item["outputs"] = jd(item.pop("outputs_json", "[]"), [])
        result.append(item)
    return jsonify(result)

@app.route("/api/sync-runs")
def sync_runs():
    c = db()
    if not table_exists(c, "sync_runs"):
        c.close()
        return jsonify([])
    source_id = request.args.get("source_id", "").strip()
    limit = int_arg("limit", default=20, minimum=1, maximum=200)
    clauses = []
    params = []
    if source_id:
        clauses.append("sr.source_id = ?")
        params.append(source_id)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    rows = c.execute(f"""
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
    """, params + [limit]).fetchall()
    c.close()
    result = []
    for row in rows:
        item = dict(row)
        item["target_tables"] = jd(item.pop("target_tables_json", "[]"), [])
        result.append(item)
    return jsonify(result)

@app.route("/api/freshness")
def freshness():
    c = db()
    rows = get_freshness_rows(c)
    c.close()
    return jsonify(rows)

@app.route("/api/projects")
def projects():
    c = db()
    contract_publication_freshness = _contract_coverage_publication_freshness()
    contract_freshness_state = str(
        contract_publication_freshness.get("state") or "unknown"
    )
    member_lookup = {}
    for member in repository.get_all_members():
        for key in [
            str(member.get("id") or ""),
            str(member.get("wd_id") or ""),
            *(str(value or "") for value in member.get("external_ids", [])),
        ]:
            if key:
                member_lookup[key] = member
    plan_join = ""
    plan_fields = [
        "NULL as latest_snapshot_date",
        "NULL as latest_plan_snapshot_date",
        "0 as snapshot_count",
        "0 as plan_snapshot_count",
    ]
    if table_exists(c, "project_snapshots"):
        plan_join = """
        LEFT JOIN (
            SELECT project_id, MAX(snapshot_date) as latest_snapshot_date, COUNT(*) as snapshot_count
            FROM project_snapshots
            GROUP BY project_id
        ) plans ON p.id=plans.project_id
        """
        plan_fields = [
            "plans.latest_snapshot_date",
            "plans.latest_snapshot_date as latest_plan_snapshot_date",
            "plans.snapshot_count",
            "plans.snapshot_count as plan_snapshot_count",
        ]
    select_fields = [
        "p.id",
        "p.name",
        "pp.phase",
        "pp.phase_detail",
        "pp.priority_tier",
        "pp.is_focus",
        "pp.objective",
        "pp.milestones",
        "pp.stakeholders",
        *plan_fields,
    ]
    rows = c.execute(f"""
        SELECT {", ".join(select_fields)}
        FROM projects p
        LEFT JOIN project_profiles pp ON p.id=pp.project_id
        {plan_join}
        WHERE p.status='active'
        GROUP BY p.id ORDER BY COALESCE(pp.priority_tier,99), p.name
    """).fetchall()
    result = []
    for r in rows:
        p = dict(r)
        p["milestones"]   = jl(p.get("milestones"))
        p["stakeholders"] = jl(p.get("stakeholders"))
        p["phase"]        = p.get("phase") or "TBC"
        team_snapshot = repository.get_project_team_snapshot(p["id"])
        planned_members = [
            dict(row)
            for row in c.execute(
                """
                SELECT e.wd_id, e.id, e.name, a.allocation, a.status as assign_status,
                       a.start_date, a.end_date
                FROM assignments a
                JOIN employees e ON a.employee_id=e.id
                WHERE a.project_id=? AND a.status='planned'
                ORDER BY a.start_date, e.name
                """,
                [p["id"]],
            ).fetchall()
        ]
        p["current_state_staffing_state"] = team_snapshot["state"]
        p["current_state_staffing_reason"] = team_snapshot["state_reason"]
        p["current_state_staffing_freshness_state"] = team_snapshot.get("freshness_state")
        p["current_state_staffing_freshness_reason"] = team_snapshot.get("freshness_reason")
        p["current_state_staffing_publication_id"] = (
            (team_snapshot.get("publication") or {}).get("publication_id")
            if isinstance(team_snapshot.get("publication"), dict)
            else None
        )
        p["contract_coverage_freshness_state"] = contract_freshness_state
        p["contract_coverage_freshness_reason"] = contract_publication_freshness.get(
            "state_reason"
        )
        p["contract_coverage_publication_id"] = contract_publication_freshness.get(
            "publication_id"
        )
        if team_snapshot["state"] == "known":
            active_members = []
            active_member_ids: list[str] = []
            for row in team_snapshot["assignments"]:
                member_projection = member_lookup.get(str(row["member_id"]))
                member_id = (
                    str(member_projection.get("id") or row["member_id"])
                    if member_projection
                    else str(row["member_id"])
                )
                active_member_ids.append(member_id)
                active_members.append(
                    {
                        "wd_id": (
                            str(member_projection.get("wd_id") or row["member_id"])
                            if member_projection
                            else row["member_id"]
                        ),
                        "id": member_id,
                        "name": (
                            str(member_projection.get("name") or row["display_name"])
                            if member_projection
                            else row["display_name"]
                        ),
                        "allocation": row["allocation"],
                        "assign_status": "active",
                        "start_date": None,
                        "end_date": None,
                    }
                )
            if team_snapshot.get("freshness_state") in {"fresh", "stale"}:
                p["members"] = active_members + planned_members
                p["team_size"] = len(p["members"])
                if _contract_counts_available(contract_freshness_state):
                    member_ids = list(
                        dict.fromkeys(active_member_ids + [row["id"] for row in planned_members])
                    )
                    hiref_risk = 0
                    for member_id in member_ids:
                        member_projection = member_lookup.get(str(member_id))
                        if not member_projection or not member_projection.get("current_hiref"):
                            continue
                        days_remaining = days_until(
                            member_projection.get("billing_end_date")
                        )
                        if (
                            days_remaining is not None
                            and days_remaining <= 90
                            and not member_projection.get("next_hiref")
                        ):
                            hiref_risk += 1
                    p["hiref_risk"] = hiref_risk
                else:
                    p["hiref_risk"] = None
            else:
                p["members"] = planned_members
                p["team_size"] = None
                p["hiref_risk"] = None
        else:
            p["team_size"] = None
            p["members"] = planned_members
            p["hiref_risk"] = None
        result.append(p)
    c.close()
    return jsonify(result)

@app.route("/api/employees")
def employees():
    c = db()
    contract_publication_freshness = _contract_coverage_publication_freshness()
    review_counts_available = _contract_review_counts_available_from_publication(
        contract_publication_freshness
    )
    result = []
    for member in repository.get_all_members():
        emp = dict(member)
        freshness_state = str(
            emp.get("current_state_staffing_freshness_state") or "unknown"
        )
        project_details = list(emp.pop("current_state_project_details", []))
        emp.pop("current_state_projects", None)
        emp.pop("external_ids", None)
        emp["load_pct"] = (
            round(float(emp["current_load"]) * 100)
        if freshness_state in {"fresh", "stale"}
        and isinstance(emp.get("current_load"), (int, float))
        else None
        )
        emp["is_contractor"] = emp.get("resource_type") == "STFTE"
        emp["contract_review_counts_available"] = review_counts_available
        emp["projects"] = [
            {
                "name": item["project_name"],
                "allocation": item["allocation"],
            }
            for item in project_details
        ]
        # Next planned assignment (Problem 2 - show future visibility)
        next_plan = c.execute("""
            SELECT p.name, a.allocation, a.start_date
            FROM assignments a JOIN projects p ON a.project_id=p.id
            WHERE a.employee_id=? AND a.status='planned'
            ORDER BY a.start_date LIMIT 1
        """, [emp["id"]]).fetchone()
        if next_plan:
            emp["next_assignment"] = {
                "name": next_plan["name"],
                "allocation": round(next_plan["allocation"] * 100),
                "start_date": next_plan["start_date"]
            }
        if review_counts_available and emp.get("current_hiref"):
            h = c.execute("SELECT start_date, end_date, project FROM hiref WHERE id=?", [emp["current_hiref"]]).fetchone()
            if h:
                emp["hiref_start_date"] = h["start_date"]
                emp["hiref_end_date"] = h["end_date"]
                emp["hiref_project"]  = h["project"]
                d = days_until(h["end_date"])
                emp["hiref_urgency"] = hiref_urgency(d, bool(emp.get("next_hiref")))
                emp["hiref_days"]    = d
        if review_counts_available and emp.get("next_hiref"):
            h = c.execute("SELECT start_date, end_date, project FROM hiref WHERE id=?", [emp["next_hiref"]]).fetchone()
            if h:
                emp["next_hiref_start_date"] = h["start_date"]
                emp["next_hiref_end_date"] = h["end_date"]
                emp["next_hiref_project"] = h["project"]
        result.append(emp)
    c.close()
    return jsonify(result)


@app.route("/api/use-cases/team-workload-overview")
def team_workload_overview():
    """Renderer-neutral workload result for external or future agent clients."""
    team = request.args.get("team")
    result = use_case_executor.execute(
        UseCaseRequest(
            use_case_id="team-workload-overview",
            actor="dashboard",
            parameters={"team": team} if team else {},
            requested_output="json",
        )
    )
    return jsonify(result.model_dump())


@app.route("/api/tool/query/<use_case_id>", methods=["POST"])
def structured_use_case_query(use_case_id: str):
    """Full read-only executor contract for Dashboard and local clients."""
    descriptor = use_case_executor.describe(use_case_id)
    if descriptor is None:
        result = use_case_executor.execute(
            UseCaseRequest(
                use_case_id=use_case_id,
                actor="dashboard",
                requested_output="json",
            )
        )
        return jsonify(result.model_dump()), 404
    if not descriptor.read_only:
        return jsonify(
            {
                "contract_version": descriptor.contract_version,
                "status": "invalid",
                "warnings": [{"code": "DASHBOARD_WRITE_ROUTE_NOT_ALLOWED"}],
            }
        ), 405
    payload = request.get_json(silent=True) or {}
    parameters = payload.get("parameters", {})
    if not isinstance(parameters, dict):
        return jsonify(
            {
                "contract_version": descriptor.contract_version,
                "status": "invalid",
                "warnings": [
                    {"code": "PARAMETER_OBJECT_REQUIRED", "field": "parameters"}
                ],
            }
        ), 400
    correlation_id = payload.get("correlation_id")
    if correlation_id is not None and not isinstance(correlation_id, str):
        return jsonify(
            {
                "contract_version": descriptor.contract_version,
                "status": "invalid",
                "warnings": [
                    {"code": "CORRELATION_ID_INVALID", "field": "correlation_id"}
                ],
            }
        ), 400
    result = use_case_executor.execute(
        UseCaseRequest(
            contract_version=str(
                payload.get("contract_version") or descriptor.contract_version
            ),
            use_case_id=use_case_id,
            operation="query",
            actor="dashboard",
            parameters=parameters,
            requested_output="json",
            correlation_id=correlation_id,
        )
    )
    status_code = {
        "invalid": 400,
        "unavailable": 404,
        "failed": 503,
    }.get(result.status, 200)
    response = jsonify(result.model_dump(mode="json"))
    response.headers["X-DM-Interface-Contract"] = "use-case-result-v1"
    return response, status_code


@app.route("/api/weekly-brief/operations", methods=["POST"])
def weekly_brief_operations():
    """Dedicated preview/confirm endpoint; generic query routes remain read-only."""
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"status": "failed", "warnings": ["WEEKLY_BRIEF_CAPTURE_CANDIDATE_INVALID"]}), 400
    if payload.get("operation") == "preview":
        allowed = {"operation", "candidate", "idempotency_key", "expires_in_seconds"}
        if set(payload) - allowed or not isinstance(payload.get("candidate"), dict) or not isinstance(payload.get("idempotency_key"), str):
            return jsonify({"status": "failed", "warnings": ["WEEKLY_BRIEF_CAPTURE_CANDIDATE_INVALID"]}), 400
        result = preview_capture(candidate=payload["candidate"], actor_id=_dashboard_actor(), idempotency_key=payload["idempotency_key"], expires_in_seconds=payload.get("expires_in_seconds", 600), db_path=DB)
    elif payload.get("operation") == "confirm":
        allowed = {"operation", "operation_id", "confirmation_token"}
        if set(payload) - allowed or not isinstance(payload.get("operation_id"), str) or not isinstance(payload.get("confirmation_token"), str):
            return jsonify({"status": "failed", "warnings": ["WEEKLY_BRIEF_CAPTURE_TOKEN_INVALID"]}), 400
        result = confirm_capture(operation_id=payload["operation_id"], confirmation_token=payload["confirmation_token"], db_path=DB)
    else:
        return jsonify({"status": "failed", "warnings": ["WEEKLY_BRIEF_CAPTURE_CANDIDATE_INVALID"]}), 400
    response = jsonify(result)
    if result.get("status") in {"previewed", "confirmed", "already_confirmed", "expired", "stale"}:
        response.headers["X-DM-Interface-Contract"] = "weekly-brief-operation-v1"
        return response, 200
    return response, 400


@app.route("/api/attention/operations", methods=["POST"])
def attention_operations():
    """Dedicated JSON projection of Attention preview/confirm operations."""
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _attention_response(
            {"status": "failed", "failure_code": "ATTENTION_PREVIEW_INVALID"}
        )
    operation = payload.get("operation")
    if operation == "confirm":
        allowed = {"operation", "operation_id", "confirmation_token"}
        if (
            set(payload) - allowed
            or not isinstance(payload.get("operation_id"), str)
            or not isinstance(payload.get("confirmation_token"), str)
        ):
            return _attention_response(
                {
                    "status": "failed",
                    "failure_code": "ATTENTION_CONFIRMATION_INVALID",
                }
            )
        result = AttentionService().confirm(
            operation_id=payload["operation_id"],
            confirmation_token=payload["confirmation_token"],
        )
        return _attention_response(result)

    if operation != "preview" or not isinstance(payload.get("action"), str):
        return _attention_response(
            {"status": "failed", "failure_code": "ATTENTION_PREVIEW_INVALID"}
        )

    service = AttentionService()
    action = payload["action"]
    if action == "reconcile":
        allowed = {
            "operation",
            "action",
            "rule_keys",
            "subject_kind",
            "subject_id",
        }
        rule_keys = payload.get("rule_keys")
        if (
            set(payload) - allowed
            or (rule_keys is not None and not isinstance(rule_keys, list))
        ):
            result = {
                "status": "failed",
                "failure_code": "ATTENTION_PREVIEW_INVALID",
            }
        else:
            result = service.preview_reconciliation(
                actor=_dashboard_actor(),
                rule_keys=rule_keys,
                subject_kind=payload.get("subject_kind"),
                subject_id=payload.get("subject_id"),
            )
    elif action == "acknowledge":
        allowed = {"operation", "action", "attention_id"}
        if (
            set(payload) - allowed
            or not isinstance(payload.get("attention_id"), str)
        ):
            result = {
                "status": "failed",
                "failure_code": "ATTENTION_PREVIEW_INVALID",
            }
        else:
            result = service.preview_acknowledgement(
                attention_id=payload["attention_id"],
                actor=_dashboard_actor(),
            )
    elif action == "snooze":
        allowed = {
            "operation",
            "action",
            "attention_id",
            "snoozed_until",
        }
        if (
            set(payload) - allowed
            or not isinstance(payload.get("attention_id"), str)
            or not isinstance(payload.get("snoozed_until"), str)
        ):
            result = {
                "status": "failed",
                "failure_code": "ATTENTION_PREVIEW_INVALID",
            }
        else:
            result = service.preview_snooze(
                attention_id=payload["attention_id"],
                actor=_dashboard_actor(),
                snoozed_until=payload["snoozed_until"],
            )
    else:
        result = {
            "status": "failed",
            "failure_code": "ATTENTION_PREVIEW_INVALID",
        }
    return _attention_response(result)


def _attention_response(result):
    code = result.get("failure_code", "")
    status_code = 200
    if result.get("status") not in {"proposed", "success"}:
        if code in {"ATTENTION_NOT_FOUND", "ATTENTION_OPERATION_NOT_FOUND"}:
            status_code = 404
        elif code == "ATTENTION_CONFIRMATION_EXPIRED":
            status_code = 410
        elif code == "DATA_ACCESS_FAILED":
            status_code = 503
        elif code in {
            "ATTENTION_OPERATION_ALREADY_USED",
            "ATTENTION_ALREADY_ACKNOWLEDGED",
            "ATTENTION_SNOOZE_UNCHANGED",
            "ATTENTION_CONFIGURATION_UNCHANGED",
            "ATTENTION_CONFIGURATION_STALE",
            "ATTENTION_ALREADY_RESOLVED",
            "ATTENTION_STILL_ACTIVE",
            "ATTENTION_NOT_ACTIVE",
            "ATTENTION_RULE_DISABLED",
        }:
            status_code = 409
        else:
            status_code = 400
    response = jsonify(result)
    if status_code == 200:
        response.headers["X-DM-Interface-Contract"] = "attention-operation-v1"
    return response, status_code


@app.route("/api/hiref")
def hiref():
    contract_publication_freshness = _contract_coverage_publication_freshness()
    contract_freshness_state = str(
        contract_publication_freshness.get("state") or "unknown"
    )
    review_counts_available = _contract_review_counts_available_from_publication(
        contract_publication_freshness
    )
    hiref_list = repository.get_hiref_contracts()
    slot_counts_available = _contract_slot_counts_available_from_publication(
        contract_publication_freshness,
        hiref_list,
    )
    expiring_list = repository.get_hiref_staff_review(days=180)
    for item in expiring_list:
        item["actual_project"] = item.get("actual_project_display") or "-"
    return jsonify({
        "all_hiref": hiref_list,
        "expiring_staff": expiring_list,
        "total": len(hiref_list),
        "free_count": (
            sum(1 for h in hiref_list if h["is_free"])
            if slot_counts_available
            else None
        ),
        "assigned_count": (
            sum(1 for h in hiref_list if not h["is_free"])
            if slot_counts_available
            else None
        ),
        "next_covered_count": (
            sum(1 for h in expiring_list if h.get("next_hiref"))
            if review_counts_available
            else None
        ),
        "mismatch_count": (
            sum(
                1
                for h in expiring_list
                if h.get("project_alignment_status") == "mismatch"
            )
            if review_counts_available
            else None
        ),
        "review_counts_available": review_counts_available,
        "contract_coverage_freshness_state": contract_freshness_state,
        "contract_coverage_freshness_reason": contract_publication_freshness.get(
            "state_reason"
        ),
        "contract_coverage_publication_id": contract_publication_freshness.get(
            "publication_id"
        ),
    })

@app.route("/api/allocations")
def allocations():
    c = db()
    rows = c.execute("""
        SELECT ma.employee_id, e.name, e.wd_id, ma.project_id, p.name as project_name,
               ma.plan_version_id,
               ma.year, ma.month, ma.allocation
        FROM monthly_allocations ma
        JOIN employees e ON ma.employee_id=e.id
        JOIN projects p ON ma.project_id=p.id
        WHERE e.status='active'
        AND (ma.year*100 + ma.month) >= 202605
        ORDER BY ma.year, ma.month, e.name
    """).fetchall()
    c.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/project-snapshots")
def project_snapshots():
    project_id = request.args.get("project_id", "").strip()
    limit = int_arg("limit", default=20, minimum=1, maximum=200)
    artifact_kind = request.args.get("kind", "").strip()
    artifact_state = request.args.get("state", request.args.get("status", "")).strip()
    health = request.args.get("health", "").strip()
    horizon = request.args.get("horizon", "").strip()
    parameters = {key: value for key, value in {"project_id": project_id, "artifact_kind": artifact_kind, "artifact_state": artifact_state, "health": health, "horizon": horizon}.items() if value}
    parameters["limit"] = limit
    result = use_case_executor.execute(UseCaseRequest(use_case_id="project-snapshot-list", actor="dashboard", parameters=parameters, requested_output="json"))
    return jsonify(result.data["snapshots"])


@app.route("/api/project-plans")
def project_plans():
    c = db()
    if not table_exists(c, "project_plan_snapshots"):
        c.close()
        return jsonify([])
    project_id = request.args.get("project_id", "").strip()
    limit = int_arg("limit", default=20, minimum=1, maximum=200)
    clauses = []
    params = []
    if project_id:
        clauses.append("pps.project_id = ?")
        params.append(project_id)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    rows = c.execute(f"""
        SELECT
            pps.*,
            p.name AS project_name,
            uc.name AS use_case_name
        FROM project_plan_snapshots pps
        JOIN projects p ON p.id = pps.project_id
        LEFT JOIN use_cases uc ON uc.id = pps.use_case_id
        {where}
        ORDER BY pps.as_of_date DESC, pps.created_at DESC
        LIMIT ?
    """, params + [limit]).fetchall()
    c.close()
    result = []
    for row in rows:
        item = dict(row)
        item["plan"] = jd(item.pop("plan_json", "{}"), {})
        item["assumptions"] = jd(item.pop("assumptions_json", "[]"), [])
        item["risks"] = jd(item.pop("risks_json", "[]"), [])
        result.append(item)
    return jsonify(result)

@app.route("/api/project-health")
def project_health():
    c = db()
    freshness_rows = get_freshness_rows(c)
    freshness_map = {row["id"]: row for row in freshness_rows}
    # Latest JIRA health snapshot per board
    jira = {}
    for r in c.execute("""
        SELECT
            h.*,
            jsv.name AS version_name,
            jsv.release_date AS release_date
        FROM jira_health_snapshots h
        LEFT JOIN jira_stream_versions jsv
          ON h.version_id = jsv.id
         AND h.board_id = jsv.board_id
        INNER JOIN (
            SELECT board_id, MAX(snapshot_date) as latest FROM jira_health_snapshots GROUP BY board_id
        ) mx ON h.board_id=mx.board_id AND h.snapshot_date=mx.latest
    """).fetchall():
        jira[r['board_id']] = dict(r)

    # Latest Confluence status snapshot per board
    conf = {}
    for r in c.execute("""
        SELECT s.* FROM confluence_status_snapshots s
        INNER JOIN (
            SELECT board_id, MAX(snapshot_date) as latest FROM confluence_status_snapshots GROUP BY board_id
        ) mx ON s.board_id=mx.board_id AND s.snapshot_date=mx.latest
    """).fetchall():
        conf[r['board_id']] = dict(r)

    # Board configs with project mapping
    boards = c.execute("SELECT * FROM jira_board_configs WHERE active=1").fetchall()

    # Build per-project health (for projects with a board link)
    project_health_map = {}
    for b in boards:
        b = dict(b)
        bid = b['id']
        entry = {
            'board_id': bid,
            'board_name': b['name'],
            'pm_project_id': b['pm_project_id'],
            'board_url': b['board_url'],
            'jira': jira.get(bid),
            'confluence': conf.get(bid),
            'freshness': {
                'jira_release': freshness_map.get(f'jira-release-{bid}'),
                'jira_health': freshness_map.get(f'jira-health-{bid}'),
                'confluence_status': freshness_map.get('confluence-status-batch'),
            },
        }
        project_health_map[bid] = entry
        # Also index by pm_project_id for project card lookup
        if b['pm_project_id']:
            project_health_map[b['pm_project_id']] = entry

    # Also include confluence-only boards (no JIRA health snapshots)
    for bid, snap in conf.items():
        if bid not in project_health_map:
            project_health_map[bid] = {
                'board_id': bid,
                'board_name': bid.replace('_',' ').title(),
                'pm_project_id': None,
                'board_url': '',
                'jira': jira.get(bid),
                'confluence': snap,
            }

    # Projects list with profiles
    projects = c.execute("""
        SELECT p.id, p.name, p.jira_key, p.status,
               pp.phase, pp.priority_tier, pp.key_risks, pp.is_focus, pp.objective
        FROM projects p
        LEFT JOIN project_profiles pp ON p.id=pp.project_id
        WHERE p.status='active'
        ORDER BY COALESCE(pp.priority_tier,9), p.name
    """).fetchall()

    result = []
    for p in projects:
        p = dict(p)
        health = project_health_map.get(p['id'])
        p['health'] = health
        result.append(p)

    # Also include standalone boards not linked to a project
    linked_ids = set(r['id'] for r in projects)
    for bid, entry in project_health_map.items():
        if entry.get('pm_project_id') is None and bid not in linked_ids and bid == entry.get('board_id'):
            result.append({
                'id': bid, 'name': entry['board_name'],
                'jira_key': None, 'status': 'active',
                'phase': None, 'priority_tier': None,
                'key_risks': '[]', 'is_focus': 0, 'objective': None,
                'health': entry
            })

    c.close()
    return jsonify(result)


@app.route("/api/project-health/sync", methods=["POST"])
def project_health_sync():
    payload = request.get_json(silent=True) or {}
    operation = str(payload.get("operation") or "").strip().lower()
    board_id = str(payload.get("board_id") or "").strip()
    stale_only = bool(payload.get("stale_only"))

    if operation == "confirm":
        operation_id = str(payload.get("operation_id") or "").strip()
        confirmation_token = str(payload.get("confirmation_token") or "").strip()
        if not operation_id or not confirmation_token:
            return jsonify(
                {
                    "success": False,
                    "code": "SYNC_CONFIRMATION_REQUIRED",
                    "message": "A preview operation and confirmation token are required.",
                }
            ), 400
        c = db()
        try:
            claimed, error_code = claim_sync_operation(
                c,
                operation_id=operation_id,
                confirmation_token=confirmation_token,
            )
        finally:
            c.close()
        if error_code:
            status = 404 if error_code == "SYNC_OPERATION_NOT_FOUND" else 409
            return jsonify(
                {
                    "success": False,
                    "code": error_code,
                    "message": "The sync confirmation is invalid, expired, or already used.",
                    "execution_id": operation_id,
                }
            ), status

        results = []
        failures = []
        for target_id in claimed["scope"]["board_ids"]:
            try:
                _run_jira_sync(target_id)
                results.append({"board_id": target_id, "success": True})
            except Exception as exc:
                error_code = _safe_sync_error_code(exc)
                failures.append(error_code)
                results.append(
                    {
                        "board_id": target_id,
                        "success": False,
                        "code": error_code,
                    }
                )
        safe_result = {
            "target_count": len(results),
            "succeeded_count": sum(1 for item in results if item["success"]),
            "failed_count": len(failures),
            "results": results,
        }
        c = db()
        try:
            finish_sync_operation(
                c,
                operation_id=operation_id,
                success=not failures,
                result=safe_result,
                failure_code="JIRA_SYNC_PARTIAL_FAILURE" if failures else "",
            )
        finally:
            c.close()
        response = {
            "success": not failures,
            "code": "JIRA_SYNC_PARTIAL_FAILURE" if failures else "JIRA_SYNC_COMPLETED",
            "message": (
                "Some JIRA sync actions failed."
                if failures
                else "JIRA release and health sync completed."
            ),
            "execution_id": operation_id,
            "actor": claimed["actor"],
            **safe_result,
        }
        return jsonify(response), 502 if failures else 200

    if operation != "preview":
        return jsonify(
            {
                "success": False,
                "code": "SYNC_PREVIEW_REQUIRED",
                "message": "Request a sync preview before confirmation.",
            }
        ), 400

    c = db()
    try:
        active_boards = _get_active_jira_boards(c)
        board_map = {board["id"]: board for board in active_boards}
        if board_id:
            board = board_map.get(board_id)
            if not board:
                return jsonify(
                    {
                        "success": False,
                        "code": "SYNC_TARGET_NOT_FOUND",
                        "message": "The requested board is unknown or inactive.",
                    }
                ), 404
            targets = [board]
        elif stale_only:
            stale_ids = _stale_jira_board_ids(c)
            targets = [board_map[target_id] for target_id in stale_ids if target_id in board_map]
            if not targets:
                return jsonify(
                    {
                        "success": True,
                        "code": "SYNC_NOT_REQUIRED",
                        "message": "No stale JIRA boards need syncing.",
                        "requires_confirmation": False,
                        "targets": [],
                    }
                )
        else:
            return jsonify(
                {
                    "success": False,
                    "code": "SYNC_SCOPE_REQUIRED",
                    "message": "Provide one board or request stale-board scope.",
                }
            ), 400

        preview = create_sync_preview(c, targets=targets, actor=_dashboard_actor())
    finally:
        c.close()

    return jsonify(
        {
            "success": True,
            "code": "SYNC_PREVIEW_READY",
            "message": "Review the target scope before starting the JIRA sync.",
            "requires_confirmation": True,
            "execution_id": preview["operation_id"],
            "confirmation_token": preview["confirmation_token"],
            "expires_at": preview["expires_at"],
            "actor": preview["actor"],
            "scope": preview["scope"],
            "targets": [
                {"board_id": target["id"], "board_name": target["name"]}
                for target in targets
            ],
        }
    )


def serve(
    host: str = "127.0.0.1",
    port: int = 5001,
    debug: bool = False,
    allow_remote: bool = False,
) -> None:
    if host not in {"127.0.0.1", "localhost", "::1"} and not allow_remote:
        raise ValueError(
            "Non-loopback Dashboard binding requires explicit allow_remote=True."
        )
    print("\n  PM Dashboard starting...")
    print(f"  Open:  http://{host}:{port}\n")
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    serve()
