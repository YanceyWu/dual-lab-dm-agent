from __future__ import annotations

import io
import importlib.util
import sqlite3
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "tools" / "rehearse_release.py"
sys.path.insert(0, str(ROOT / "tools"))
SPEC = importlib.util.spec_from_file_location("rehearse_release", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
rehearse_release = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(rehearse_release)


def _archive_with_file() -> tarfile.TarFile:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as archive:
        payload = b"portable test payload"
        info = tarfile.TarInfo("sample.txt")
        info.size = len(payload)
        archive.addfile(info, io.BytesIO(payload))
    buffer.seek(0)
    return tarfile.open(fileobj=buffer, mode="r")


def test_extract_git_archive_uses_filter_when_available(
    tmp_path: Path,
    monkeypatch,
) -> None:
    with _archive_with_file() as archive:
        calls: list[tuple[Path, str | None]] = []

        def fake_extractall(path=".", members=None, *, numeric_owner=False, filter=None):
            calls.append((Path(path), filter))

        monkeypatch.setattr(archive, "extractall", fake_extractall)
        rehearse_release._extract_git_archive(archive, tmp_path)

    assert calls == [(tmp_path, "data")]


def test_extract_git_archive_falls_back_without_filter(tmp_path: Path) -> None:
    with _archive_with_file() as archive:
        rehearse_release._extract_git_archive(archive, tmp_path)

    assert (tmp_path / "sample.txt").read_text(encoding="utf-8") == "portable test payload"


def test_verify_upgraded_database_accepts_canonical_current_state_tables(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "rehearsal.db"
    core_tables = set(rehearse_release.CORE_TABLES)
    required_objects = {
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
        "current_state_staffing_import_sessions",
        "current_state_staffing_import_attempts",
        "current_state_staffing_import_runs",
        "current_state_staffing_publications",
        "current_state_staffing_members",
        "current_state_staffing_projects",
        "current_state_staffing_assignments",
        "current_state_staffing_member_loads",
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
    }

    with sqlite3.connect(database_path) as connection:
        for table_name in sorted(core_tables | required_objects):
            if table_name == "staffing_proposals":
                connection.execute(
                    """
                    CREATE TABLE staffing_proposals (
                        id TEXT PRIMARY KEY,
                        confirmation_token_hash TEXT
                    )
                    """
                )
            else:
                connection.execute(
                    f'CREATE TABLE "{table_name}" (id TEXT PRIMARY KEY)'
                )
        connection.commit()

    rehearse_release.verify_upgraded_database(
        database_path,
        rehearse_release.counts(database_path),
    )
