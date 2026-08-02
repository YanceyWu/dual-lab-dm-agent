#!/usr/bin/env python3
# ruff: noqa: E402
"""Seed deterministic synthetic evidence for the R1 demo database.

This script is sample-data tooling, not a product feature.  It inserts rows
only into existing tables through their existing schemas so the promoted
engines can demonstrate real states: authoritative source-evidence runs,
JIRA-style issues/releases/sprints, legacy health snapshots, one overdue
action, and one overloaded member.  All rows are synthetic
(``SYNTHETIC_DATASET_V1``) and the script is idempotent: it deletes its own
previously seeded rows before inserting them again.
"""

from __future__ import annotations

import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pm_agent.config import settings

BOARD_ID = "atlas-board"
BEACON_BOARD_ID = "beacon-board"
PROJECT_ID = "project-synthetic-atlas"
BEACON_PROJECT_ID = "project-synthetic-beacon"
SOURCE_ID = "source-synthetic-jira-evidence"
HISTORY_RUN = "evidence-history-demo-001"
LINKS_RUN = "evidence-links-demo-001"
VERSION_REF = "version-demo-001"
SPRINT_REF = "sprint-demo-001"
ISSUE_REFS = ("ATLAS-1", "ATLAS-2", "ATLAS-3")
MARKER = "SYNTHETIC_DATASET_V1"
HIREF_MEMBERS = (
    "member-synthetic-001",
    "member-synthetic-002",
    "member-synthetic-003",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _seed(connection: sqlite3.Connection) -> None:
    observed_at = "2026-08-01T11:00:00+00:00"
    finished_at = "2026-08-01T12:00:00+00:00"

    # Authoritative source-evidence runs make the derivation complete/fresh.
    connection.execute(
        """
        INSERT INTO source_evidence_runs
            (run_id, source_id, board_id, dataset, coverage_status, publication_status,
             prior_published_run_id, requested_cursor_time, requested_cursor_ref,
             proposed_cursor_time, proposed_cursor_ref, overlap_seconds,
             authoritative_manifest, pages_expected, pages_received, rows_read,
             rows_accepted, rows_deduplicated, rows_rejected, rows_published,
             field_coverage_json, warning_codes_json, error_code,
             started_at, finished_at, published_at)
        VALUES (?, ?, ?, 'jira_issue_history', 'complete', 'published',
                '', '', '', '', '', 0, 1, 1, 1, ?, ?, 0, 0, ?,
                '{}', '[]', '', ?, ?, ?)
        """,
        [
            HISTORY_RUN,
            SOURCE_ID,
            BOARD_ID,
            len(ISSUE_REFS),
            len(ISSUE_REFS),
            len(ISSUE_REFS),
            observed_at,
            finished_at,
            finished_at,
        ],
    )
    connection.execute(
        """
        INSERT INTO source_evidence_runs
            (run_id, source_id, board_id, dataset, coverage_status, publication_status,
             prior_published_run_id, requested_cursor_time, requested_cursor_ref,
             proposed_cursor_time, proposed_cursor_ref, overlap_seconds,
             authoritative_manifest, pages_expected, pages_received, rows_read,
             rows_accepted, rows_deduplicated, rows_rejected, rows_published,
             field_coverage_json, warning_codes_json, error_code,
             started_at, finished_at, published_at)
        VALUES (?, ?, ?, 'jira_issue_links', 'complete', 'published',
                '', '', '', '', '', 0, 1, 1, 1, 0, 0, 0, 0, 0,
                '{}', '[]', '', ?, ?, ?)
        """,
        [
            LINKS_RUN,
            SOURCE_ID,
            BOARD_ID,
            observed_at,
            finished_at,
            finished_at,
        ],
    )
    connection.executemany(
        """
        INSERT INTO source_evidence_cursors
            (source_id, board_id, dataset, cursor_time, cursor_ref,
             published_run_id, overlap_seconds, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, 0, ?)
        """,
        [
            (SOURCE_ID, BOARD_ID, "jira_issue_history", finished_at, "synthetic-cursor-history", HISTORY_RUN, finished_at),
            (SOURCE_ID, BOARD_ID, "jira_issue_links", finished_at, "synthetic-cursor-links", LINKS_RUN, finished_at),
        ],
    )
    connection.executemany(
        """
        INSERT INTO source_evidence_published_items
            (source_id, board_id, dataset, item_ref, is_current,
             first_published_run_id, last_published_run_id, removed_run_id)
        VALUES (?, ?, 'jira_issue_history', ?, 1, ?, ?, '')
        """,
        [(SOURCE_ID, BOARD_ID, ref, HISTORY_RUN, HISTORY_RUN) for ref in ISSUE_REFS],
    )

    # Issue events drive canonical work items, story points, and release scope.
    issue_rows = [
        ("ATLAS-1", "done", "done", 3.0),
        ("ATLAS-2", "done", "done", 2.0),
        ("ATLAS-3", "in_progress", "indeterminate", 1.0),
    ]
    events = []
    for issue_ref, status, category, points in issue_rows:
        events.extend(
            [
                (SOURCE_ID, BOARD_ID, f"demo-{issue_ref}-status", issue_ref, f"demo-event-{issue_ref}-status", "issue_observed", "status", "", status, observed_at, observed_at, HISTORY_RUN, HISTORY_RUN),
                (SOURCE_ID, BOARD_ID, f"demo-{issue_ref}-category", issue_ref, f"demo-event-{issue_ref}-category", "issue_observed", "status_category", "", category, observed_at, observed_at, HISTORY_RUN, HISTORY_RUN),
                (SOURCE_ID, BOARD_ID, f"demo-{issue_ref}-points", issue_ref, f"demo-event-{issue_ref}-points", "issue_observed", "story_points", "", str(points), observed_at, observed_at, HISTORY_RUN, HISTORY_RUN),
                (SOURCE_ID, BOARD_ID, f"demo-{issue_ref}-version", issue_ref, f"demo-event-{issue_ref}-version", "issue_observed", "fix_versions", "", f'["{VERSION_REF}"]', observed_at, observed_at, HISTORY_RUN, HISTORY_RUN),
            ]
        )
    connection.executemany(
        """
        INSERT INTO jira_issue_events
            (source_id, board_id, dedup_key, issue_ref, source_event_ref,
             event_type, field_key, from_value, to_value, source_updated_at,
             observed_at, first_published_run_id, last_published_run_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        events,
    )
    connection.executemany(
        """
        INSERT INTO jira_issues
            (id, board_id, version_id, project_key, summary, issue_type,
             status, status_category, story_points, assignee_id, assignee_name, synced_at)
        VALUES (?, ?, ?, 'ATL', ?, 'Story', ?, ?, ?, 'member-synthetic-001', 'Synthetic Member 001', ?)
        """,
        [
            (ref, BOARD_ID, VERSION_REF, f"{MARKER} demo issue {ref}", status, category, points, observed_at)
            for ref, status, category, points in issue_rows
        ],
    )
    connection.execute(
        """
        INSERT INTO jira_stream_versions
            (id, board_id, project_key, name, release_date, start_date,
             status, released, total_issues, done_issues, inprogress_issues,
             todo_issues, progress_pct, total_sp, done_sp, inprogress_sp, synced_at)
        VALUES (?, ?, 'ATL', 'Atlas Demo Release', '2026-08-20', '2026-07-01',
                'unreleased', 0, 3, 2, 1, 0, 66.7, 6.0, 5.0, 1.0, ?)
        """,
        [VERSION_REF, BOARD_ID, observed_at],
    )
    connection.execute(
        """
        INSERT INTO jira_sprints
            (id, board_id, name, state, start_date, end_date, goal,
             committed_sp, delivered_sp, completion_pct, total_issues, done_issues,
             bug_count, defect_count, synced_at)
        VALUES (?, ?, 'Atlas Demo Sprint', 'closed', '2026-07-01', '2026-07-14',
                'Deliver the demo backlog', 8.0, 6.0, 75.0, 3, 2, 1, 1, ?)
        """,
        [SPRINT_REF, BOARD_ID, observed_at],
    )

    # Legacy health snapshots drive the project-health Attention rule.
    connection.execute(
        """
        INSERT INTO jira_health_snapshots
            (board_id, version_id, snapshot_date, sprint_id, sprint_name,
             velocity_score, sprint_score, defect_score, scope_score,
             overall_score, overall_grade, remaining_sp, done_sp, total_sp,
             sp_progress_pct, summary_text, risks_json)
        VALUES (?, ?, '2026-08-01', ?, 'Atlas Demo Sprint',
                6.0, 4.0, 2.0, 3.0, 35.0, 'RED', 1.0, 5.0, 6.0, 83.3,
                'SYNTHETIC_DATASET_V1 demo snapshot', '[]')
        """,
        [BOARD_ID, VERSION_REF, SPRINT_REF],
    )
    connection.execute(
        """
        INSERT INTO confluence_status_snapshots
            (board_id, page_id, page_title, snapshot_date, rag_status,
             status_as_of, owner, summary_text, risks_text, impact_text,
             sprint_iteration, milestones_text, raw_content, synced_at)
        VALUES (?, 'demo-page-001', 'Atlas Demo Status', '2026-08-01', 'AMBER',
                '2026-08-01', 'Synthetic Member 001', 'Demo summary',
                'Demo risk', 'Demo impact', 'sprint-demo-001',
                'Milestone text', 'Raw demo content', ?)
        """,
        [BOARD_ID, observed_at],
    )
    # Beacon has no source evidence (partial derivation by design) but keeps
    # legacy snapshots so the project-health Attention rule covers both
    # active projects with distinct states (Atlas red, Beacon amber).
    connection.execute(
        """
        INSERT INTO jira_health_snapshots
            (board_id, snapshot_date, overall_score, overall_grade,
             summary_text, risks_json)
        VALUES (?, '2026-08-01', 62.0, 'AMBER',
                'SYNTHETIC_DATASET_V1 demo beacon snapshot', '[]')
        """,
        [BEACON_BOARD_ID],
    )
    connection.execute(
        """
        INSERT INTO confluence_status_snapshots
            (board_id, page_id, page_title, snapshot_date, rag_status,
             status_as_of, owner, summary_text, risks_text, impact_text,
             sprint_iteration, milestones_text, raw_content, synced_at)
        VALUES (?, 'demo-page-002', 'Beacon Demo Status', '2026-08-01', 'CLEAR',
                '2026-08-01', 'Synthetic Member 003', 'Beacon summary',
                '', '', '', '', 'Raw beacon content', ?)
        """,
        [BEACON_BOARD_ID, observed_at],
    )

    # One overdue high-priority action drives the action Attention rule and
    # the weekly-brief next-actions section.
    connection.execute(
        """
        INSERT INTO action_items
            (id, title, owner_id, source, priority, status, due_date, notes, created_at)
        VALUES (1, ?, 'member-synthetic-001', 'manual', 'high', 'open',
                '2026-07-20', 'SYNTHETIC_DATASET_V1 demo overdue follow-up', ?)
        """,
        [f"{MARKER} overdue follow-up", observed_at],
    )

    # HIREF / contract-continuity demo states: member 001 has a current
    # contract plus a registered renewal, member 002 is expiring without a
    # renewal, member 003 has no current contract, and one HIREF slot is
    # free with an open staffing placeholder.
    connection.execute(
        """
        UPDATE employees
        SET resource_type = 'STFTE', billing_end_date = ?, wd_id = id
        WHERE id = 'member-synthetic-001'
        """,
        ["2026-12-31"],
    )
    connection.execute(
        """
        UPDATE employees
        SET resource_type = 'STFTE', billing_end_date = ?, wd_id = id
        WHERE id = 'member-synthetic-002'
        """,
        ["2026-09-30"],
    )
    connection.execute(
        """
        UPDATE employees
        SET resource_type = 'STFTE', billing_end_date = '2026-08-31', wd_id = id
        WHERE id = 'member-synthetic-003'
        """
    )
    connection.executemany(
        """
        INSERT INTO hiref
            (id, project, request_type, start_date, end_date, notes, created_at)
        VALUES (?, ?, 'STFTE', ?, ?, ?, ?)
        """,
        [
            ("hiref-synthetic-001", "project-synthetic-atlas", "2026-01-01", "2026-12-31", f"{MARKER} current contract member 001", observed_at),
            ("hiref-synthetic-002", "project-synthetic-beacon", "2027-01-01", "2027-12-31", f"{MARKER} registered renewal member 001", observed_at),
            ("hiref-synthetic-003", "project-synthetic-atlas", "2025-01-01", "2026-09-30", f"{MARKER} expiring contract member 002", observed_at),
            ("hiref-synthetic-004", "project-synthetic-beacon", "2026-08-01", "2026-11-30", f"{MARKER} free slot", observed_at),
        ],
    )
    connection.execute(
        """
        UPDATE employees
        SET current_hiref = 'hiref-synthetic-001', next_hiref = 'hiref-synthetic-002'
        WHERE id = 'member-synthetic-001'
        """
    )
    connection.execute(
        """
        UPDATE employees
        SET current_hiref = 'hiref-synthetic-003', next_hiref = ''
        WHERE id = 'member-synthetic-002'
        """
    )
    connection.execute(
        """
        INSERT INTO staffing_placeholders
            (placeholder_id, display_name, source_system, hiref_id,
             linked_employee_id, resource_type, status, notes, created_at)
        VALUES (?, ?, 'resource_portal', '', NULL, 'STFTE', 'planned', ?, ?)
        """,
        ["placeholder-synthetic-001", "Synthetic Backfill", f"{MARKER} open placeholder", observed_at],
    )

    # Legacy assignments mirror the versioned monthly allocations exactly:
    # member 001 = 0.5, member 002 = 0.0 (no row), member 003 = 0.6 + 0.6.
    # The legacy load view therefore agrees with the canonical capacity data.
    connection.executemany(
        """
        INSERT INTO assignments
            (employee_id, project_id, role, allocation, start_date, end_date, status, created_at)
        VALUES (?, ?, ?, ?, '2026-01-01', NULL, 'active', ?)
        """,
        [
            ("member-synthetic-001", PROJECT_ID, "delivery_manager", 0.5, observed_at),
            ("member-synthetic-003", PROJECT_ID, "analyst", 0.6, observed_at),
            ("member-synthetic-003", BEACON_PROJECT_ID, "analyst", 0.6, observed_at),
        ],
    )


def _clear(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        UPDATE employees
        SET resource_type = '', billing_end_date = '', current_hiref = '',
            next_hiref = '', wd_id = ''
        WHERE id IN ('member-synthetic-001', 'member-synthetic-002', 'member-synthetic-003')
        """
    )
    connection.execute("DELETE FROM hiref WHERE id LIKE 'hiref-synthetic-%'")
    connection.execute(
        "DELETE FROM staffing_placeholders WHERE placeholder_id = 'placeholder-synthetic-001'"
    )
    connection.execute("DELETE FROM jira_issue_events WHERE board_id = ? AND source_id = ?", [BOARD_ID, SOURCE_ID])
    connection.execute(
        "DELETE FROM source_evidence_published_items WHERE first_published_run_id IN (?, ?)",
        [HISTORY_RUN, LINKS_RUN],
    )
    connection.execute(
        "DELETE FROM source_evidence_cursors WHERE published_run_id IN (?, ?)",
        [HISTORY_RUN, LINKS_RUN],
    )
    connection.execute("DELETE FROM source_evidence_runs WHERE run_id IN (?, ?)", [HISTORY_RUN, LINKS_RUN])
    for table in (
        "jira_health_snapshots",
        "jira_sprints",
        "jira_issues",
        "jira_stream_versions",
    ):
        connection.execute(f'DELETE FROM "{table}" WHERE board_id = ?', [BOARD_ID])
        connection.execute(f'DELETE FROM "{table}" WHERE board_id = ?', [BEACON_BOARD_ID])
    connection.execute(
        "DELETE FROM confluence_status_snapshots WHERE board_id IN (?, ?)",
        [BOARD_ID, BEACON_BOARD_ID],
    )
    connection.execute(
        "DELETE FROM action_items WHERE id = 1 OR title LIKE 'SYNTHETIC_DATASET_V1%'"
    )
    connection.execute(
        "DELETE FROM assignments WHERE employee_id IN ('member-synthetic-001', 'member-synthetic-003')",
    )


def main() -> None:
    connection = sqlite3.connect(settings.database_path)
    try:
        connection.execute("BEGIN IMMEDIATE")
        _clear(connection)
        _seed(connection)
        connection.commit()
    finally:
        connection.close()
    print(f"Seeded deterministic synthetic evidence for board {BOARD_ID} at {_now()}")


if __name__ == "__main__":
    main()
