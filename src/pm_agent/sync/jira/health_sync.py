
import argparse, json, sqlite3, sys
from datetime import datetime, timedelta
from pathlib import Path
import requests

from pm_agent.database.bootstrap import main as init_db
from pm_agent.config import get_database_path, settings
from pm_agent.connectors.shared import get_auth_session
from pm_agent.database import repository

def jira_search(session, base_url, jql, fields):
    issues, next_token = [], None
    while True:
        body = {"jql": jql, "maxResults": 100, "fields": fields}
        if next_token:
            body["nextPageToken"] = next_token
        r = session.post(f"{base_url}/rest/api/3/search/jql", json=body)
        if not r.ok:
            print(f"  search error ({r.status_code}): {r.text[:200]}")
            break
        data = r.json()
        issues.extend(data.get("issues", []))
        if data.get("isLast", True):
            break
        next_token = data.get("nextPageToken")
        if not next_token:
            break
    return issues

def get_active_sprints(session, base_url, board_id):
    r = session.get(f"{base_url}/rest/agile/1.0/board/{board_id}/sprint", params={"state": "active"})
    r.raise_for_status()
    return r.json().get("values", [])

def score_burndown(done_sp, total_sp, release_date, snapshot_date):
    if total_sp <= 0:
        return 50.0, {"reason": "no_sp_data"}
    actual_pct = done_sp / total_sp
    if release_date:
        try:
            rd = datetime.strptime(release_date, "%Y-%m-%d")
            sd = datetime.strptime(snapshot_date, "%Y-%m-%d")
            start = rd - timedelta(days=90)
            total_days = (rd - start).days
            elapsed = (sd - start).days
            ideal_pct = max(0.0, min(1.0, elapsed / total_days)) if total_days > 0 else 0.5
        except Exception:
            ideal_pct = 0.5
    else:
        ideal_pct = 0.5
    delta = actual_pct - ideal_pct
    score = min(100, 70 + delta * 100) if delta >= 0 else max(0, 70 + delta * 150)
    return round(score, 1), {"actual_pct": round(actual_pct*100,1), "ideal_pct": round(ideal_pct*100,1),
                              "delta_pct": round(delta*100,1), "done_sp": done_sp, "total_sp": total_sp}

def score_sprint(sp_done, sp_committed):
    if sp_committed <= 0:
        return 50.0, {"reason": "no_committed_sp"}
    pct = sp_done / sp_committed
    score = min(100.0, pct * 100)
    if pct >= 0.9: score = min(100, score + 5)
    elif pct < 0.6: score = max(0, score - 10)
    return round(score, 1), {"committed_sp": sp_committed, "done_sp": sp_done, "completion_pct": round(pct*100,1)}

def score_defects(p1p2, p3p4, done_stories):
    if done_stories <= 0:
        score = max(0.0, 100.0 - (p1p2*3 + p3p4)*10)
        return round(score, 1), {"p1p2": p1p2, "p3p4": p3p4, "baseline": "absolute"}
    ratio = (p1p2*3 + p3p4) / done_stories
    score = max(0.0, 100.0 - ratio*70)
    return round(score, 1), {"p1p2": p1p2, "p3p4": p3p4, "done_stories": done_stories, "weighted_ratio": round(ratio,3)}

def score_scope(added_sp, removed_sp, total_sp):
    if total_sp <= 0:
        return 70.0, {"reason": "no_sp_baseline"}
    net_pct = abs(added_sp - removed_sp) / total_sp
    score = max(0.0, 100.0 - net_pct*200)
    return round(score, 1), {"added_sp": added_sp, "removed_sp": removed_sp, "net_change_pct": round(net_pct*100,1)}

def compute_overall(v, s, d, sc):
    score = round(v*0.35 + s*0.25 + d*0.25 + sc*0.15, 1)
    grade = "GREEN" if score >= 75 else ("YELLOW" if score >= 50 else "RED")
    return score, grade

def sync_board(conn, session, base_url, board, snapshot_date, dry_run=False):
    board_id = board["id"]
    board_name = board["name"]
    jira_board_id = board.get("board_id")
    base_jql = board["base_jql"]
    print("\n" + "="*60)
    print(f"Board: {board_name}  (jira_board={jira_board_id or 'N/A'})")
    run_id = None
    rows_in = 0
    rows_changed = 0
    if not dry_run:
        run_id = repository.start_sync_run(
            f"jira-health-{board_id}",
            run_type="incremental",
            target_tables=["jira_sprints", "jira_health_snapshots"],
            triggered_by="cli",
            notes=f"JIRA health sync for board {board_name}",
        )

    try:
        # Get version_name_pattern for sub-system grouping
        ver_pattern = board.get("version_name_pattern", "")
        # For boards with pipe-separated patterns (e.g. BAU with DOMIS|BCS|...), detect sub-systems
        sub_patterns = [p.strip() for p in ver_pattern.split("|")] if "|" in ver_pattern else []

        # Get nearest future releases with SP data
        rows_ver = conn.execute(
            "SELECT id, name, release_date, total_sp, done_sp, sp_progress_pct "
            "FROM jira_stream_versions WHERE board_id=? AND released=0 AND total_sp > 0 "
            "AND (release_date IS NULL OR release_date >= date('now')) "
            "ORDER BY release_date ASC NULLS LAST LIMIT 10", (board_id,)).fetchall()
        if not rows_ver:
            rows_ver = conn.execute(
                "SELECT id, name, release_date, total_sp, done_sp, sp_progress_pct "
                "FROM jira_stream_versions WHERE board_id=? AND released=0 "
                "ORDER BY release_date ASC NULLS LAST LIMIT 6", (board_id,)).fetchall()

        if not rows_ver:
            print("  No unreleased version -- skip")
            if not dry_run:
                repository.finish_sync_run(
                    run_id,
                    rows_in=0,
                    rows_changed=0,
                    notes=f"No unreleased version found for {board_name}; sync skipped.",
                )
            return

        # If multiple sub-systems, pick one nearest per sub-system prefix; otherwise just first
        import fnmatch as _fnmatch
        if sub_patterns:
            seen_prefixes = {}
            for r in rows_ver:
                for pat in sub_patterns:
                    glob = pat.replace("%", "*").replace("_", "?").lower()
                    prefix = pat.rstrip("%").rstrip("*").upper()
                    if _fnmatch.fnmatch(r[1].lower(), glob) and prefix not in seen_prefixes:
                        seen_prefixes[prefix] = r
                        break
            target_versions = list(seen_prefixes.values()) if seen_prefixes else [rows_ver[0]]
        else:
            target_versions = [rows_ver[0]]

        row = target_versions[0]  # primary version for sprint/defect analysis
        if not row:
            print("  No unreleased version -- skip")
            if not dry_run:
                repository.finish_sync_run(
                    run_id,
                    rows_in=0,
                    rows_changed=0,
                    notes=f"No target version resolved for {board_name}; sync skipped.",
                )
            return
        ver_id, ver_name, release_date, total_sp, done_sp, sp_pct = row
        remaining_sp = (total_sp or 0) - (done_sp or 0)
        if len(target_versions) > 1:
            print(f"  Sub-system releases ({len(target_versions)} tracked):")
            for tv in target_versions:
                print(f"    {tv[1]:<30} {tv[4] or 0:.0f}/{tv[3] or 0:.0f} SP  ({tv[5] or 0:.1f}%)  [{tv[2] or 'no date'}]")
            print(f"  Primary (for sprint/defect): {ver_name}")
        else:
            print(f"  Release : {ver_name}  ({release_date or 'no date'})")
            print(f"  Progress: {done_sp}/{total_sp} SP  ({sp_pct:.1f}%)")

        est = conn.execute(
            "SELECT COUNT(*), SUM(CASE WHEN story_points IS NULL OR story_points=0 THEN 1 ELSE 0 END) "
            "FROM jira_issues WHERE board_id=? AND version_id=? AND status_category != 'done'",
            (board_id, ver_id)).fetchone()
        total_open = est[0] or 0
        unest = est[1] or 0
        unest_pct = unest / total_open * 100 if total_open > 0 else 0
        print(f"  Estimation: {total_open-unest}/{total_open} ({100-unest_pct:.0f}% coverage)")

        sprint_info = {}
        sp_done_sprint = sp_committed = 0.0
        sprint_completion_pct = 0.0
        p1p2 = p3p4 = done_stories = 0
        scope_added = scope_removed = 0.0

        if jira_board_id:
            active_sprints = get_active_sprints(session, base_url, jira_board_id)
            if active_sprints:
                from datetime import date as _date
                today_str = str(_date.today())
                # Filter to sprints where today falls within the sprint window
                current_sprints = [s for s in active_sprints
                                   if (s.get("startDate","")[:10] <= today_str <= s.get("endDate","")[:10])]
                if not current_sprints:
                    current_sprints = active_sprints[-3:]  # fallback: latest 3
                active_sprints = current_sprints
                sprint_ids_str = ",".join(str(s["id"]) for s in active_sprints)
                sprint_name_display = active_sprints[0].get("name","").split("]")[-1].strip() if active_sprints else ""
                print(f"  Current sprint ({len(active_sprints)} tracks): {sprint_name_display}")
                if not dry_run:
                    for sp in active_sprints:
                        conn.execute("INSERT OR REPLACE INTO jira_sprints "
                            "(id, board_id, name, state, start_date, end_date, synced_at) "
                            "VALUES (?,?,?,?,?,?,datetime('now'))",
                            (str(sp["id"]), board_id, sp.get("name"), sp.get("state"),
                             (sp.get("startDate") or "")[:10], (sp.get("endDate") or "")[:10]))
                    rows_changed += len(active_sprints)
                jql = (f"({base_jql}) AND sprint in ({sprint_ids_str})"
                       f" AND issuetype != \"Sub Test Execution\""
                       f" AND created >= \"2026-01-01\"")
                fields = ["summary", "status", "issuetype", "priority", "customfield_10037", "resolutiondate"]
                sprint_issues = jira_search(session, base_url, jql, fields)
                rows_in += len(target_versions) + len(sprint_issues)
                print(f"  Sprint issues: {len(sprint_issues)}")
                for issue in sprint_issues:
                    f = issue["fields"]
                    itype = (f.get("issuetype") or {}).get("name", "").lower()
                    if itype == "sub test execution":
                        continue
                    sp_val = float(f.get("customfield_10037") or 0)
                    status_key = (f.get("status") or {}).get("statusCategory", {}).get("key", "")
                    pname = (f.get("priority") or {}).get("name", "").upper()
                    sp_committed += sp_val
                    if status_key == "done":
                        sp_done_sprint += sp_val
                        if itype not in ("bug", "defect", "sub-task", "subtask"):
                            done_stories += 1
                    if itype in ("bug", "defect"):
                        if any(p in pname for p in ("HIGH", "P1", "P2", "BLOCKER", "CRITICAL", "HIGHEST")):
                            p1p2 += 1
                        else:
                            p3p4 += 1
                if sp_committed > 0:
                    sprint_completion_pct = sp_done_sprint / sp_committed * 100
                sprint_info = {"sprint_id": str(active_sprints[0]["id"]),
                               "sprint_name": active_sprints[0].get("name"),
                               "tracks": len(active_sprints), "total_issues": len(sprint_issues),
                               "sp_committed": sp_committed, "sp_done": sp_done_sprint}
            else:
                rows_in += len(target_versions)
                print("  No active sprint found")
        else:
            rows_in += len(target_versions)

        last = conn.execute(
            "SELECT total_sp FROM jira_health_snapshots WHERE board_id=? AND version_id=? "
            "ORDER BY snapshot_date DESC LIMIT 1", (board_id, ver_id)).fetchone()
        if last and last[0]:
            delta = (total_sp or 0) - last[0]
            if delta > 0: scope_added = delta
            elif delta < 0: scope_removed = abs(delta)

        v_score, v_det = score_burndown(done_sp or 0, total_sp or 0, release_date, snapshot_date)
        s_score, s_det = score_sprint(sp_done_sprint, sp_committed)
        d_score, d_det = score_defects(p1p2, p3p4, done_stories)
        sc_score, sc_det = score_scope(scope_added, scope_removed, total_sp or 0)
        overall, grade = compute_overall(v_score, s_score, d_score, sc_score)

        print("\n  === RAW DATA ===")
        print(f"  Burndown : {json.dumps(v_det)}")
        print(f"  Sprint   : {json.dumps(s_det)}")
        print(f"  Defects  : {json.dumps(d_det)}")
        print(f"  Scope    : {json.dumps(sc_det)}")
        print("\n  === SCORES ===")
        print(f"  Burndown  (35%) : {v_score:6.1f}")
        print(f"  Sprint    (25%) : {s_score:6.1f}")
        print(f"  Defects   (25%) : {d_score:6.1f}")
        print(f"  Scope     (15%) : {sc_score:6.1f}")
        print(f"  OVERALL         : {overall:6.1f}  [{grade}]")

        risks = []
        if unest_pct > 30:
            risks.append({"type": "estimation", "msg": f"{unest_pct:.0f}% issues unestimated"})
        if p1p2 >= 3:
            risks.append({"type": "quality", "msg": f"{p1p2} P1/P2 bugs in active sprint"})
        if v_det.get("delta_pct", 0) < -15:
            risks.append({"type": "schedule", "msg": f"Behind ideal burndown by {abs(v_det['delta_pct']):.0f}%"})
        if sprint_completion_pct < 50 and sp_committed > 0:
            risks.append({"type": "sprint", "msg": f"Sprint only {sprint_completion_pct:.0f}% complete"})
        if risks:
            print("\n  === RISKS ===")
            for r in risks:
                print(f"  WARN [{r['type']}] {r['msg']}")

        if not dry_run:
            conn.execute(
                "INSERT INTO jira_health_snapshots "
                "(board_id, version_id, snapshot_date, sprint_id, sprint_name, "
                "velocity_score, sprint_score, defect_score, scope_score, overall_score, overall_grade, "
                "remaining_sp, done_sp, total_sp, sp_progress_pct, sprint_completion_pct, "
                "new_bugs_p1p2, new_bugs_p3p4, total_defects, done_stories, "
                "scope_added_sp, scope_removed_sp, unestimated_count, unestimated_pct, "
                "raw_sprint_issues, raw_defects, summary_text, risks_json) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (board_id, ver_id, snapshot_date,
                 sprint_info.get("sprint_id"), sprint_info.get("sprint_name"),
                 v_score, s_score, d_score, sc_score, overall, grade,
                 remaining_sp, done_sp or 0, total_sp or 0, sp_pct or 0, sprint_completion_pct,
                 p1p2, p3p4, p1p2+p3p4, done_stories, scope_added, scope_removed,
                 unest, round(unest_pct,1), json.dumps(sprint_info), json.dumps(d_det),
                 f"[{grade}] {board_name}: {ver_name} | Overall={overall}", json.dumps(risks)))
            conn.commit()
            rows_changed += 1
            repository.finish_sync_run(
                run_id,
                rows_in=rows_in,
                rows_changed=rows_changed,
                notes=f"JIRA health sync completed for {board_name}.",
            )
            print("\n  Snapshot saved")
        else:
            print("\n  [DRY RUN] Not saved")
    except Exception as exc:
        if not dry_run:
            repository.fail_sync_run(
                run_id,
                str(exc),
                rows_in=rows_in,
                rows_changed=rows_changed,
                notes=f"JIRA health sync failed for {board_name}.",
            )
        raise


def run_sync(board: str | None = None, dry_run: bool = False) -> None:
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
    conn = sqlite3.connect(get_database_path())
    snapshot_date = datetime.now().strftime("%Y-%m-%d")
    print(f"Health sync -- {snapshot_date}" + (" [DRY RUN]" if dry_run else ""))
    q = "SELECT id, name, board_id, base_jql, version_name_pattern FROM jira_board_configs WHERE active=1"
    params = []
    if board:
        q += " AND id=?"
        params.append(board)
    boards = conn.execute(q, params).fetchall()
    if not boards:
        print("No active boards found")
        return
    for b in boards:
        try:
            sync_board(conn, session, base_url,
                       {"id": b[0], "name": b[1], "board_id": b[2], "base_jql": b[3],
                        "version_name_pattern": b[4] if len(b) > 4 else ""},
                       snapshot_date, dry_run)
        except Exception as e:
            print(f"  ERROR on {b[0]}: {e}")
            import traceback; traceback.print_exc()
    conn.close()
    print("\nHealth sync complete")


def main():
    parser = argparse.ArgumentParser(description="Sync JIRA health scores")
    parser.add_argument("--board", help="Board ID, for example atlas-board")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run_sync(board=args.board, dry_run=args.dry_run)

if __name__ == "__main__":
    main()
