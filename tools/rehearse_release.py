#!/usr/bin/env python3
"""Rehearse wheel install, isolated DB upgrade, and DB rollback."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
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
                    'monthly_project_allocation_coverage'
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
    }:
        raise RuntimeError("DATABASE_OBJECT_SET_INVALID")
    if token_columns != {"confirmation_token_hash"}:
        raise RuntimeError("CONFIRMATION_TOKEN_SCHEMA_INVALID")
    if counts(path) != expected_counts:
        raise RuntimeError("DATABASE_CORE_COUNTS_CHANGED")


def rehearse() -> None:
    with tempfile.TemporaryDirectory(prefix="dm-release-rehearsal-") as temp_dir:
        workspace = Path(temp_dir)
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
            if connection.execute("SELECT COUNT(*) FROM jira_issue_events").fetchone()[0] != 1:
                raise RuntimeError("INSTALLED_PHASE3_EVIDENCE_BEHAVIOR_INVALID")
            if connection.execute(
                "SELECT published_run_id FROM source_evidence_cursors"
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
        print(f"Release rehearsal FAILED: {type(exc).__name__}", file=sys.stderr)
        raise SystemExit(1) from exc
