from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

from pm_agent.database.bootstrap import main as init_db
from scripts.import_confluence_pages import import_confluence_pages
from scripts.import_jira_boards import import_jira_boards


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_import_jira_boards_reconciles_removed_registry_rows(isolated_db: Path, tmp_path: Path) -> None:
    init_db(quiet=True)

    con = sqlite3.connect(isolated_db)
    try:
        con.execute(
            """
            INSERT INTO jira_board_configs
                (id, name, project_key, base_jql, active)
            VALUES
                ('stale-board', 'Stale Board', 'OLD', 'project = OLD', 1)
            """
        )
        con.execute(
            """
            INSERT INTO jira_stream_versions
                (id, board_id, project_key, name)
            VALUES
                ('version-1', 'stale-board', 'OLD', 'Old Release')
            """
        )
        con.execute(
            """
            INSERT INTO jira_issues
                (id, board_id, version_id, project_key)
            VALUES
                ('OLD-1', 'stale-board', 'version-1', 'OLD')
            """
        )
        con.execute(
            """
            INSERT INTO jira_sprints
                (id, board_id, name)
            VALUES
                ('sprint-1', 'stale-board', 'Stale Sprint')
            """
        )
        con.execute(
            """
            INSERT INTO jira_health_snapshots
                (board_id, version_id, snapshot_date)
            VALUES
                ('stale-board', 'version-1', '2026-07-12')
            """
        )
        con.executemany(
            """
            INSERT INTO data_sources
                (id, source_type, source_name, ingestion_mode, refresh_sla_hours, active, config_json, notes)
            VALUES (?, 'jira', ?, 'api', 24, 1, '{}', '')
            """,
            [
                ("jira-release-stale-board", "Stale Release Source"),
                ("jira-health-stale-board", "Stale Health Source"),
            ],
        )
        con.execute(
            """
            INSERT INTO memory_facts (category, subject, fact, confidence, source)
            VALUES ('jira_project_key', 'OLD', 'Old project key', 1.0, 'csv-import')
            """
        )
        con.execute(
            """
            INSERT INTO memory_facts (category, subject, fact, confidence, source)
            VALUES ('jira_project_key', 'MANUAL', 'Manual project key', 1.0, 'manual')
            """
        )
        con.commit()
    finally:
        con.close()

    csv_path = tmp_path / "jira_boards.csv"
    _write_csv(
        csv_path,
        [
            "id",
            "name",
            "project_key",
            "base_jql",
            "version_name_pattern",
            "board_id",
            "board_url",
            "pm_project_id",
            "active",
            "issues_use_base_jql",
            "notes",
        ],
        [
            {
                "id": "keep-board",
                "name": "Keep Board",
                "project_key": "NEW",
                "base_jql": "project = NEW",
                "version_name_pattern": "%NEW%",
                "board_id": "",
                "board_url": "",
                "pm_project_id": "",
                "active": "1",
                "issues_use_base_jql": "0",
                "notes": "current board",
            }
        ],
    )

    import_jira_boards(csv_path)

    con = sqlite3.connect(isolated_db)
    try:
        assert con.execute(
            "SELECT COUNT(*) FROM jira_board_configs WHERE id = 'stale-board'"
        ).fetchone()[0] == 0
        assert con.execute(
            "SELECT COUNT(*) FROM data_sources WHERE id IN ('jira-release-stale-board', 'jira-health-stale-board')"
        ).fetchone()[0] == 0
        assert con.execute(
            "SELECT COUNT(*) FROM jira_stream_versions WHERE board_id = 'stale-board'"
        ).fetchone()[0] == 0
        assert con.execute(
            "SELECT COUNT(*) FROM jira_issues WHERE board_id = 'stale-board'"
        ).fetchone()[0] == 0
        assert con.execute(
            "SELECT COUNT(*) FROM jira_sprints WHERE board_id = 'stale-board'"
        ).fetchone()[0] == 0
        assert con.execute(
            "SELECT COUNT(*) FROM jira_health_snapshots WHERE board_id = 'stale-board'"
        ).fetchone()[0] == 0
        assert con.execute(
            "SELECT COUNT(*) FROM jira_board_configs WHERE id = 'keep-board'"
        ).fetchone()[0] == 1
        assert con.execute(
            """
            SELECT COUNT(*) FROM memory_facts
            WHERE category = 'jira_project_key' AND subject = 'OLD' AND source = 'csv-import'
            """
        ).fetchone()[0] == 0
        assert con.execute(
            """
            SELECT COUNT(*) FROM memory_facts
            WHERE category = 'jira_project_key' AND subject = 'MANUAL' AND source = 'manual'
            """
        ).fetchone()[0] == 1
    finally:
        con.close()


def test_import_confluence_pages_reconciles_removed_registry_rows(
    isolated_db: Path,
    tmp_path: Path,
) -> None:
    init_db(quiet=True)

    con = sqlite3.connect(isolated_db)
    try:
        con.execute(
            """
            INSERT INTO confluence_pages (id, board_id, title, page_type)
            VALUES ('stale-page', 'stale-board', 'Old Page', 'weekly_status')
            """
        )
        con.execute(
            """
            INSERT INTO confluence_pages (id, board_id, title, page_type)
            VALUES ('global-page', 'global', 'Global Page', 'reference')
            """
        )
        con.execute(
            """
            INSERT INTO confluence_status_snapshots
                (board_id, page_id, page_title, snapshot_date)
            VALUES
                ('stale-board', 'stale-page', 'Old Page', '2026-07-12')
            """
        )
        con.execute(
            """
            INSERT INTO action_tracker
                (page_id, item, synced_date)
            VALUES
                ('stale-page', 'Remove me', '2026-07-12')
            """
        )
        con.commit()
    finally:
        con.close()

    csv_path = tmp_path / "confluence_pages.csv"
    _write_csv(
        csv_path,
        ["id", "board_id", "title", "page_type", "last_synced", "last_modified", "content_summary"],
        [
            {
                "id": "keep-page",
                "board_id": "keep-board",
                "title": "Keep Page",
                "page_type": "weekly_status",
                "last_synced": "",
                "last_modified": "",
                "content_summary": "current page",
            }
        ],
    )

    import_confluence_pages(csv_path)

    con = sqlite3.connect(isolated_db)
    try:
        assert con.execute(
            "SELECT COUNT(*) FROM confluence_pages WHERE board_id = 'stale-board'"
        ).fetchone()[0] == 0
        assert con.execute(
            "SELECT COUNT(*) FROM confluence_status_snapshots WHERE board_id = 'stale-board'"
        ).fetchone()[0] == 0
        assert con.execute(
            "SELECT COUNT(*) FROM action_tracker WHERE page_id = 'stale-page'"
        ).fetchone()[0] == 0
        assert con.execute(
            "SELECT COUNT(*) FROM confluence_pages WHERE id = 'keep-page'"
        ).fetchone()[0] == 1
        assert con.execute(
            "SELECT COUNT(*) FROM confluence_pages WHERE id = 'global-page' AND board_id = 'global'"
        ).fetchone()[0] == 1
    finally:
        con.close()
