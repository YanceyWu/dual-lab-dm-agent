from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone

from typer.testing import CliRunner

from pm_agent.cli import app as app_module
from pm_agent.dashboard import server as dashboard_server
from pm_agent.database.bootstrap import main as init_db
from pm_agent.use_cases import use_case_executor
from pm_agent.use_cases.service import UseCaseRequest


def _seed_execution_review(db_path) -> None:
    init_db(quiet=True)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with sqlite3.connect(db_path) as connection:
        connection.execute("INSERT INTO projects(id, name, status) VALUES ('project-review-1', 'Synthetic', 'active')")
        connection.execute(
            """
            INSERT INTO execution_derivation_runs
                (derivation_run_id, project_id, board_id, rule_version, input_fingerprint,
                 completeness_state, freshness_state, started_at, finished_at)
            VALUES ('review-run-1', 'project-review-1', 'board-review-1', 'execution-foundation-v1',
                    'synthetic-review-fingerprint', 'complete', 'fresh', ?, ?)
            """,
            [now, now],
        )
        rows = [
            ('fact-sprint', 'sprint', 'sprint-review-1', 'sprint_scope_change', None, 'unavailable'),
            ('fact-release', 'release', 'release-review-1', 'release_scope_count', {'total': 2, 'done': 1}, 'known'),
            ('fact-milestone', 'milestone', 'milestone-review-1', 'milestone_adherence', 'overdue', 'known'),
        ]
        for fact_id, kind, subject_id, fact_key, value, state in rows:
            connection.execute(
                """
                INSERT INTO execution_facts
                    (fact_id, derivation_run_id, project_id, subject_kind, subject_id,
                     fact_key, value_json, value_state, freshness_state, evidence_json)
                VALUES (?, 'review-run-1', 'project-review-1', ?, ?, ?, ?, ?, 'fresh', '{}')
                """,
                [fact_id, kind, subject_id, fact_key, json.dumps(value), state],
            )


def test_execution_review_projects_separate_layers_and_evidence(isolated_db) -> None:
    _seed_execution_review(isolated_db)
    result = use_case_executor.execute(
        UseCaseRequest(
            use_case_id='delivery-execution-review',
            parameters={'project_id': 'project-review-1'},
        )
    )
    assert result.status == 'success'
    assert len(result.data['sprint_execution']) == 1
    assert len(result.data['release_milestone']) == 2
    assert result.recommendations == []
    assert {signal.signal_type for signal in result.signals} == {
        'execution_evidence_limited', 'milestone_schedule_exception',
    }
    assert {item['coverage'] for item in result.evidence} == {'complete'}


def test_execution_review_validates_scope_and_generic_interfaces(isolated_db) -> None:
    _seed_execution_review(isolated_db)
    invalid = use_case_executor.execute(
        UseCaseRequest(
            use_case_id='delivery-execution-review',
            parameters={'project_id': 'project-review-1', 'layer': 'sprint', 'subject_kind': 'release'},
        )
    )
    assert invalid.status == 'invalid'
    assert invalid.warnings == [{'code': 'EXECUTION_SUBJECT_LAYER_INVALID'}]
    cli = CliRunner().invoke(
        app_module.app,
        ['tool', 'query', 'delivery-execution-review', '--project', 'project-review-1', '--param', 'layer=release_milestone'],
    )
    dashboard = dashboard_server.app.test_client().post(
        '/api/tool/query/delivery-execution-review',
        json={'parameters': {'project_id': 'project-review-1', 'layer': 'release_milestone'}},
    )
    assert cli.exit_code == 0, cli.output
    assert dashboard.status_code == 200
    assert json.loads(cli.output)['data'] == dashboard.get_json()['data']


def test_execution_review_picks_newest_run_by_creation_order_within_same_second(
    isolated_db,
) -> None:
    """A later-created derivation run must win even when its UUID sorts first."""
    init_db(quiet=True)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with sqlite3.connect(isolated_db) as connection:
        connection.execute("INSERT INTO projects(id, name, status) VALUES ('project-review-2', 'Synthetic', 'active')")
        for run_id in ("zzz-run-old", "aaa-run-new"):
            connection.execute(
                """
                INSERT INTO execution_derivation_runs
                    (derivation_run_id, project_id, board_id, rule_version, input_fingerprint,
                     completeness_state, freshness_state, started_at, finished_at)
                VALUES (?, 'project-review-2', 'board-review-2', 'execution-foundation-v1',
                        ?, 'complete', 'fresh', ?, ?)
                """,
                [run_id, f"synthetic-{run_id}", now, now],
            )
        connection.execute(
            """
            INSERT INTO execution_facts
                (fact_id, derivation_run_id, project_id, subject_kind, subject_id,
                 fact_key, value_json, value_state, freshness_state, evidence_json)
            VALUES ('fact-new', 'aaa-run-new', 'project-review-2', 'milestone', 'milestone-new',
                    'milestone_adherence', '"overdue"', 'known', 'fresh', '{}')
            """
        )
    result = use_case_executor.execute(
        UseCaseRequest(
            use_case_id='delivery-execution-review',
            parameters={'project_id': 'project-review-2'},
        )
    )
    assert result.status == 'success'
    assert [item['subject']['id'] for item in result.data['release_milestone']] == ['milestone-new']


def test_execution_review_non_known_value_is_contract_compliant(isolated_db) -> None:
    """A non-known fact value must be None in typed output while data keeps it."""
    init_db(quiet=True)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with sqlite3.connect(isolated_db) as connection:
        connection.execute("INSERT INTO projects(id, name, status) VALUES ('project-review-3', 'Synthetic', 'active')")
        connection.execute(
            """
            INSERT INTO execution_derivation_runs
                (derivation_run_id, project_id, board_id, rule_version, input_fingerprint,
                 completeness_state, freshness_state, started_at, finished_at)
            VALUES ('review-run-3', 'project-review-3', 'board-review-3', 'execution-foundation-v1',
                    'synthetic-review-fingerprint-3', 'complete', 'fresh', ?, ?)
            """,
            [now, now],
        )
        connection.execute(
            """
            INSERT INTO execution_facts
                (fact_id, derivation_run_id, project_id, subject_kind, subject_id,
                 fact_key, value_json, value_state, freshness_state, evidence_json)
            VALUES ('fact-target', 'review-run-3', 'project-review-3', 'release', 'release-review-3',
                    'release_target_date_change',
                    '{"first": "2026-08-01", "latest": "2026-08-01"}', 'unknown', 'fresh', '{}')
            """
        )
    result = use_case_executor.execute(
        UseCaseRequest(
            use_case_id='delivery-execution-review',
            parameters={'project_id': 'project-review-3'},
        )
    )
    assert result.status == 'success'
    unknown = [fact for fact in result.facts if fact.value_state == 'unknown']
    assert unknown
    assert all(fact.value is None for fact in unknown)
    assert result.data['release_milestone'][0]['value'] == {
        'first': '2026-08-01',
        'latest': '2026-08-01',
    }
