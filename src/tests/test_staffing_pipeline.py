from __future__ import annotations

import sqlite3
from datetime import date

import pytest
from typer.testing import CliRunner

from pm_agent.cli import app as app_module
from pm_agent.database.bootstrap import main as init_db
from pm_agent.use_cases.staffing import StaffingDemand, StaffingProposalService, assess_feasibility, staffing_read_model


def _seed_staffing_facts(db_path) -> None:
    init_db(quiet=True)
    con = sqlite3.connect(db_path)
    try:
        con.execute(
            "INSERT INTO plan_versions (plan_version_id, version_name, version_status) VALUES ('plan-2026-08', 'Plan', 'active')"
        )
        con.execute(
            "INSERT INTO projects (id, name, status, priority) VALUES ('project-atlas-990001', 'Project Atlas', 'active', 1)"
        )
        con.executemany(
            """
            INSERT INTO employees (id, wd_id, name, status, resource_type, skills, current_hiref)
            VALUES (?, ?, ?, 'active', ?, ?, ?)
            """,
            [
                ('990101', '990101', 'Alex Example', 'LTFTE', '{"python": 0.9}', ''),
                ('990102', '990102', 'Blair Example', 'LTFTE', '{"python": 0.8}', ''),
                ('990103', '990103', 'Casey Example', 'LTFTE', '{"react": 0.9}', ''),
                ('990104', '990104', 'Drew Example', 'STFTE', '{"python": 0.9}', 'HIREF-990104'),
            ],
        )
        con.execute(
            """INSERT INTO hiref (id, project, request_type, start_date, end_date)
               VALUES ('HIREF-990104', 'Project Atlas', 'extend', '2026-01-01', '2026-08-15')"""
        )
        con.executemany(
            """
            INSERT INTO monthly_allocations (employee_id, project_id, year, month, allocation, plan_version_id)
            VALUES (?, 'project-atlas-990001', 2026, 8, ?, 'plan-2026-08')
            """,
            [('990101', 0.6), ('990102', 0.8), ('990103', 0.1), ('990104', 0.0)],
        )
        con.commit()
    finally:
        con.close()


def _demand() -> StaffingDemand:
    return StaffingDemand(
        project_id='project-atlas-990001', start_period='2026-08', end_period='2026-08',
        effort=0.6, role='developer', required_skills=['python'], minimum_allocation=0.2,
        maximum_people=2, splittable=True, plan_version_id='plan-2026-08',
    )


def test_period_aware_staffing_read_model_distinguishes_contract_and_plan(isolated_db) -> None:
    _seed_staffing_facts(isolated_db)

    model = staffing_read_model(_demand())

    assert model['periods'] == [{'year': 2026, 'month': 8}]
    assert model['plan_version']['plan_version_id'] == 'plan-2026-08'
    alex = next(member for member in model['members'] if member['member_id'] == '990101')
    assert alex['periods']['2026-08']['load'] == 0.6
    drew = next(member for member in model['members'] if member['member_id'] == '990104')
    assert drew['periods']['2026-08']['contract']['end_date'] == '2026-08-15'


def test_feasibility_accepts_capacity_and_rejects_skill_and_contract_gaps(isolated_db) -> None:
    _seed_staffing_facts(isolated_db)

    result = assess_feasibility(_demand())
    candidates = {candidate['member_id']: candidate for candidate in result['candidates']}

    assert result['feasible'] is True
    assert result['selections'] == [
        {'member_id': '990101', 'name': 'Alex Example', 'allocation': 0.4},
        {'member_id': '990102', 'name': 'Blair Example', 'allocation': 0.2},
    ]
    assert candidates['990103']['reasons'] == ['missing_required_skills']
    assert candidates['990104']['reasons'] == ['contract_not_covered']


def test_proposal_preview_confirm_is_atomic_and_idempotent(isolated_db) -> None:
    _seed_staffing_facts(isolated_db)
    service = StaffingProposalService()

    proposed = service.propose(_demand())
    preview = service.preview(proposed['proposal_id'])
    confirmed = service.confirm(proposed['proposal_id'], proposed['confirmation_token'])
    repeated = service.confirm(proposed['proposal_id'], proposed['confirmation_token'])

    assert proposed['status'] == 'proposed'
    assert preview['status'] == 'proposed'
    assert confirmed['status'] == 'confirmed'
    assert repeated == {**confirmed, 'idempotent': True}
    con = sqlite3.connect(isolated_db)
    try:
        planned = con.execute("SELECT COUNT(*) FROM assignments WHERE status='planned'").fetchone()[0]
        decisions = con.execute("SELECT COUNT(*) FROM decision_log WHERE type='staffing_proposal'").fetchone()[0]
        proposal = con.execute("SELECT status FROM staffing_proposals WHERE proposal_id=?", [proposed['proposal_id']]).fetchone()[0]
    finally:
        con.close()
    assert (planned, decisions, proposal) == (2, 1, 'confirmed')


def test_confirmation_rejects_changed_capacity_without_domain_write(isolated_db) -> None:
    _seed_staffing_facts(isolated_db)
    service = StaffingProposalService()
    proposed = service.propose(_demand())
    con = sqlite3.connect(isolated_db)
    try:
        con.execute(
            """INSERT INTO monthly_allocations (employee_id, project_id, year, month, allocation, plan_version_id)
               VALUES ('990101', 'project-atlas-990001', 2026, 8, 0.4, 'plan-2026-08')"""
        )
        con.commit()
    finally:
        con.close()

    result = service.confirm(proposed['proposal_id'], proposed['confirmation_token'])

    assert result['status'] == 'invalid'
    con = sqlite3.connect(isolated_db)
    try:
        planned = con.execute("SELECT COUNT(*) FROM assignments WHERE status='planned'").fetchone()[0]
        decisions = con.execute("SELECT COUNT(*) FROM decision_log WHERE type='staffing_proposal'").fetchone()[0]
    finally:
        con.close()
    assert (planned, decisions) == (0, 0)


def test_cancel_and_reject_leave_domain_records_unchanged(isolated_db) -> None:
    _seed_staffing_facts(isolated_db)
    service = StaffingProposalService()
    cancelled = service.propose(_demand())
    rejected = service.propose(_demand())

    assert service.cancel(cancelled['proposal_id'], 'no longer needed')['status'] == 'cancelled'
    assert service.reject(rejected['proposal_id'], 'manager declined')['status'] == 'rejected'
    con = sqlite3.connect(isolated_db)
    try:
        planned = con.execute("SELECT COUNT(*) FROM assignments WHERE status='planned'").fetchone()[0]
        statuses = con.execute("SELECT status FROM staffing_proposals ORDER BY proposal_id").fetchall()
    finally:
        con.close()
    assert planned == 0
    assert {status[0] for status in statuses} == {'cancelled', 'rejected'}


def test_expired_proposal_cannot_write(isolated_db) -> None:
    _seed_staffing_facts(isolated_db)
    service = StaffingProposalService()
    proposed = service.propose(_demand())
    con = sqlite3.connect(isolated_db)
    try:
        con.execute("UPDATE staffing_proposals SET expires_at='2000-01-01T00:00:00' WHERE proposal_id=?", [proposed['proposal_id']])
        con.commit()
    finally:
        con.close()

    result = service.confirm(proposed['proposal_id'], proposed['confirmation_token'])

    assert result['status'] == 'invalid'
    con = sqlite3.connect(isolated_db)
    try:
        planned = con.execute("SELECT COUNT(*) FROM assignments WHERE status='planned'").fetchone()[0]
        status = con.execute("SELECT status FROM staffing_proposals WHERE proposal_id=?", [proposed['proposal_id']]).fetchone()[0]
    finally:
        con.close()
    assert (planned, status) == (0, 'expired')


@pytest.mark.parametrize(
    ('overrides', 'expected_feasible', 'expected_reason'),
    [
        ({}, True, None),
        ({'effort': 0.4, 'maximum_people': 1, 'splittable': False}, True, None),
        ({'effort': 0.7}, False, None),
        ({'effort': 0.6, 'splittable': False}, False, None),
        ({'required_skills': ['react']}, True, None),
        ({'required_skills': ['go']}, False, 'missing_required_skills'),
        ({'minimum_allocation': 0.3}, False, 'insufficient_capacity'),
        ({'maximum_people': 1}, False, None),
        ({'effort': 1.1}, False, None),
        ({'priority': 'high'}, True, None),
        ({'role': 'architect'}, True, None),
        ({'required_skills': ['Python']}, True, None),
        ({'start_period': '2026-09', 'end_period': '2026-09'}, True, None),
        ({'plan_version_id': None}, True, None),
    ],
)
def test_golden_staffing_feasibility_matrix(isolated_db, overrides, expected_feasible, expected_reason) -> None:
    _seed_staffing_facts(isolated_db)
    demand = _demand().model_copy(update=overrides)

    result = assess_feasibility(demand)

    assert result['feasible'] is expected_feasible
    assert result['rule_version'] == 'staffing-feasibility-v1'
    assert {item['state'] for item in result['source_states']} == {'never_synced'}
    if expected_reason:
        assert expected_reason in {reason for candidate in result['candidates'] for reason in candidate['reasons']}


def test_golden_invalid_period_is_rejected(isolated_db) -> None:
    _seed_staffing_facts(isolated_db)
    with pytest.raises(ValueError, match='end_period'):
        assess_feasibility(_demand().model_copy(update={'start_period': '2026-09', 'end_period': '2026-08'}))


def test_golden_inactive_member_is_not_eligible(isolated_db) -> None:
    _seed_staffing_facts(isolated_db)
    con = sqlite3.connect(isolated_db)
    try:
        con.execute("UPDATE employees SET status='on_leave' WHERE id='990101'")
        con.commit()
    finally:
        con.close()

    result = assess_feasibility(_demand())
    assert '990101' not in {item['member_id'] for item in result['candidates']}


def test_manager_cli_assess_is_read_only_json(isolated_db) -> None:
    _seed_staffing_facts(isolated_db)
    result = CliRunner().invoke(
        app_module.app,
        ['staffing', 'assess', '--project', 'project-atlas-990001', '--start', '2026-08', '--end', '2026-08',
         '--effort', '0.6', '--skills', 'python', '--maximum-people', '2', '--plan-version', 'plan-2026-08'],
    )
    assert result.exit_code == 0, result.output
    assert '"feasible": true' in result.output
