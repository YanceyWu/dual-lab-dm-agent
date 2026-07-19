"""
pm_agent.sync.jira.release_sync — Sync JIRA release versions & issue progress into pm.db.

Auth: Uses repo-native Atlassian auth resolution from pm_agent.connectors.shared.atlassian.
      Token state is stored only under .auth/atlassian/tokens.json.

Usage:
  python3 scripts/sync_jira_releases.py                      # sync all registered projects
  python3 scripts/sync_jira_releases.py --project ATL        # single project key
  python3 scripts/sync_jira_releases.py --dry-run            # preview, no DB write
"""

import os
import sys
import json
import sqlite3
import argparse
import requests
from datetime import datetime

from pm_agent.database.bootstrap import main as init_db
from pm_agent.config import settings
from pm_agent.connectors.shared import get_auth_session
from pm_agent.database import repository


def jira_get(session: requests.Session, url: str) -> dict:
    r = session.get(url, timeout=20)
    r.raise_for_status()
    return r.json()


def jira_fetch_issues(session: requests.Session, base_url: str, jql: str) -> list[dict]:
    """Fetch ALL issues matching jql with status + story_points fields.
    Returns list of dicts: {id, summary, issue_type, status, status_category, story_points, assignee_id, assignee_name}
    """
    issues = []
    page_token = None
    FIELDS = ["summary", "status", "issuetype", "assignee", "customfield_10037"]
    while True:
        body = {"jql": jql, "maxResults": 5000, "fields": FIELDS}
        if page_token:
            body["nextPageToken"] = page_token
        r = session.post(f"{base_url}/rest/api/3/search/jql", json=body, timeout=30)
        if r.status_code != 200:
            break
        data = r.json()
        for issue in data.get("issues", []):
            f = issue["fields"]
            if (f.get("issuetype") or {}).get("name", "") == "Sub Test Execution":
                continue
            cat = f["status"]["statusCategory"]["key"]
            assignee = f.get("assignee") or {}
            issues.append({
                "id":              issue["key"],
                "summary":         (f.get("summary") or "")[:200],
                "issue_type":      f["issuetype"]["name"],
                "status":          f["status"]["name"],
                "status_category": cat,                             # todo / indeterminate / done
                "story_points":    f.get("customfield_10037"),      # None = unestimated
                "assignee_id":     assignee.get("accountId", ""),
                "assignee_name":   assignee.get("displayName", ""),
            })
        if data.get("isLast", True):
            break
        page_token = data.get("nextPageToken")
        if not page_token:
            break
    return issues


def aggregate_issues(issues: list[dict]) -> dict:
    """Compute count-based and SP-based progress aggregates from a list of issues."""
    total = done = inprog = 0
    total_sp = done_sp = inprog_sp = 0.0

    for i in issues:
        cat = i["status_category"]
        sp  = i["story_points"] or 0.0
        total    += 1
        total_sp += sp
        if cat == "done":
            done    += 1
            done_sp += sp
        elif cat == "indeterminate":
            inprog    += 1
            inprog_sp += sp

    return {
        "total":          total,
        "done":           done,
        "inprog":         inprog,
        "todo":           total - done - inprog,
        "progress_pct":   round(done / total * 100, 1) if total > 0 else 0.0,
        "total_sp":       round(total_sp, 1),
        "done_sp":        round(done_sp, 1),
        "inprog_sp":      round(inprog_sp, 1),
        "todo_sp":        round(total_sp - done_sp - inprog_sp, 1),
        "sp_progress_pct": round(done_sp / total_sp * 100, 1) if total_sp > 0 else 0.0,
    }


def get_board_configs(db_path: str, board_filter: str = "", project_filter: str = "") -> list[dict]:
    """Return active jira_board_configs, optionally filtered by board id or project key."""
    conn = sqlite3.connect(db_path)
    cols = "id, name, project_key, base_jql, version_name_pattern, issues_use_base_jql"
    if board_filter:
        rows = conn.execute(
            f"SELECT {cols} FROM jira_board_configs WHERE id=? AND active=1",
            (board_filter,)
        ).fetchall()
    elif project_filter:
        rows = conn.execute(
            f"SELECT {cols} FROM jira_board_configs WHERE project_key=? AND active=1",
            (project_filter.upper(),)
        ).fetchall()
    else:
        rows = conn.execute(
            f"SELECT {cols} FROM jira_board_configs WHERE active=1"
        ).fetchall()
    conn.close()
    return [{"id": r[0], "name": r[1], "project_key": r[2], "base_jql": r[3],
             "version_name_pattern": r[4], "issues_use_base_jql": bool(r[5])} for r in rows]


def get_project_versions(session: requests.Session, base_url: str, project_key: str) -> list[dict]:
    """Fetch all versions for a JIRA project (cached per project_key in this run)."""
    versions = jira_get(session, f"{base_url}/rest/api/3/project/{project_key}/versions")
    if not isinstance(versions, list):
        versions = versions.get("values", [])
    return versions


def sync_board(session: requests.Session, base_url: str, cfg: dict,
               all_versions: list[dict], db_path: str, dry_run: bool) -> int:
    """Sync release versions for ONE board/stream.

    - Filters versions by cfg['version_pattern'] (LIKE match on name)
    - Fetches all issues (with story points) using cfg['base_jql'] AND fixVersion=<id>
    - Writes per-issue data to jira_issues
    - Writes aggregated counts + SP totals to jira_stream_versions
    """
    import fnmatch
    board_id           = cfg["id"]
    board_name         = cfg["name"]
    base_jql           = cfg["base_jql"]
    ver_pattern        = (cfg.get("version_name_pattern") or "").strip()
    project_key        = cfg["project_key"]
    use_base_jql       = cfg.get("issues_use_base_jql", False)

    if ver_pattern:
        # Support pipe-separated multiple patterns e.g. "DOMIS%|BCS%|%BAU%"
        patterns = [p.strip().replace("%", "*").replace("_", "?").lower()
                    for p in ver_pattern.split("|")]
        matching = [v for v in all_versions
                    if any(fnmatch.fnmatch(v["name"].lower(), p) for p in patterns)]
    else:
        matching = all_versions

    # Only keep 2026+ versions (or versions with no release date = future/unscheduled)
    matching = [v for v in matching
                if not v.get("releaseDate") or v.get("releaseDate", "") >= "2026-01-01"]

    unreleased = [v for v in matching if not v.get("released")]
    print(f"  [{board_name}] {len(matching)} versions matched"
          f" ({len(unreleased)} unreleased) | pattern={ver_pattern or 'ALL'} | 2026+ only")

    now   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    count = 0
    conn  = sqlite3.connect(db_path)
    base_jql_fetched = False  # for use_base_jql boards: only fetch issues once
    rows_in = 0
    rows_changed = 0
    errors: list[str] = []
    run_id = None
    if not dry_run:
        run_id = repository.start_sync_run(
            f"jira-release-{board_id}",
            run_type="incremental",
            target_tables=["jira_stream_versions", "jira_issues"],
            triggered_by="cli",
            notes=f"JIRA release sync for board {board_name}",
        )

    try:
        for v in matching:
            ver_id       = str(v.get("id", ""))
            name         = v.get("name", "")
            status       = v.get("status", "")
            released     = 1 if v.get("released") else 0
            release_date = v.get("releaseDate", "")
            start_date   = v.get("startDate", "")

            agg = {"total": 0, "done": 0, "inprog": 0, "todo": 0, "progress_pct": 0.0,
                   "total_sp": 0.0, "done_sp": 0.0, "inprog_sp": 0.0, "todo_sp": 0.0, "sp_progress_pct": 0.0}
            issues = []

            if not v.get("released"):
                try:
                    if use_base_jql:
                        # Some streams track issues by label rather than fixVersion.
                        # Fetch all board issues once, attach to first unreleased version only
                        if not base_jql_fetched:
                            jql = (f"({base_jql})"
                                   f" AND issuetype != \"Sub Test Execution\""
                                   f" AND created >= \"2026-01-01\"")
                            issues = jira_fetch_issues(session, base_url, jql)
                            agg    = aggregate_issues(issues)
                            base_jql_fetched = True
                        # else: leave issues=[] and agg=zeros for subsequent unreleased versions
                    else:
                        jql = (f"({base_jql}) AND fixVersion={ver_id}"
                               f" AND issuetype != \"Sub Test Execution\""
                               f" AND created >= \"2026-01-01\"")
                        issues = jira_fetch_issues(session, base_url, jql)
                        agg    = aggregate_issues(issues)
                except Exception as e:
                    errors.append(f"{name}: {e}")
                    print(f"    ⚠ Error fetching {name}: {e}")

            rows_in += 1 + len(issues)

            if dry_run:
                pct = agg["sp_progress_pct"] if agg["total_sp"] > 0 else agg["progress_pct"]
                bar = "#" * int(pct // 5) + "-" * (20 - int(pct // 5))
                label = "✅" if released else "🔄"
                unest = sum(1 for i in issues if i["story_points"] is None)
                sp_note = f"SP: {agg['done_sp']}/{agg['total_sp']}" if agg["total_sp"] > 0 else f"no SP ({unest} unestimated)"
                print(f"    {label} {name:42s} | {release_date or 'TBD':12s} | "
                      f"#{agg['done']}/{agg['total']} | {sp_note} | [{bar}] {pct:.0f}%")
                count += 1
                continue

            # Upsert version summary
            conn.execute("""
                INSERT INTO jira_stream_versions
                    (id, board_id, project_key, name, release_date, start_date,
                     status, released,
                     total_issues, done_issues, inprogress_issues, todo_issues, progress_pct,
                     total_sp, done_sp, inprogress_sp, todo_sp, sp_progress_pct,
                     raw_data, synced_at)
                VALUES
                    (:id,:board_id,:pkey,:name,:rel_date,:start,:status,:released,
                     :total,:done,:inprog,:todo,:pct,
                     :total_sp,:done_sp,:inprog_sp,:todo_sp,:sp_pct,
                     :raw,:now)
                ON CONFLICT(id, board_id) DO UPDATE SET
                    name=excluded.name, release_date=excluded.release_date,
                    status=excluded.status, released=excluded.released,
                    total_issues=excluded.total_issues, done_issues=excluded.done_issues,
                    inprogress_issues=excluded.inprogress_issues, todo_issues=excluded.todo_issues,
                    progress_pct=excluded.progress_pct,
                    total_sp=excluded.total_sp, done_sp=excluded.done_sp,
                    inprogress_sp=excluded.inprogress_sp, todo_sp=excluded.todo_sp,
                    sp_progress_pct=excluded.sp_progress_pct,
                    raw_data=excluded.raw_data, synced_at=excluded.synced_at
            """, {
                "id": ver_id, "board_id": board_id, "pkey": project_key,
                "name": name, "rel_date": release_date, "start": start_date,
                "status": status, "released": released,
                "total": agg["total"], "done": agg["done"],
                "inprog": agg["inprog"], "todo": agg["todo"], "pct": agg["progress_pct"],
                "total_sp": agg["total_sp"], "done_sp": agg["done_sp"],
                "inprog_sp": agg["inprog_sp"], "todo_sp": agg["todo_sp"],
                "sp_pct": agg["sp_progress_pct"],
                "raw": json.dumps(v), "now": now,
            })
            rows_changed += 1

            # Upsert individual issues
            for issue in issues:
                conn.execute("""
                    INSERT INTO jira_issues
                        (id, board_id, version_id, project_key, summary,
                         issue_type, status, status_category, story_points,
                         assignee_id, assignee_name, synced_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(id, board_id) DO UPDATE SET
                        version_id=excluded.version_id, summary=excluded.summary,
                        issue_type=excluded.issue_type, status=excluded.status,
                        status_category=excluded.status_category,
                        story_points=excluded.story_points,
                        assignee_id=excluded.assignee_id, assignee_name=excluded.assignee_name,
                        synced_at=excluded.synced_at
                """, (issue["id"], board_id, ver_id, project_key, issue["summary"],
                      issue["issue_type"], issue["status"], issue["status_category"],
                      issue["story_points"], issue["assignee_id"], issue["assignee_name"], now))
            rows_changed += len(issues)
            count += 1
        if not dry_run:
            conn.commit()
            repository.finish_sync_run(
                run_id,
                status="partial" if errors else "success",
                rows_in=rows_in,
                rows_changed=rows_changed,
                error_message=" | ".join(errors[:3]),
                notes=(
                    f"JIRA release sync completed for {board_name}."
                    if not errors
                    else (
                        f"JIRA release sync completed for {board_name} with "
                        f"{len(errors)} version fetch warning(s)."
                    )
                ),
            )
        return count
    except Exception as exc:
        if not dry_run:
            conn.rollback()
            repository.fail_sync_run(
                run_id,
                str(exc),
                rows_in=rows_in,
                rows_changed=rows_changed,
                notes=f"JIRA release sync failed for {board_name}.",
            )
        raise
    finally:
        conn.close()


def sync_all(board_filter: str = "", project_filter: str = "", dry_run: bool = False) -> None:
    init_db()

    auth = get_auth_session(
        "jira",
        base_url_hint=settings.jira_base_url,
        email=settings.jira_user_email,
        api_token=settings.jira_api_token,
        verify_ssl=settings.jira_verify_ssl,
        cloud_id_hint=settings.atlassian_cloud_id,
    )
    base_url = auth.base_url
    session = auth.session

    db_path = settings.database_path

    boards = get_board_configs(db_path, board_filter=board_filter, project_filter=project_filter)
    if not boards:
        if board_filter:
            print(f"⚠  未找到 board '{board_filter}'。请先用 `pm release add-board` 注册。")
        else:
            print("⚠  未配置任何 Board。请先用 `pm release add-board` 注册。")
            print("   示例: pm release add-board atlas-board --name 'Atlas Board' --project ATL \\")
            print("           --jql 'project = ATL' --version-pattern '%ATLAS%'")
        sys.exit(0)

    print(f"同步 {len(boards)} 个 stream...")
    if dry_run:
        print("[DRY RUN] 仅预览，不写入 DB\n")

    # Cache versions per project to avoid redundant API calls
    versions_cache: dict[str, list] = {}
    total_synced = 0

    for cfg in boards:
        pkey = cfg["project_key"]
        print(f"\n📁 {cfg['name']} ({pkey}):")
        if pkey not in versions_cache:
            try:
                versions_cache[pkey] = get_project_versions(session, base_url, pkey)
                print(f"  Fetched {len(versions_cache[pkey])} total versions from JIRA")
            except requests.HTTPError as e:
                print(f"  ⚠ HTTP {e.response.status_code} fetching versions — skipping")
                continue

        n = sync_board(session, base_url, cfg, versions_cache[pkey], db_path, dry_run)
        total_synced += n
        if not dry_run:
            print(f"  ✓ {n} 个版本已同步")

    if not dry_run:
        print(f"\n✅ 完成。共同步 {total_synced} 条记录。")
        print("运行 `python3 -m pm_agent.cli.app release list` 查看进度。")


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync JIRA release versions per stream into pm.db")
    parser.add_argument("--board",   default="", help="Only sync this board id (e.g. atlas-board)")
    parser.add_argument("--project", default="", help="Only sync boards under this JIRA project key")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    sync_all(board_filter=args.board, project_filter=args.project, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
