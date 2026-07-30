from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from pm_agent.database import execution, source_evidence
from pm_agent.database.bootstrap import main as init_db
from pm_agent.use_cases.execution_foundation import ExecutionFoundationService


def _seed_board(db_path: Path) -> None:
    init_db(quiet=True)
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            "INSERT INTO projects(id, name, status) VALUES ('project-synthetic-001', 'Synthetic', 'active')"
        )
        connection.execute(
            """
            INSERT INTO jira_board_configs(id, name, project_key, base_jql, pm_project_id, active)
            VALUES ('board-synthetic', 'Synthetic Board', 'SYN', 'project = SYN', 'project-synthetic-001', 1)
            """
        )
        connection.execute(
            """
            INSERT INTO jira_stream_versions(id, board_id, project_key, name, release_date, status)
            VALUES ('release-1', 'board-synthetic', 'SYN', 'Synthetic Release', '2026-08-15', 'unreleased')
            """
        )
        connection.executemany(
            """
            INSERT INTO jira_issues(id, board_id, project_key, status_category, story_points)
            VALUES (?, 'board-synthetic', 'SYN', ?, ?)
            """,
            [('SYN-1', 'done', 3.0), ('SYN-2', 'todo', 5.0)],
        )


def _event(issue_ref: str, field_key: str, value: object, event_ref: str) -> source_evidence.IssueEvent:
    return source_evidence.IssueEvent(
        issue_ref=issue_ref,
        source_event_ref=event_ref,
        event_type='issue_observed',
        field_key=field_key,
        from_value='',
        to_value=value,
        source_updated_at='2026-07-30T01:00:00+00:00',
        observed_at='2026-07-30T01:05:00+00:00',
    )


def _publish_evidence(
    db_path: Path,
    *,
    authoritative: bool,
) -> None:
    history = source_evidence.start_run(
        'jira-evidence-board-synthetic', 'board-synthetic', 'jira_issue_history',
        overlap_seconds=300, db_path=db_path, run_id=f'history-{authoritative}',
    )
    events = [
            _event('SYN-1', 'status_category', 'done', 'syn1-category'),
            _event('SYN-1', 'fix_versions', ['release-1'], 'syn1-release'),
            _event('SYN-2', 'status_category', 'todo', 'syn2-category'),
            _event('SYN-2', 'fix_versions', ['release-1'], 'syn2-release'),
    ]
    source_evidence.stage_issue_events(
        history,
        events,
        manifest_issue_refs=['SYN-1', 'SYN-2'], db_path=db_path,
    )
    source_evidence.finish_staging(
        history, coverage_status='complete', pages_received=1, pages_expected=1,
        proposed_cursor_time='2026-07-30T01:00:00+00:00', proposed_cursor_ref='SYN-2',
        authoritative_manifest=authoritative, db_path=db_path,
    )
    source_evidence.publish_run(history, db_path=db_path)
    links = source_evidence.start_run(
        'jira-evidence-board-synthetic', 'board-synthetic', 'jira_issue_links',
        overlap_seconds=300, db_path=db_path, run_id=f'links-{authoritative}',
    )
    source_evidence.stage_issue_links(
        links,
        [source_evidence.IssueLink(
            source_link_ref='link-1', issue_ref='SYN-1', related_issue_ref='SYN-2',
            link_type='Blocks', direction='outward', observation_state='active',
            source_updated_at='2026-07-30T01:00:00+00:00',
            observed_at='2026-07-30T01:05:00+00:00',
        )],
        manifest_link_refs=['link-1'], db_path=db_path,
    )
    source_evidence.finish_staging(
        links, coverage_status='complete', pages_received=1, pages_expected=1,
        proposed_cursor_time='2026-07-30T01:00:00+00:00', proposed_cursor_ref='SYN-2',
        authoritative_manifest=authoritative, db_path=db_path,
    )
    source_evidence.publish_run(links, db_path=db_path)


def _milestone_payload(*, observed_at: str = '2026-07-30T02:00:00+00:00') -> dict:
    return {
        'milestones': [{
            'milestone_id': 'milestone-synthetic-1',
            'project_id': 'project-synthetic-001',
            'milestone_type': 'release_gate',
            'criticality': 'high',
            'lifecycle_state': 'in_progress',
            'planned_date': '2026-08-10',
            'source_target_date': '2026-08-12',
            'forecast_date': '',
            'actual_date': '',
            'authority': 'approved_local_import',
            'completeness_state': 'known',
            'observed_at': observed_at,
            'schema_version': 'milestone-import-v1',
        }],
    }


def test_bootstrap_adds_b2_canonical_storage(isolated_db: Path) -> None:
    init_db(quiet=True)
    expected = {
        'execution_work_items', 'execution_source_identities', 'execution_work_item_observations', 'execution_sprints',
        'execution_release_commitments', 'execution_release_observations', 'execution_scope_memberships',
        'execution_milestones', 'execution_milestone_observations',
        'execution_milestone_release_links', 'execution_dependencies',
        'execution_dependency_observations', 'execution_derivation_runs',
        'execution_derivation_inputs', 'execution_facts', 'milestone_import_operations',
    }
    with sqlite3.connect(isolated_db) as connection:
        names = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert expected <= names


def test_derivation_projects_authoritative_evidence_and_is_idempotent(isolated_db: Path) -> None:
    _seed_board(isolated_db)
    _publish_evidence(isolated_db, authoritative=True)
    first = execution.derive_board('board-synthetic', db_path=isolated_db)
    repeated = execution.derive_board('board-synthetic', db_path=isolated_db)
    assert first['status'] == 'derived'
    assert repeated == {**first, 'idempotent': True}
    with sqlite3.connect(isolated_db) as connection:
        assert connection.execute("SELECT COUNT(*) FROM execution_work_items").fetchone()[0] == 2
        assert connection.execute("SELECT COUNT(*) FROM execution_source_identities").fetchone()[0] == 2
        assert connection.execute("SELECT COUNT(*) FROM execution_scope_memberships").fetchone()[0] == 2
        assert connection.execute("SELECT COUNT(*) FROM execution_dependencies").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM execution_release_observations").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM execution_dependency_observations").fetchone()[0] == 1
        facts = connection.execute(
            "SELECT fact_key, value_state, value_json FROM execution_facts ORDER BY fact_key"
        ).fetchall()
    assert facts == [
        ('dependency_readiness', 'known', '{"state":"active"}'),
        ('release_scope_count', 'known', '{"done":1,"total":2}'),
        ('release_story_point_coverage', 'known', '{"done":3.0,"total":8.0}'),
        ('release_target_date_change', 'unknown', '{"first":"2026-08-15","latest":"2026-08-15"}'),
    ]


def test_non_authoritative_evidence_cannot_produce_known_scope_fact(isolated_db: Path) -> None:
    _seed_board(isolated_db)
    _publish_evidence(isolated_db, authoritative=False)
    result = execution.derive_board('board-synthetic', db_path=isolated_db)
    with sqlite3.connect(isolated_db) as connection:
        run = connection.execute(
            "SELECT completeness_state, warning_codes_json FROM execution_derivation_runs WHERE derivation_run_id = ?",
            [result['derivation_run_id']],
        ).fetchone()
        facts = connection.execute("SELECT value_state FROM execution_facts ORDER BY fact_key").fetchall()
    assert run == ('partial', '["SCOPE_MANIFEST_NOT_AUTHORITATIVE"]')
    assert facts == [('known',), ('unavailable',), ('unavailable',), ('unknown',)]


def test_authoritative_manifest_closes_missing_scope_memberships(isolated_db: Path) -> None:
    _seed_board(isolated_db)
    _publish_evidence(isolated_db, authoritative=True)
    execution.derive_board('board-synthetic', db_path=isolated_db)
    history = source_evidence.start_run(
        'jira-evidence-board-synthetic', 'board-synthetic', 'jira_issue_history',
        overlap_seconds=300, db_path=isolated_db, run_id='history-closure',
    )
    source_evidence.stage_issue_events(
        history, [_event('SYN-1', 'status_category', 'done', 'syn1-closure')],
        manifest_issue_refs=['SYN-1'], db_path=isolated_db,
    )
    source_evidence.finish_staging(
        history, coverage_status='complete', pages_received=1, pages_expected=1,
        proposed_cursor_time='2026-07-31T01:00:00+00:00', proposed_cursor_ref='SYN-1',
        authoritative_manifest=True, db_path=isolated_db,
    )
    source_evidence.publish_run(history, db_path=isolated_db)
    execution.derive_board('board-synthetic', db_path=isolated_db)
    with sqlite3.connect(isolated_db) as connection:
        state = connection.execute(
            """
            SELECT sm.state FROM execution_scope_memberships sm
            JOIN execution_work_items wi ON wi.work_item_id = sm.work_item_id
            WHERE wi.source_ref = 'SYN-2'
            """
        ).fetchone()[0]
    assert state == 'closed'


def test_legacy_snapshot_change_creates_a_new_derivation_and_target_history(isolated_db: Path) -> None:
    _seed_board(isolated_db)
    _publish_evidence(isolated_db, authoritative=True)
    first = execution.derive_board('board-synthetic', db_path=isolated_db)
    with sqlite3.connect(isolated_db) as connection:
        connection.execute(
            "UPDATE jira_stream_versions SET release_date = '2026-08-20', synced_at = '2026-07-31T02:00:00+00:00'"
        )
    second = execution.derive_board('board-synthetic', db_path=isolated_db)
    assert second['idempotent'] is False
    assert second['derivation_run_id'] != first['derivation_run_id']
    with sqlite3.connect(isolated_db) as connection:
        fact = connection.execute(
            """
            SELECT value_state, value_json FROM execution_facts
            WHERE derivation_run_id = ? AND fact_key = 'release_target_date_change'
            """,
            [second['derivation_run_id']],
        ).fetchone()
    assert fact == ('known', '{"first":"2026-08-15","latest":"2026-08-20"}')


def test_authoritative_scope_movement_closes_prior_release_and_tracks_sprint(isolated_db: Path) -> None:
    _seed_board(isolated_db)
    with sqlite3.connect(isolated_db) as connection:
        connection.execute(
            """
            INSERT INTO jira_stream_versions(id, board_id, project_key, name, release_date, status)
            VALUES ('release-2', 'board-synthetic', 'SYN', 'Synthetic Release 2', '2026-09-15', 'unreleased')
            """
        )
        connection.execute(
            """
            INSERT INTO jira_sprints(id, board_id, name, state)
            VALUES ('sprint-1', 'board-synthetic', 'Synthetic Sprint', 'active')
            """
        )
    _publish_evidence(isolated_db, authoritative=True)
    execution.derive_board('board-synthetic', db_path=isolated_db)
    history = source_evidence.start_run(
        'jira-evidence-board-synthetic', 'board-synthetic', 'jira_issue_history',
        overlap_seconds=300, db_path=isolated_db, run_id='history-z-scope-move',
    )
    source_evidence.stage_issue_events(
        history,
        [
            _event('SYN-1', 'fix_versions', ['release-2'], 'syn1-release-move'),
            _event('SYN-1', 'sprint', 'sprint-1', 'syn1-sprint'),
        ],
        manifest_issue_refs=['SYN-1', 'SYN-2'], db_path=isolated_db,
    )
    source_evidence.finish_staging(
        history, coverage_status='complete', pages_received=1, pages_expected=1,
        proposed_cursor_time='2026-07-31T02:00:00+00:00', proposed_cursor_ref='SYN-2',
        authoritative_manifest=True, db_path=isolated_db,
    )
    source_evidence.publish_run(history, db_path=isolated_db)
    execution.derive_board('board-synthetic', db_path=isolated_db)
    with sqlite3.connect(isolated_db) as connection:
        memberships = connection.execute(
            """
            SELECT sm.scope_kind, rc.source_ref, sm.state
            FROM execution_scope_memberships sm
            JOIN execution_work_items wi ON wi.work_item_id = sm.work_item_id
            LEFT JOIN execution_release_commitments rc ON rc.release_id = sm.scope_id
            WHERE wi.source_ref = 'SYN-1'
            ORDER BY sm.scope_kind, rc.source_ref
            """
        ).fetchall()
    assert memberships == [
        ('release', 'release-1', 'closed'),
        ('release', 'release-2', 'open'),
        ('sprint', None, 'open'),
    ]


def test_authoritative_link_removal_inactivates_dependency(isolated_db: Path) -> None:
    _seed_board(isolated_db)
    _publish_evidence(isolated_db, authoritative=True)
    execution.derive_board('board-synthetic', db_path=isolated_db)
    links = source_evidence.start_run(
        'jira-evidence-board-synthetic', 'board-synthetic', 'jira_issue_links',
        overlap_seconds=300, db_path=isolated_db, run_id='links-z-removed',
    )
    source_evidence.stage_issue_links(links, [], manifest_link_refs=[], db_path=isolated_db)
    source_evidence.finish_staging(
        links, coverage_status='complete', pages_received=1, pages_expected=1,
        proposed_cursor_time='2026-07-31T03:00:00+00:00', proposed_cursor_ref='link-1',
        authoritative_manifest=True, db_path=isolated_db,
    )
    source_evidence.publish_run(links, db_path=isolated_db)
    derived = execution.derive_board('board-synthetic', db_path=isolated_db)
    with sqlite3.connect(isolated_db) as connection:
        state = connection.execute("SELECT state FROM execution_dependencies").fetchone()[0]
        facts = connection.execute(
            "SELECT COUNT(*) FROM execution_facts WHERE derivation_run_id = ? AND fact_key = 'dependency_readiness'",
            [derived['derivation_run_id']],
        ).fetchone()[0]
    assert state == 'inactive'
    assert facts == 0


def test_milestone_import_preview_confirm_is_atomic_and_preserves_first_target(isolated_db: Path) -> None:
    _seed_board(isolated_db)
    service = ExecutionFoundationService()
    preview = service.preview_milestone_import(_milestone_payload(), db_path=isolated_db)
    assert preview['status'] == 'proposed'
    with sqlite3.connect(isolated_db) as connection:
        assert connection.execute("SELECT COUNT(*) FROM execution_milestones").fetchone()[0] == 0
    confirmed = service.confirm_milestone_import(
        preview['operation_id'], preview['confirmation_token'], db_path=isolated_db,
    )
    repeated = service.confirm_milestone_import(
        preview['operation_id'], preview['confirmation_token'], db_path=isolated_db,
    )
    assert confirmed['status'] == 'confirmed'
    assert repeated == {**confirmed, 'idempotent': True}
    changed = _milestone_payload(observed_at='2026-07-30T03:00:00+00:00')
    changed['milestones'][0]['source_target_date'] = '2026-08-14'
    follow_up = service.preview_milestone_import(changed, db_path=isolated_db)
    service.confirm_milestone_import(follow_up['operation_id'], follow_up['confirmation_token'], db_path=isolated_db)
    with sqlite3.connect(isolated_db) as connection:
        milestone = connection.execute(
            "SELECT source_target_date, first_observed_target_date FROM execution_milestones"
        ).fetchone()
        observations = connection.execute("SELECT COUNT(*) FROM execution_milestone_observations").fetchone()[0]
    assert milestone == ('2026-08-14', '2026-08-12')
    assert observations == 2


def test_milestone_preview_rejects_noop_and_confirm_rejects_stale_fingerprint(isolated_db: Path) -> None:
    _seed_board(isolated_db)
    service = ExecutionFoundationService()
    first = service.preview_milestone_import(_milestone_payload(), db_path=isolated_db)
    service.confirm_milestone_import(first['operation_id'], first['confirmation_token'], db_path=isolated_db)
    assert service.preview_milestone_import(_milestone_payload(), db_path=isolated_db) == {'status': 'no_op', 'changes': []}
    changed = _milestone_payload(observed_at='2026-07-30T03:00:00+00:00')
    changed['milestones'][0]['source_target_date'] = '2026-08-14'
    preview = service.preview_milestone_import(changed, db_path=isolated_db)
    with sqlite3.connect(isolated_db) as connection:
        connection.execute("UPDATE execution_milestones SET source_target_date = '2026-08-13'")
    rejected = service.confirm_milestone_import(preview['operation_id'], preview['confirmation_token'], db_path=isolated_db)
    assert rejected == {'status': 'rejected', 'operation_id': preview['operation_id'], 'reason': 'STALE_FINGERPRINT'}


def test_milestone_confirm_requires_valid_unexpired_one_time_token(isolated_db: Path) -> None:
    _seed_board(isolated_db)
    service = ExecutionFoundationService()
    preview = service.preview_milestone_import(_milestone_payload(), db_path=isolated_db)
    with pytest.raises(ValueError, match='Invalid confirmation token'):
        service.confirm_milestone_import(preview['operation_id'], 'wrong-token', db_path=isolated_db)
    with sqlite3.connect(isolated_db) as connection:
        connection.execute(
            "UPDATE milestone_import_operations SET expires_at = '2026-01-01T00:00:00+00:00'"
        )
    assert service.confirm_milestone_import(
        preview['operation_id'], preview['confirmation_token'], db_path=isolated_db,
    ) == {'status': 'expired', 'operation_id': preview['operation_id']}


def test_milestone_import_rejects_unpersisted_dependency_reference(isolated_db: Path) -> None:
    _seed_board(isolated_db)
    payload = _milestone_payload()
    payload['milestones'][0]['dependency_ids'] = ['dependency-synthetic-1']
    with pytest.raises(ValueError, match='unsupported fields'):
        ExecutionFoundationService().preview_milestone_import(payload, db_path=isolated_db)


def test_milestone_import_validates_and_persists_explicit_release_links(isolated_db: Path) -> None:
    _seed_board(isolated_db)
    _publish_evidence(isolated_db, authoritative=True)
    execution.derive_board('board-synthetic', db_path=isolated_db)
    with sqlite3.connect(isolated_db) as connection:
        release_id = connection.execute("SELECT release_id FROM execution_release_commitments").fetchone()[0]
    payload = _milestone_payload()
    payload['milestones'][0]['release_ids'] = [release_id]
    service = ExecutionFoundationService()
    preview = service.preview_milestone_import(payload, db_path=isolated_db)
    service.confirm_milestone_import(preview['operation_id'], preview['confirmation_token'], db_path=isolated_db)
    derived = execution.derive_board('board-synthetic', db_path=isolated_db)
    assert derived['idempotent'] is False
    with sqlite3.connect(isolated_db) as connection:
        assert connection.execute("SELECT milestone_id, release_id FROM execution_milestone_release_links").fetchone() == (
            'milestone-synthetic-1', release_id,
        )
        assert connection.execute(
            "SELECT value_json, value_state FROM execution_facts WHERE fact_key = 'milestone_adherence'"
        ).fetchone() == ('"on_track"', 'known')
