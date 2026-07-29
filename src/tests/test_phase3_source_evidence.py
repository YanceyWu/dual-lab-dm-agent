from __future__ import annotations

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from pm_agent.database import source_evidence
from pm_agent.database.bootstrap import main as init_db
from pm_agent.sync.jira.evidence_sync import JiraEvidenceConfig, sync_dataset


def _event(
    issue_ref: str,
    *,
    event_ref: str,
    source_time: str = "2026-07-29T01:00:00+00:00",
) -> source_evidence.IssueEvent:
    return source_evidence.IssueEvent(
        issue_ref=issue_ref,
        source_event_ref=event_ref,
        event_type="field_changed",
        field_key="status",
        from_value="todo",
        to_value="in_progress",
        source_updated_at=source_time,
        observed_at="2026-07-29T01:05:00+00:00",
    )


def _finish_complete(
    run_id: str,
    db_path: Path,
    *,
    cursor_time: str,
    cursor_ref: str,
    authoritative: bool = True,
) -> None:
    source_evidence.finish_staging(
        run_id,
        coverage_status="complete",
        pages_received=1,
        pages_expected=1,
        proposed_cursor_time=cursor_time,
        proposed_cursor_ref=cursor_ref,
        authoritative_manifest=authoritative,
        field_coverage={"status": True},
        db_path=db_path,
    )


def test_bootstrap_adds_b1_storage_idempotently_and_preserves_legacy_objects(
    isolated_db: Path,
) -> None:
    init_db(quiet=True)
    with sqlite3.connect(isolated_db) as connection:
        connection.execute(
            "INSERT INTO projects(id, name) VALUES ('project-synthetic-001', 'Synthetic')"
        )
        connection.commit()
        legacy_before = connection.execute("SELECT COUNT(*) FROM projects").fetchone()[0]

    init_db(quiet=True)

    with sqlite3.connect(isolated_db) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                """
                SELECT name FROM sqlite_master
                WHERE type = 'table' AND name LIKE '%evidence%'
                   OR type = 'table' AND name IN (
                       'jira_issue_event_stage', 'jira_issue_events',
                       'jira_issue_link_stage', 'jira_issue_links'
                   )
                """
            )
        }
        assert {
            "source_evidence_runs",
            "source_evidence_cursors",
            "source_evidence_manifest_stage",
            "source_evidence_published_items",
            "jira_issue_event_stage",
            "jira_issue_events",
            "jira_issue_link_stage",
            "jira_issue_links",
        } <= tables
        assert connection.execute("SELECT COUNT(*) FROM projects").fetchone()[0] == legacy_before
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []


def test_complete_publication_is_atomic_replay_safe_and_uses_compound_cursor(
    isolated_db: Path,
) -> None:
    init_db(quiet=True)
    first_run = source_evidence.start_run(
        "jira-evidence-synthetic",
        "board-synthetic",
        "jira_issue_history",
        overlap_seconds=300,
        db_path=isolated_db,
        run_id="run-first",
    )
    accepted, duplicated = source_evidence.stage_issue_events(
        first_run,
        [
            _event("SYN-1", event_ref="evt-1"),
            _event("SYN-1", event_ref="evt-1"),
        ],
        manifest_issue_refs=["SYN-1"],
        db_path=isolated_db,
    )
    assert (accepted, duplicated) == (1, 1)
    _finish_complete(
        first_run,
        isolated_db,
        cursor_time="2026-07-29T01:00:00+00:00",
        cursor_ref="SYN-1",
    )
    assert source_evidence.publish_run(first_run, db_path=isolated_db) == 1

    replay_run = source_evidence.start_run(
        "jira-evidence-synthetic",
        "board-synthetic",
        "jira_issue_history",
        overlap_seconds=300,
        db_path=isolated_db,
        run_id="run-replay",
    )
    source_evidence.stage_issue_events(
        replay_run,
        [
            _event("SYN-1", event_ref="evt-1"),
            _event("SYN-2", event_ref="evt-2"),
        ],
        manifest_issue_refs=["SYN-1", "SYN-2"],
        db_path=isolated_db,
    )
    _finish_complete(
        replay_run,
        isolated_db,
        cursor_time="2026-07-29T01:00:00+00:00",
        cursor_ref="SYN-2",
    )
    source_evidence.publish_run(replay_run, db_path=isolated_db)

    with sqlite3.connect(isolated_db) as connection:
        connection.row_factory = sqlite3.Row
        assert connection.execute("SELECT COUNT(*) FROM jira_issue_events").fetchone()[0] == 2
        replayed = connection.execute(
            "SELECT first_published_run_id, last_published_run_id "
            "FROM jira_issue_events WHERE source_event_ref = 'evt-1'"
        ).fetchone()
        assert dict(replayed) == {
            "first_published_run_id": "run-first",
            "last_published_run_id": "run-replay",
        }
    cursor = source_evidence.get_cursor(
        "jira-evidence-synthetic",
        "board-synthetic",
        "jira_issue_history",
        db_path=isolated_db,
    )
    assert cursor is not None
    assert cursor["cursor_time"] == "2026-07-29T01:00:00+00:00"
    assert cursor["cursor_ref"] == "SYN-2"
    assert cursor["published_run_id"] == "run-replay"
    assert cursor["overlap_seconds"] == 300


def test_partial_run_cannot_advance_cursor_or_close_manifest_item(isolated_db: Path) -> None:
    init_db(quiet=True)
    complete_run = source_evidence.start_run(
        "jira-evidence-synthetic",
        "board-synthetic",
        "jira_issue_history",
        overlap_seconds=300,
        db_path=isolated_db,
        run_id="run-complete",
    )
    source_evidence.stage_issue_events(
        complete_run,
        [_event("SYN-1", event_ref="evt-1")],
        manifest_issue_refs=["SYN-1"],
        db_path=isolated_db,
    )
    _finish_complete(
        complete_run,
        isolated_db,
        cursor_time="2026-07-29T01:00:00+00:00",
        cursor_ref="SYN-1",
    )
    source_evidence.publish_run(complete_run, db_path=isolated_db)

    partial_run = source_evidence.start_run(
        "jira-evidence-synthetic",
        "board-synthetic",
        "jira_issue_history",
        overlap_seconds=300,
        db_path=isolated_db,
        run_id="run-partial",
    )
    source_evidence.stage_issue_events(
        partial_run,
        [_event("SYN-2", event_ref="evt-2")],
        manifest_issue_refs=["SYN-2"],
        db_path=isolated_db,
    )
    source_evidence.finish_staging(
        partial_run,
        coverage_status="complete",
        pages_received=1,
        pages_expected=2,
        proposed_cursor_time="2026-07-29T02:00:00+00:00",
        proposed_cursor_ref="SYN-2",
        authoritative_manifest=True,
        db_path=isolated_db,
    )
    with pytest.raises(ValueError, match="complete evidence run"):
        source_evidence.publish_run(partial_run, db_path=isolated_db)

    with sqlite3.connect(isolated_db) as connection:
        cursor = connection.execute(
            "SELECT published_run_id FROM source_evidence_cursors"
        ).fetchone()[0]
        current = connection.execute(
            """
            SELECT item_ref FROM source_evidence_published_items
            WHERE is_current = 1
            """
        ).fetchall()
        coverage = connection.execute(
            "SELECT coverage_status FROM source_evidence_runs WHERE run_id = 'run-partial'"
        ).fetchone()[0]
    assert cursor == "run-complete"
    assert current == [("SYN-1",)]
    assert coverage == "partial"


def test_only_complete_authoritative_manifest_creates_tombstone(isolated_db: Path) -> None:
    init_db(quiet=True)
    first_run = source_evidence.start_run(
        "jira-evidence-synthetic",
        "board-synthetic",
        "jira_issue_history",
        overlap_seconds=0,
        db_path=isolated_db,
        run_id="run-manifest-1",
    )
    source_evidence.stage_issue_events(
        first_run,
        [
            _event("SYN-1", event_ref="evt-1"),
            _event("SYN-2", event_ref="evt-2"),
        ],
        manifest_issue_refs=["SYN-1", "SYN-2"],
        db_path=isolated_db,
    )
    _finish_complete(
        first_run,
        isolated_db,
        cursor_time="2026-07-29T01:00:00+00:00",
        cursor_ref="SYN-2",
    )
    source_evidence.publish_run(first_run, db_path=isolated_db)

    second_run = source_evidence.start_run(
        "jira-evidence-synthetic",
        "board-synthetic",
        "jira_issue_history",
        overlap_seconds=0,
        db_path=isolated_db,
        run_id="run-manifest-2",
    )
    source_evidence.stage_issue_events(
        second_run,
        [_event("SYN-2", event_ref="evt-2")],
        manifest_issue_refs=["SYN-2"],
        db_path=isolated_db,
    )
    _finish_complete(
        second_run,
        isolated_db,
        cursor_time="2026-07-29T02:00:00+00:00",
        cursor_ref="SYN-2",
    )
    source_evidence.publish_run(second_run, db_path=isolated_db)

    with sqlite3.connect(isolated_db) as connection:
        assert connection.execute(
            """
            SELECT is_current, removed_run_id
            FROM source_evidence_published_items
            WHERE item_ref = 'SYN-1'
            """
        ).fetchone() == (0, "run-manifest-2")
        assert connection.execute(
            """
            SELECT COUNT(*) FROM jira_issue_events
            WHERE issue_ref = 'SYN-1' AND event_type = 'tombstone'
            """
        ).fetchone()[0] == 1


def test_multiple_directed_links_and_unknown_types_are_not_flattened(
    isolated_db: Path,
) -> None:
    init_db(quiet=True)
    run_id = source_evidence.start_run(
        "jira-evidence-synthetic",
        "board-synthetic",
        "jira_issue_links",
        overlap_seconds=300,
        db_path=isolated_db,
        run_id="run-links",
    )
    source_evidence.stage_issue_links(
        run_id,
        [
            source_evidence.IssueLink(
                source_link_ref="link-1",
                issue_ref="SYN-1",
                related_issue_ref="SYN-2",
                link_type="Blocks",
                direction="outward",
                observation_state="active",
                source_updated_at="2026-07-29T01:00:00+00:00",
                observed_at="2026-07-29T01:05:00+00:00",
            ),
            source_evidence.IssueLink(
                source_link_ref="link-2",
                issue_ref="SYN-1",
                related_issue_ref="SYN-3",
                link_type="Synthetic Unknown",
                direction="inward",
                observation_state="unsupported",
                source_updated_at="2026-07-29T01:00:00+00:00",
                observed_at="2026-07-29T01:05:00+00:00",
            ),
        ],
        manifest_link_refs=["link-1", "link-2"],
        db_path=isolated_db,
    )
    _finish_complete(
        run_id,
        isolated_db,
        cursor_time="2026-07-29T01:00:00+00:00",
        cursor_ref="SYN-1",
    )
    source_evidence.publish_run(run_id, db_path=isolated_db)

    removal_run = source_evidence.start_run(
        "jira-evidence-synthetic",
        "board-synthetic",
        "jira_issue_links",
        overlap_seconds=300,
        db_path=isolated_db,
        run_id="run-links-removal",
    )
    source_evidence.stage_issue_links(
        removal_run,
        [
            source_evidence.IssueLink(
                source_link_ref="link-2",
                issue_ref="SYN-1",
                related_issue_ref="SYN-3",
                link_type="Synthetic Unknown",
                direction="inward",
                observation_state="unsupported",
                source_updated_at="2026-07-29T01:00:00+00:00",
                observed_at="2026-07-29T02:05:00+00:00",
            )
        ],
        manifest_link_refs=["link-2"],
        db_path=isolated_db,
    )
    _finish_complete(
        removal_run,
        isolated_db,
        cursor_time="2026-07-29T02:00:00+00:00",
        cursor_ref="SYN-1",
    )
    source_evidence.publish_run(removal_run, db_path=isolated_db)

    with sqlite3.connect(isolated_db) as connection:
        rows = connection.execute(
            """
            SELECT related_issue_ref, link_type, direction, observation_state
            FROM jira_issue_links
            WHERE observation_state != 'tombstone'
            ORDER BY source_link_ref
            """
        ).fetchall()
        tombstones = connection.execute(
            """
            SELECT source_link_ref, issue_ref, related_issue_ref, observation_state
            FROM jira_issue_links
            WHERE observation_state = 'tombstone'
            """
        ).fetchall()
    assert rows == [
        ("SYN-2", "Blocks", "outward", "active"),
        ("SYN-3", "Synthetic Unknown", "inward", "unsupported"),
    ]
    assert tombstones == [("link-1", "SYN-1", "SYN-2", "tombstone")]


class _Response:
    def __init__(self, payload: dict, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code

    def json(self) -> dict:
        return self._payload


class _Session:
    def __init__(self, search_pages: list[_Response], changelog_pages: list[_Response] | None = None):
        self.search_pages = list(search_pages)
        self.changelog_pages = list(changelog_pages or [])
        self.posts: list[dict] = []
        self.gets: list[dict] = []

    def post(self, url: str, *, json: dict, timeout: int) -> _Response:
        self.posts.append({"url": url, "json": json, "timeout": timeout})
        return self.search_pages.pop(0)

    def get(self, url: str, *, params: dict, timeout: int) -> _Response:
        self.gets.append({"url": url, "params": params, "timeout": timeout})
        return self.changelog_pages.pop(0)


def test_adapter_marks_missing_pagination_token_partial_and_does_not_publish(
    isolated_db: Path,
) -> None:
    init_db(quiet=True)
    session = _Session(
        [
            _Response(
                {
                    "issues": [
                        {
                            "key": "SYN-1",
                            "fields": {
                                "updated": "2026-07-29T01:00:00+00:00",
                                "issuelinks": [],
                            },
                        }
                    ],
                    "isLast": False,
                }
            )
        ]
    )
    config = JiraEvidenceConfig(
        source_id="jira-evidence-synthetic",
        board_id="board-synthetic",
        base_jql="project = SYN",
        field_mappings={"status": "status"},
    )
    run_id, result = sync_dataset(
        session,
        "https://synthetic.invalid",
        config,
        "jira_issue_links",
        db_path=str(isolated_db),
        observed_at="2026-07-29T01:05:00+00:00",
    )
    assert result.coverage_status == "partial"
    with sqlite3.connect(isolated_db) as connection:
        assert connection.execute(
            "SELECT publication_status FROM source_evidence_runs WHERE run_id = ?",
            [run_id],
        ).fetchone()[0] == "rejected"
        assert connection.execute("SELECT COUNT(*) FROM source_evidence_cursors").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM jira_issue_links").fetchone()[0] == 0


def test_adapter_paginates_changelog_and_stores_only_normalized_fields(
    isolated_db: Path,
) -> None:
    init_db(quiet=True)
    session = _Session(
        [
            _Response(
                {
                    "issues": [
                        {
                            "key": "SYN-1",
                            "fields": {
                                "updated": "2026-07-29T01:00:00+00:00",
                                "status": {"id": "status-2", "name": "Private status label"},
                                "fixVersions": [
                                    {"id": "version-2", "name": "Private Release B"},
                                    {"id": "version-1", "name": "Private Release A"},
                                ],
                            },
                        }
                    ],
                    "isLast": True,
                }
            )
        ],
        [
            _Response(
                {
                    "values": [
                        {
                            "id": "history-1",
                            "created": "2026-07-29T00:30:00+00:00",
                            "items": [
                                {
                                    "fieldId": "status",
                                    "fromString": "todo",
                                    "toString": "in_progress",
                                },
                                {
                                    "fieldId": "summary",
                                    "fromString": "Private old summary",
                                    "toString": "Private new summary",
                                },
                            ],
                        }
                    ],
                    "total": 2,
                }
            ),
            _Response(
                {
                    "values": [
                        {
                            "id": "history-2",
                            "created": "2026-07-29T00:45:00+00:00",
                            "items": [
                                {
                                    "fieldId": "status",
                                    "fromString": "in_progress",
                                    "toString": "done",
                                }
                            ],
                        }
                    ],
                    "total": 2,
                }
            ),
        ],
    )
    config = JiraEvidenceConfig(
        source_id="jira-evidence-synthetic",
        board_id="board-synthetic",
        base_jql="project = SYN",
        field_mappings={"status": "status", "fixVersions": "fix_versions"},
        page_size=1,
    )
    _run_id, result = sync_dataset(
        session,
        "https://synthetic.invalid",
        config,
        "jira_issue_history",
        db_path=str(isolated_db),
        observed_at="2026-07-29T01:05:00+00:00",
    )
    assert result.coverage_status == "complete"
    assert len(session.gets) == 2
    with sqlite3.connect(isolated_db) as connection:
        fields = connection.execute(
            """
            SELECT field_key, from_value, to_value
            FROM jira_issue_events
            ORDER BY source_updated_at, field_key
            """
        ).fetchall()
        serialized = repr(fields)
    assert fields == [
        ("status", "todo", "in_progress"),
        ("status", "in_progress", "done"),
        ("fix_versions", "", '["version-1","version-2"]'),
        ("issue_observed", "", "present"),
        ("status", "", "status-2"),
    ]
    assert "Private" not in serialized


def test_concurrent_publication_claims_run_once(isolated_db: Path) -> None:
    init_db(quiet=True)
    run_id = source_evidence.start_run(
        "jira-evidence-synthetic",
        "board-synthetic",
        "jira_issue_history",
        overlap_seconds=300,
        db_path=isolated_db,
        run_id="run-concurrent",
    )
    source_evidence.stage_issue_events(
        run_id,
        [_event("SYN-1", event_ref="evt-1")],
        manifest_issue_refs=["SYN-1"],
        db_path=isolated_db,
    )
    _finish_complete(
        run_id,
        isolated_db,
        cursor_time="2026-07-29T01:00:00+00:00",
        cursor_ref="SYN-1",
    )

    def publish() -> str:
        try:
            source_evidence.publish_run(run_id, db_path=isolated_db)
            return "published"
        except ValueError:
            return "rejected"

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = sorted(executor.map(lambda _index: publish(), range(2)))
    assert outcomes == ["published", "rejected"]
    with sqlite3.connect(isolated_db) as connection:
        assert connection.execute("SELECT COUNT(*) FROM jira_issue_events").fetchone()[0] == 1
        assert connection.execute(
            "SELECT publication_status FROM source_evidence_runs WHERE run_id = ?",
            [run_id],
        ).fetchone()[0] == "published"
