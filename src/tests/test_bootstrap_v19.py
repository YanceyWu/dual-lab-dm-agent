from __future__ import annotations

import sqlite3
from pathlib import Path

from pm_agent.database.bootstrap import main as init_db


LEGACY_JIRA_VERSIONS_DDL = """
CREATE TABLE jira_versions (
    id TEXT PRIMARY KEY,
    project_key TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    status TEXT,
    released INTEGER DEFAULT 0,
    release_date TEXT,
    start_date TEXT,
    total_issues INTEGER DEFAULT 0,
    done_issues INTEGER DEFAULT 0,
    inprogress_issues INTEGER DEFAULT 0,
    todo_issues INTEGER DEFAULT 0,
    progress_pct REAL DEFAULT 0.0,
    raw_data TEXT DEFAULT '{}',
    synced_at TEXT DEFAULT (datetime('now'))
);
"""


def _table_exists(db_path: Path, table_name: str) -> bool:
    con = sqlite3.connect(db_path)
    try:
        row = con.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            [table_name],
        ).fetchone()
        return row is not None
    finally:
        con.close()


def test_bootstrap_migrates_legacy_jira_versions_when_board_mapping_exists(
    isolated_db: Path,
) -> None:
    init_db(quiet=True)

    con = sqlite3.connect(isolated_db)
    try:
        con.executescript(LEGACY_JIRA_VERSIONS_DDL)
        con.execute(
            """
            INSERT INTO jira_board_configs
                (id, name, project_key, base_jql, version_name_pattern, active)
            VALUES
                ('legacy-atlas', 'Legacy Atlas', 'ATL', 'project = ATL', '%ATLAS%', 1)
            """
        )
        con.execute(
            """
            INSERT INTO jira_versions
                (id, project_key, name, status, release_date, total_issues, done_issues,
                 inprogress_issues, todo_issues, progress_pct, raw_data, synced_at)
            VALUES
                ('legacy-v1', 'ATL', 'ATLAS 2026R08', 'unreleased', '2026-08-15',
                 10, 4, 3, 3, 40.0, '{}', '2026-07-12 10:00:00')
            """
        )
        con.commit()
    finally:
        con.close()

    init_db(quiet=True)

    assert not _table_exists(isolated_db, "jira_versions")
    con = sqlite3.connect(isolated_db)
    try:
        migrated = con.execute(
            """
            SELECT board_id, project_key, name, progress_pct, total_issues, done_issues
            FROM jira_stream_versions
            WHERE id = 'legacy-v1'
            """
        ).fetchall()
    finally:
        con.close()

    assert migrated == [("legacy-atlas", "ATL", "ATLAS 2026R08", 40.0, 10, 4)]


def test_bootstrap_retains_unmapped_legacy_jira_versions_for_manual_followup(
    isolated_db: Path,
) -> None:
    init_db(quiet=True)

    con = sqlite3.connect(isolated_db)
    try:
        con.executescript(LEGACY_JIRA_VERSIONS_DDL)
        con.execute(
            """
            INSERT INTO jira_versions
                (id, project_key, name, status, progress_pct, raw_data, synced_at)
            VALUES
                ('legacy-v2', 'BKN', 'Unmapped Release', 'unreleased', 0.0, '{}', '2026-07-12 10:00:00')
            """
        )
        con.commit()
    finally:
        con.close()

    init_db(quiet=True)

    assert _table_exists(isolated_db, "jira_versions")
    con = sqlite3.connect(isolated_db)
    try:
        legacy_count = con.execute("SELECT COUNT(*) FROM jira_versions").fetchone()[0]
        migrated_count = con.execute(
            "SELECT COUNT(*) FROM jira_stream_versions WHERE id = 'legacy-v2'"
        ).fetchone()[0]
    finally:
        con.close()

    assert legacy_count == 1
    assert migrated_count == 0
