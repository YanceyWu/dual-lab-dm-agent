#!/usr/bin/env python3
"""Rehearse wheel install, isolated DB upgrade, and DB rollback."""

from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import tarfile
from pathlib import Path

from validate_release import REPO_ROOT, build_package, package_version

SAMPLE_DB = REPO_ROOT / "src/sample-data/demo/sample_pm.db"
CORE_TABLES = (
    "employees",
    "projects",
    "assignments",
    "monthly_allocations",
    "decision_log",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def counts(path: Path) -> dict[str, int]:
    with sqlite3.connect(path) as connection:
        return {
            table: connection.execute(
                f"SELECT COUNT(*) FROM {table}"
            ).fetchone()[0]
            for table in CORE_TABLES
        }


def verify_upgraded_database(path: Path, expected_counts: dict[str, int]) -> None:
    with sqlite3.connect(path) as connection:
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        foreign_keys = connection.execute("PRAGMA foreign_key_check").fetchall()
        names = {
            row[0]
            for row in connection.execute(
                """
                SELECT name FROM sqlite_master
                WHERE name IN (
                    'v_member_load',
                    'v_project_team',
                    'staffing_proposals',
                    'dashboard_operations',
                    'source_evidence_runs',
                    'source_evidence_cursors',
                    'source_evidence_manifest_stage',
                    'source_evidence_published_items',
                    'jira_issue_event_stage',
                    'jira_issue_events',
                    'jira_issue_link_stage',
                    'jira_issue_links',
                    'execution_work_items',
                    'execution_source_identities',
                    'execution_work_item_observations',
                    'execution_sprints',
                    'execution_release_commitments',
                    'execution_release_observations',
                    'execution_scope_memberships',
                    'execution_milestones',
                    'execution_milestone_observations',
                    'execution_milestone_release_links',
                    'execution_dependencies',
                    'execution_dependency_observations',
                    'execution_derivation_runs',
                    'execution_derivation_inputs',
                    'execution_facts',
                    'milestone_import_operations',
                    'workforce_planning_import_sessions',
                    'workforce_planning_import_attempts',
                    'workforce_planning_import_runs',
                    'workforce_planning_publications',
                    'workforce_member_period_coverage',
                    'monthly_project_allocation_coverage',
                    'resource_capacity_import_sessions',
                    'resource_capacity_import_attempts',
                    'resource_capacity_import_runs',
                    'resource_capacity_publications',
                    'resource_capacity_manifest_coverage',
                    'resource_capacity_observations',
                    'resource_capacity_derivations',
                    'weekly_brief_snapshot_operations',
                    'staffing_capacity_policy'
                )
                """
            )
        }
        connection.execute("SELECT COUNT(*) FROM v_member_load").fetchone()
        connection.execute("SELECT COUNT(*) FROM v_project_team").fetchone()
        token_columns = {
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(staffing_proposals)"
            )
            if row[1].startswith("confirmation_token")
        }

    if integrity != "ok":
        raise RuntimeError("DATABASE_INTEGRITY_FAILED")
    if foreign_keys:
        raise RuntimeError("DATABASE_FOREIGN_KEY_CHECK_FAILED")
    if names != {
        "v_member_load",
        "v_project_team",
        "staffing_proposals",
        "dashboard_operations",
        "source_evidence_runs",
        "source_evidence_cursors",
        "source_evidence_manifest_stage",
        "source_evidence_published_items",
        "jira_issue_event_stage",
        "jira_issue_events",
        "jira_issue_link_stage",
        "jira_issue_links",
        "execution_work_items",
        "execution_source_identities",
        "execution_work_item_observations",
        "execution_sprints",
        "execution_release_commitments",
        "execution_release_observations",
        "execution_scope_memberships",
        "execution_milestones",
        "execution_milestone_observations",
        "execution_milestone_release_links",
        "execution_dependencies",
        "execution_dependency_observations",
        "execution_derivation_runs",
        "execution_derivation_inputs",
        "execution_facts",
        "milestone_import_operations",
        "workforce_planning_import_sessions",
        "workforce_planning_import_attempts",
        "workforce_planning_import_runs",
        "workforce_planning_publications",
        "workforce_member_period_coverage",
        "monthly_project_allocation_coverage",
        "resource_capacity_import_sessions",
        "resource_capacity_import_attempts",
        "resource_capacity_import_runs",
        "resource_capacity_publications",
        "resource_capacity_manifest_coverage",
        "resource_capacity_observations",
        "resource_capacity_derivations",
        "weekly_brief_snapshot_operations",
        "staffing_capacity_policy",
    }:
        raise RuntimeError("DATABASE_OBJECT_SET_INVALID")
    if token_columns != {"confirmation_token_hash"}:
        raise RuntimeError("CONFIRMATION_TOKEN_SCHEMA_INVALID")
    if counts(path) != expected_counts:
        raise RuntimeError("DATABASE_CORE_COUNTS_CHANGED")


def rehearse() -> None:
    with tempfile.TemporaryDirectory(prefix="dm-release-rehearsal-") as temp_dir:
        workspace = Path(temp_dir)
        prior_runtime = workspace / "prior-runtime"
        archive = subprocess.run(
            ["git", "archive", "8cb5f69dadb9b6653d82d0ad6d3b7c3585ed24eb"],
            check=True,
            cwd=REPO_ROOT,
            capture_output=True,
        ).stdout
        with tarfile.open(fileobj=io.BytesIO(archive)) as contents:
            contents.extractall(prior_runtime, filter="data")
        artifact_dir = workspace / "dist"
        artifact_dir.mkdir()
        wheel, _sdist = build_package(artifact_dir)

        install_dir = workspace / "installed"
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--no-deps",
                "--target",
                str(install_dir),
                str(wheel),
            ],
            check=True,
            cwd=workspace,
        )
        installed_env = os.environ.copy()
        installed_env["PYTHONPATH"] = str(install_dir)
        installed_version = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "from importlib.metadata import version;"
                    "print(version('ai-pm-agent'))"
                ),
            ],
            check=True,
            cwd=workspace,
            env=installed_env,
            capture_output=True,
            text=True,
        ).stdout.strip()
        if installed_version != package_version():
            raise RuntimeError("INSTALLED_VERSION_MISMATCH")

        backup_db = workspace / "before-upgrade.db"
        clean_db = workspace / "clean-bootstrap.db"
        upgrade_db = workspace / "upgrade-copy.db"
        rollback_db = workspace / "rollback-copy.db"
        shutil.copy2(SAMPLE_DB, backup_db)
        shutil.copy2(backup_db, upgrade_db)
        original_hash = sha256(backup_db)
        before_counts = counts(backup_db)
        with sqlite3.connect(backup_db) as connection:
            before_events = connection.execute(
                "SELECT COUNT(*) FROM jira_issue_events"
            ).fetchone()[0]

        upgrade_env = installed_env.copy()
        upgrade_env["DATABASE_PATH"] = str(upgrade_db)
        clean_env = installed_env.copy()
        clean_env["DATABASE_PATH"] = str(clean_db)
        subprocess.run(
            [
                sys.executable,
                "-c",
                "from pm_agent.database.bootstrap import main; main()",
            ],
            check=True,
            cwd=workspace,
            env=clean_env,
        )
        verify_upgraded_database(
            clean_db,
            {table: 0 for table in CORE_TABLES},
        )
        installed_weekly_capture = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "import json,threading;from pm_agent.weekly_brief.snapshots import WeeklyBriefSnapshotService;"
                    "c={'execution_id':'weekly-v2-execution-synthetic-001','contract_version':'weekly-brief-v2','comparison_rule_version':'weekly-brief-comparison-v2','generated_at':'2026-08-01T00:00:00Z','week_key':'2026-W31','scope':{'project_ids':['project-synthetic-001']},'input':{'as_of':'2026-08-01T00:00:00Z'},'baseline_snapshot_id':'','baseline_fingerprint':'','statement_manifest':[{'identity_key':'attention:synthetic-001','producer':'attention','scope_fingerprint':'6aea5364bcf8ff86511c5fe530ff5228ddc8da971564ab1732e34eaf9ba554eb','semantic_fingerprint':'a'*64,'evidence_state_fingerprint':'e'*64,'active_material':True,'transition_state':'active','coverage_complete':True,'usable_evidence':True,'limited_active_proven':True}],'evidence_summary':{'producer':'synthetic-public-contract'},'section_coverage':{'attention':'complete'},'limitation_codes':[]};"
                    "s=WeeklyBriefSnapshotService(query_lookup=lambda x:c,recompose=lambda x:c);p=s.preview(candidate=c,actor_id='actor-synthetic-001',idempotency_key='capture-synthetic-001');r=s.confirm(operation_id=p['operation_id'],confirmation_token=p['confirmation_token']);q=s.confirm(operation_id=p['operation_id'],confirmation_token=p['confirmation_token']);z=WeeklyBriefSnapshotService(query_lookup=lambda x:c,recompose=lambda x:{**c,'input':{'as_of':'2026-08-02T00:00:00Z'}});sp=z.preview(candidate=c,actor_id='actor-synthetic-001',idempotency_key='stale-synthetic-001');sr=z.confirm(operation_id=sp['operation_id'],confirmation_token=sp['confirmation_token']);cp=s.preview(candidate=c,actor_id='actor-synthetic-001',idempotency_key='concurrent-synthetic-001');out=[];ts=[threading.Thread(target=lambda:out.append(s.confirm(operation_id=cp['operation_id'],confirmation_token=cp['confirmation_token'])['status'])) for _ in range(2)];[t.start() for t in ts];[t.join() for t in ts];print(json.dumps({'preview':p['status'],'confirm':r['status'],'replay':q['status'],'stale':sr['status'],'concurrent':sorted(out)}))"
                ),
            ],
            check=True,
            cwd=workspace,
            env=clean_env,
            capture_output=True,
            text=True,
        )
        weekly_capture_result = json.loads(installed_weekly_capture.stdout)
        # Claim races have two valid externally observable outcomes: the losing
        # caller can observe either the finalized idempotent confirmation or a
        # failed claim.  In both cases exactly one write is confirmed.
        if not (
            {key: weekly_capture_result.get(key) for key in ("preview", "confirm", "replay", "stale")}
            == {"preview": "previewed", "confirm": "confirmed", "replay": "already_confirmed", "stale": "stale"}
            and weekly_capture_result.get("concurrent") in (["confirmed", "failed"], ["already_confirmed", "confirmed"])
        ):
            raise RuntimeError(f"INSTALLED_WEEKLY_BRIEF_CAPTURE_INVALID:{installed_weekly_capture.stdout}")
        prior_env = clean_env.copy()
        prior_env["PYTHONPATH"] = str(prior_runtime / "src")
        installed_weekly_rollback = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "import json,sqlite3,os;"
                    "from pm_agent.use_cases.weekly_report import WeeklyReportService;"
                    "p=os.environ['DATABASE_PATH'];con=sqlite3.connect(p);"
                    "before=con.execute(\"SELECT COUNT(*) FROM weekly_brief_snapshot_operations WHERE status='confirmed'\").fetchone()[0];"
                    "report=WeeklyReportService().weekly();"
                    "after=con.execute(\"SELECT COUNT(*) FROM weekly_brief_snapshot_operations WHERE status='confirmed'\").fetchone()[0];con.close();"
                    "print(json.dumps({'before':before,'after':after,'week':report.data['week']}))"
                ),
            ],
            check=True,
            cwd=workspace,
            env=prior_env,
            capture_output=True,
            text=True,
        )
        rollback_result = json.loads(installed_weekly_rollback.stdout)
        if rollback_result.get("before") != 2 or rollback_result.get("after") != 2 or not rollback_result.get("week"):
            raise RuntimeError(f"INSTALLED_WEEKLY_BRIEF_ADDITIVE_ROLLBACK_INVALID:{installed_weekly_rollback.stdout}")
        installed_import = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "import json,sys;"
                    "from pm_agent.workforce_planning_import.service import "
                    "preview_import,confirm_import;"
                    "p=json.load(open(sys.argv[1],encoding='utf-8'));"
                    "v=preview_import(p);r=confirm_import(v['session_id']);"
                    "i=preview_import(p);"
                    "print(json.dumps({'result':r,'replay':i},sort_keys=True))"
                ),
                str(
                    REPO_ROOT
                    / "src/sample-data/json/workforce_planning_import.sample.json"
                ),
            ],
            check=True,
            cwd=workspace,
            env=clean_env,
            capture_output=True,
            text=True,
        )
        import_result = json.loads(installed_import.stdout)
        if import_result["result"]["status"] != "completed":
            raise RuntimeError("INSTALLED_WORKFORCE_PLANNING_IMPORT_FAILED")
        if import_result["replay"]["status"] != "already_completed":
            raise RuntimeError("INSTALLED_WORKFORCE_PLANNING_REPLAY_INVALID")
        if import_result["result"]["report"]["software_rollback"]["state"] != "passed":
            raise RuntimeError("INSTALLED_WORKFORCE_PLANNING_ROLLBACK_INVALID")
        verify_upgraded_database(
            clean_db,
            {
                "employees": 2,
                "projects": 1,
                "assignments": 0,
                "monthly_allocations": 2,
                "decision_log": 0,
            },
        )
        with sqlite3.connect(clean_db) as connection:
            audit_counts = {
                table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in (
                    "workforce_planning_import_sessions",
                    "workforce_planning_import_attempts",
                    "workforce_planning_publications",
                    "workforce_member_period_coverage",
                    "monthly_project_allocation_coverage",
                )
            }
        if audit_counts != {
            "workforce_planning_import_sessions": 1,
            "workforce_planning_import_attempts": 1,
            "workforce_planning_publications": 1,
            "workforce_member_period_coverage": 2,
            "monthly_project_allocation_coverage": 2,
        }:
            raise RuntimeError("INSTALLED_WORKFORCE_PLANNING_AUDIT_INVALID")
        installed_capacity = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "import json,sys;"
                    "from pm_agent.resource_intelligence.service import "
                    "preview_import,confirm_import;"
                    "from pm_agent.resource_intelligence.read_model import "
                    "get_effective_capacity;"
                    "p=json.load(open(sys.argv[1],encoding='utf-8'));"
                    "v=preview_import(p);r=confirm_import(v['session_id']);"
                    "i=preview_import(p);"
                    "c=get_effective_capacity('member-synthetic-001',2026,8,"
                    "'plan-synthetic-baseline-001');"
                    "print(json.dumps({'result':r,'replay':i,'capacity':c},sort_keys=True))"
                ),
                str(REPO_ROOT / "src/sample-data/json/resource_capacity_import.sample.json"),
            ],
            check=True,
            cwd=workspace,
            env=clean_env,
            capture_output=True,
            text=True,
        )
        capacity_result = json.loads(installed_capacity.stdout)
        if capacity_result["result"]["status"] != "completed":
            raise RuntimeError("INSTALLED_RESOURCE_CAPACITY_IMPORT_FAILED")
        if capacity_result["replay"]["status"] != "already_completed":
            raise RuntimeError("INSTALLED_RESOURCE_CAPACITY_REPLAY_INVALID")
        capacity = capacity_result["capacity"]
        if (
            capacity["state"] != "known"
            or capacity["effective_capacity"] != 0.7
            or capacity["available_capacity"] != 0.2
        ):
            raise RuntimeError("INSTALLED_RESOURCE_CAPACITY_DERIVATION_INVALID")
        if capacity_result["result"]["report"]["software_rollback"]["state"] != "passed":
            raise RuntimeError("INSTALLED_RESOURCE_CAPACITY_ROLLBACK_INVALID")
        with sqlite3.connect(clean_db) as connection:
            capacity_audit = {
                table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in (
                    "resource_capacity_import_sessions",
                    "resource_capacity_import_attempts",
                    "resource_capacity_publications",
                    "resource_capacity_manifest_coverage",
                    "resource_capacity_observations",
                    "resource_capacity_derivations",
                )
            }
        if capacity_audit != {
            "resource_capacity_import_sessions": 1,
            "resource_capacity_import_attempts": 1,
            "resource_capacity_publications": 1,
            "resource_capacity_manifest_coverage": 6,
            "resource_capacity_observations": 6,
            "resource_capacity_derivations": 2,
        }:
            raise RuntimeError("INSTALLED_RESOURCE_CAPACITY_AUDIT_INVALID")
        installed_staffing_capacity = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "import json;"
                    "from pm_agent.database.staffing_capacity import "
                    "capacity_required,enable_capacity_requirement;"
                    "from pm_agent.use_cases.staffing import StaffingDemand,assess_feasibility;"
                    "before=capacity_required();enabled=enable_capacity_requirement();"
                    "result=assess_feasibility(StaffingDemand("
                    "project_id='project-synthetic-atlas',start_period='2026-08',"
                    "end_period='2026-08',effort=0.2,minimum_allocation=0.1,"
                    "maximum_people=1,plan_version_id='plan-synthetic-baseline-001'));"
                    "print(json.dumps({'before':before,'enabled':enabled,'result':result},"
                    "sort_keys=True))"
                ),
            ],
            check=True,
            cwd=workspace,
            env=clean_env,
            capture_output=True,
            text=True,
        )
        staffing_capacity_result = json.loads(installed_staffing_capacity.stdout)
        if staffing_capacity_result["before"] is not False:
            raise RuntimeError("INSTALLED_STAFFING_CAPACITY_MARKER_DEFAULT_INVALID")
        if staffing_capacity_result["enabled"]["capacity_required"] is not True:
            raise RuntimeError("INSTALLED_STAFFING_CAPACITY_MARKER_ENABLE_INVALID")
        staffing_result = staffing_capacity_result["result"]
        if (
            staffing_result["capacity_policy"]["required"] is not True
            or staffing_result["rule_version"] != "staffing-effective-capacity-v1"
            or staffing_result["selections"][0]["member_id"]
            != "member-synthetic-002"
        ):
            raise RuntimeError("INSTALLED_STAFFING_CAPACITY_CONSUMPTION_INVALID")
        installed_project_health_capacity = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "import json;"
                    "from pm_agent.project_health.evaluation import evaluate;"
                    "from pm_agent.project_health.read_model import latest_assessments;"
                    "r=evaluate('project-synthetic-atlas',capacity_year=2026,"
                    "capacity_month=8,capacity_plan_version_id="
                    "'plan-synthetic-baseline-001');"
                    "a=latest_assessments(project_id='project-synthetic-atlas')[0];"
                    "f=next(x for x in a['factors'] if x['factor_id']=="
                    "'resource_capacity_coverage');"
                    "print(json.dumps({'result':r,'factor':f},sort_keys=True))"
                ),
            ],
            check=True,
            cwd=workspace,
            env=clean_env,
            capture_output=True,
            text=True,
        )
        project_health_capacity = json.loads(installed_project_health_capacity.stdout)
        health_result = project_health_capacity["result"]
        health_factor = project_health_capacity["factor"]
        capacity_evidence = health_factor["detail"]["evidence_refs"][0]["evidence"]
        if (
            health_result["dimensions"]["resource"] != "green"
            or health_factor["state"] != "green"
            or capacity_evidence["capacity_derivations"][0]["derivation_rule_version"]
            != "effective-capacity-v1"
        ):
            raise RuntimeError("INSTALLED_PROJECT_HEALTH_CAPACITY_INVALID")
        with sqlite3.connect(clean_db) as connection:
            if connection.execute("SELECT COUNT(*) FROM attention_signals").fetchone()[0]:
                raise RuntimeError("INSTALLED_PROJECT_HEALTH_CAPACITY_ATTENTION_CREATED")
        subprocess.run(
            [
                sys.executable,
                "-c",
                "from pm_agent.database.bootstrap import main; main()",
            ],
            check=True,
            cwd=workspace,
            env=upgrade_env,
        )
        subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "from pm_agent.database import source_evidence as e;"
                    "r=e.start_run('jira-evidence-synthetic','board-synthetic',"
                    "'jira_issue_history',overlap_seconds=300,run_id='installed-run');"
                    "e.stage_issue_events(r,[e.IssueEvent(issue_ref='SYN-1',"
                    "source_event_ref='evt-1',event_type='field_changed',"
                    "field_key='status',from_value='todo',to_value='done',"
                    "source_updated_at='2026-07-29T01:00:00+00:00',"
                    "observed_at='2026-07-29T01:05:00+00:00')]);"
                    "e.finish_staging(r,coverage_status='complete',pages_received=1,"
                    "pages_expected=1,proposed_cursor_time="
                    "'2026-07-29T01:00:00+00:00',proposed_cursor_ref='SYN-1');"
                    "e.publish_run(r)"
                    ";p=e.start_run('jira-evidence-synthetic','board-synthetic',"
                    "'jira_issue_history',overlap_seconds=300,run_id='installed-partial');"
                    "e.stage_issue_events(p,[e.IssueEvent(issue_ref='SYN-2',"
                    "source_event_ref='evt-2',event_type='field_changed',"
                    "field_key='status',from_value='todo',to_value='done',"
                    "source_updated_at='2026-07-29T02:00:00+00:00',"
                    "observed_at='2026-07-29T02:05:00+00:00')]);"
                    "e.finish_staging(p,coverage_status='complete',pages_received=1,"
                    "pages_expected=2,proposed_cursor_time="
                    "'2026-07-29T02:00:00+00:00',proposed_cursor_ref='SYN-2');"
                    "e.reject_run(p)"
                ),
            ],
            check=True,
            cwd=workspace,
            env=upgrade_env,
        )
        verify_upgraded_database(upgrade_db, before_counts)
        with sqlite3.connect(upgrade_db) as connection:
            if (
                connection.execute("SELECT COUNT(*) FROM jira_issue_events").fetchone()[0]
                != before_events + 1
            ):
                raise RuntimeError("INSTALLED_PHASE3_EVIDENCE_BEHAVIOR_INVALID")
            if connection.execute(
                """
                SELECT published_run_id FROM source_evidence_cursors
                WHERE source_id = 'jira-evidence-synthetic'
                  AND board_id = 'board-synthetic'
                  AND dataset = 'jira_issue_history'
                """
            ).fetchone()[0] != "installed-run":
                raise RuntimeError("INSTALLED_PHASE3_CURSOR_BEHAVIOR_INVALID")
            partial_state = connection.execute(
                """
                SELECT coverage_status, publication_status
                FROM source_evidence_runs
                WHERE run_id = 'installed-partial'
                """
            ).fetchone()
            if partial_state != ("partial", "rejected"):
                raise RuntimeError("INSTALLED_PHASE3_PARTIAL_STATE_INVALID")
            if connection.execute(
                """
                SELECT COUNT(*) FROM jira_issue_event_stage
                WHERE run_id = 'installed-partial'
                """
            ).fetchone()[0] != 1:
                raise RuntimeError("INSTALLED_PHASE3_PARTIAL_STAGE_MISSING")
            if connection.execute(
                """
                SELECT COUNT(*) FROM jira_issue_events
                WHERE issue_ref = 'SYN-2'
                """
            ).fetchone()[0] != 0:
                raise RuntimeError("INSTALLED_PHASE3_PARTIAL_RUN_PUBLISHED")

        shutil.copy2(backup_db, rollback_db)
        if sha256(rollback_db) != original_hash:
            raise RuntimeError("DATABASE_ROLLBACK_HASH_MISMATCH")
        if sha256(SAMPLE_DB) != original_hash:
            raise RuntimeError("SOURCE_SAMPLE_DATABASE_CHANGED")

    print(
        "Release rehearsal PASSED: wheel install, isolated DB upgrade, "
        f"and rollback for ai-pm-agent {package_version()}"
    )


if __name__ == "__main__":
    try:
        rehearse()
    except (RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"Release rehearsal FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
