"""
PM Dashboard API server.

Run:
    pm dashboard serve
    python3 -m pm_agent.dashboard
"""

from __future__ import annotations

import io
import json
import sqlite3
from contextlib import redirect_stdout
from datetime import datetime, date
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from pm_agent.config import get_database_path
from pm_agent.connectors import jira as jira_connector
from pm_agent.database import repository
from pm_agent.use_cases import use_case_executor
from pm_agent.use_cases.service import UseCaseRequest

APP_DIR = Path(__file__).resolve().parent
REPO_ROOT = APP_DIR.parents[1]
WEB_DIR = APP_DIR / "web"


def _resolve_db_path() -> str:
    return str(get_database_path())


# Optional explicit override retained for tests and embedded launchers. Normal
# runtime resolution happens at connection time.
DB: str | None = None
app = Flask(__name__, static_folder=str(WEB_DIR), static_url_path="")

def db():
    conn = sqlite3.connect(DB or _resolve_db_path())
    conn.row_factory = sqlite3.Row
    return conn


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

def int_arg(name, default=20, minimum=1, maximum=200):
    raw = request.args.get(name, str(default))
    try:
        value = int(raw)
    except (TypeError, ValueError):
        value = default
    return max(minimum, min(maximum, value))


def days_until(date_str):
    try:
        return (date.fromisoformat(date_str) - date.today()).days
    except (TypeError, ValueError):
        return 9999


def urgency(days):
    if days <= 0:
        return "expired"
    if days <= 60:
        return "critical"
    if days <= 90:
        return "high"
    if days <= 180:
        return "medium"
    return "ok"


def hiref_urgency(days, has_next_hiref=False):
    if has_next_hiref:
        return "ok"
    return urgency(days)

@app.route("/")
def index():
    return send_from_directory(str(WEB_DIR), "index.html")

@app.route("/api/summary")
def summary():
    c = db()
    total_staff   = c.execute("SELECT COUNT(*) FROM employees WHERE status='active'").fetchone()[0]
    active_proj   = c.execute("SELECT COUNT(*) FROM projects  WHERE status='active'").fetchone()[0]
    avg_load_row  = c.execute("SELECT AVG(current_load) FROM v_member_load").fetchone()
    avg_load      = round((avg_load_row[0] or 0) * 100, 1)
    overloaded    = c.execute("SELECT COUNT(*) FROM v_member_load WHERE current_load > 1.0").fetchone()[0]
    hiref_60d     = c.execute("""
        SELECT COUNT(*) FROM employees e JOIN hiref h ON e.current_hiref=h.id
        WHERE e.status='active' AND h.end_date <= date('now','+60 days')
          AND COALESCE(e.next_hiref, '') = ''
    """).fetchone()[0]
    free_hiref    = c.execute("""
        SELECT COUNT(*)
        FROM hiref h
        LEFT JOIN employees e
          ON (e.current_hiref=h.id OR e.next_hiref=h.id) AND e.status='active'
        WHERE e.id IS NULL
    """).fetchone()[0]
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
    plan_join = ""
    plan_fields = (
        "NULL as latest_snapshot_date, NULL as latest_plan_snapshot_date, "
        "0 as snapshot_count, 0 as plan_snapshot_count,"
    )
    if table_exists(c, "project_snapshots"):
        plan_join = """
        LEFT JOIN (
            SELECT project_id, MAX(snapshot_date) as latest_snapshot_date, COUNT(*) as snapshot_count
            FROM project_snapshots
            GROUP BY project_id
        ) plans ON p.id=plans.project_id
        """
        plan_fields = (
            "plans.latest_snapshot_date, plans.latest_snapshot_date as latest_plan_snapshot_date, "
            "plans.snapshot_count, plans.snapshot_count as plan_snapshot_count,"
        )
    rows = c.execute(f"""
        SELECT p.id, p.name, pp.phase, pp.phase_detail, pp.priority_tier, pp.is_focus,
               pp.objective, pp.milestones, pp.stakeholders,
               {plan_fields}
               COUNT(a.id) as team_size
        FROM projects p
        LEFT JOIN project_profiles pp ON p.id=pp.project_id
        {plan_join}
        LEFT JOIN assignments a ON p.id=a.project_id AND a.status IN ('active','planned')
        WHERE p.status='active'
        GROUP BY p.id ORDER BY COALESCE(pp.priority_tier,99), p.name
    """).fetchall()
    result = []
    for r in rows:
        p = dict(r)
        p["milestones"]   = jl(p.get("milestones"))
        p["stakeholders"] = jl(p.get("stakeholders"))
        p["phase"]        = p.get("phase") or "TBC"
        members = c.execute("""
            SELECT e.wd_id, e.id, e.name, a.allocation, a.status as assign_status,
                   a.start_date, a.end_date
            FROM assignments a JOIN employees e ON a.employee_id=e.id
            WHERE a.project_id=? AND a.status IN ('active','planned') ORDER BY a.status, e.name
        """, [p["id"]]).fetchall()
        p["members"] = [dict(m) for m in members]
        # HIREF risk
        hiref_risk = c.execute("""
            SELECT COUNT(*) FROM employees e
            JOIN hiref h ON e.current_hiref=h.id
            JOIN assignments a ON e.id=a.employee_id
            WHERE a.project_id=? AND a.status IN ('active','planned') AND h.end_date <= date('now','+90 days')
        """, [p["id"]]).fetchone()[0]
        p["hiref_risk"] = hiref_risk
        result.append(p)
    c.close()
    return jsonify(result)

@app.route("/api/employees")
def employees():
    c = db()
    rows = c.execute("""
        SELECT e.wd_id, e.id, e.name, e.resource_type, e.role, e.level, e.team,
               e.current_hiref, e.next_hiref, v.current_load, v.active_projects, e.skills
        FROM employees e
        LEFT JOIN v_member_load v ON e.id=v.id
        WHERE e.status='active' ORDER BY e.name
    """).fetchall()
    result = []
    for r in rows:
        emp = dict(r)
        emp["load_pct"] = round((emp.get("current_load") or 0) * 100)
        emp["is_contractor"] = emp.get("resource_type") == "STFTE"
        try:
            emp["skills"] = json.loads(emp.get("skills") or "{}")
        except (TypeError, json.JSONDecodeError):
            emp["skills"] = {}
        projs = c.execute("""
            SELECT p.name, a.allocation FROM assignments a
            JOIN projects p ON a.project_id=p.id
            WHERE a.employee_id=? AND a.status='active'
        """, [emp["id"]]).fetchall()
        emp["projects"] = [dict(p) for p in projs]
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
        if emp.get("current_hiref"):
            h = c.execute("SELECT start_date, end_date, project FROM hiref WHERE id=?", [emp["current_hiref"]]).fetchone()
            if h:
                emp["hiref_start_date"] = h["start_date"]
                emp["hiref_end_date"] = h["end_date"]
                emp["hiref_project"]  = h["project"]
                d = days_until(h["end_date"])
                emp["hiref_urgency"] = hiref_urgency(d, bool(emp.get("next_hiref")))
                emp["hiref_days"]    = d
        if emp.get("next_hiref"):
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

@app.route("/api/hiref")
def hiref():
    hiref_list = repository.get_hiref_contracts()
    expiring_list = repository.get_hiref_staff_review(days=180)
    for item in expiring_list:
        item["actual_project"] = item.get("actual_project_display") or "-"
    return jsonify({
        "all_hiref": hiref_list,
        "expiring_staff": expiring_list,
        "total": len(hiref_list),
        "free_count": sum(1 for h in hiref_list if h["is_free"]),
        "assigned_count": sum(1 for h in hiref_list if not h["is_free"]),
        "next_covered_count": sum(1 for h in expiring_list if h.get("next_hiref")),
        "mismatch_count": sum(
            1 for h in expiring_list if h.get("project_alignment_status") == "mismatch"
        ),
    })

@app.route("/api/allocations")
def allocations():
    c = db()
    rows = c.execute("""
        SELECT ma.employee_id, e.name, e.wd_id, ma.project_id, p.name as project_name,
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
    board_id = str(payload.get("board_id") or "").strip()
    stale_only = bool(payload.get("stale_only"))

    c = db()
    try:
        active_boards = _get_active_jira_boards(c)
        board_map = {board["id"]: board for board in active_boards}
        if board_id:
            board = board_map.get(board_id)
            if not board:
                return jsonify({"message": f"Unknown or inactive board: {board_id}"}), 404
            targets = [board]
        elif stale_only:
            stale_ids = _stale_jira_board_ids(c)
            targets = [board_map[target_id] for target_id in stale_ids if target_id in board_map]
            if not targets:
                return jsonify(
                    {
                        "success": True,
                        "message": "No stale JIRA boards need syncing.",
                        "results": [],
                    }
                )
        else:
            return jsonify({"message": "Provide board_id or stale_only=true."}), 400
    finally:
        c.close()

    results = []
    failures = []
    for target in targets:
        try:
            output = _run_jira_sync(target["id"])
            results.append(
                {
                    "board_id": target["id"],
                    "board_name": target["name"],
                    "success": True,
                    "log_tail": "\n".join(output.splitlines()[-20:]),
                }
            )
        except Exception as exc:
            failures.append(target["id"])
            results.append(
                {
                    "board_id": target["id"],
                    "board_name": target["name"],
                    "success": False,
                    "error": str(exc),
                }
            )

    if failures:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Some JIRA sync actions failed.",
                    "results": results,
                }
            ),
            500,
        )

    board_names = ", ".join(target["name"] for target in targets)
    return jsonify(
        {
            "success": True,
            "message": f"JIRA release + health sync completed for: {board_names}",
            "results": results,
        }
    )

def serve(host: str = "127.0.0.1", port: int = 5001, debug: bool = False) -> None:
    print("\n  PM Dashboard starting...")
    print(f"  Open:  http://{host}:{port}\n")
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    serve()
