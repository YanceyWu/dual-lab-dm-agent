from __future__ import annotations

import sqlite3
import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from pm_agent.cli import app as app_module
from current_state_staffing_test_helpers import publish_current_state_staffing_from_legacy
from pm_agent.database import repository
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
            """INSERT INTO projects
               (id, name, status, priority, tech_stack)
               VALUES ('project-atlas-990001', 'Project Atlas', 'active', 1,
                       '["python", "react"]')"""
        )
        con.executemany(
            """
            INSERT INTO employees
                (id, wd_id, name, role, status, resource_type, current_hiref)
            VALUES (?, ?, ?, ?, 'active', ?, ?)
            """,
            [
                ('990101', '990101', 'Alex Example', 'Back-end Engineer', 'LTFTE', ''),
                ('990102', '990102', 'Blair Example', 'Front-end Engineer', 'LTFTE', ''),
                ('990103', '990103', 'Casey Example', 'Front-end Engineer', 'LTFTE', ''),
                ('990104', '990104', 'Drew Example', 'Back-end Engineer', 'STFTE', 'HIREF-990104'),
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
            [('990101', 0.6), ('990102', 0.8), ('990103', 0.9), ('990104', 0.0)],
        )
        con.commit()
    finally:
        con.close()
    _mark_staffing_sources_fresh()
    publish_current_state_staffing_from_legacy(
        Path(db_path),
        package_id="package-staffing-current-state-r1",
    )


def _mark_staffing_sources_fresh() -> None:
    for source_id in (
        "import-resource-portal",
        "import-hiref-report",
    ):
        run_id = repository.start_sync_run(source_id, triggered_by="synthetic-test")
        repository.finish_sync_run(run_id, status="success")


def _fail_source(db_path, source_id: str) -> None:
    with sqlite3.connect(db_path) as con:
        con.execute(
            "UPDATE sync_runs SET started_at='2000-01-01', finished_at='2000-01-01' "
            "WHERE source_id=?",
            [source_id],
        )
    run_id = repository.start_sync_run(source_id, triggered_by="synthetic-test")
    repository.fail_sync_run(run_id, "synthetic failure")


def _mark_current_state_publication_stale(db_path) -> None:
    with sqlite3.connect(db_path) as con:
        con.execute(
            """
            UPDATE current_state_staffing_publications
            SET published_at = '2000-01-01T00:00:00+00:00'
            WHERE is_current = 1
            """
        )
        con.commit()


def _mark_current_state_publication_partial(db_path) -> None:
    with sqlite3.connect(db_path) as con:
        row = con.execute(
            """
            SELECT report_json
            FROM current_state_staffing_publications
            WHERE is_current = 1
            LIMIT 1
            """
        ).fetchone()
        report = json.loads(row[0])
        report["coverage"]["assignment_manifest_state"] = "partial"
        report["coverage"]["missing_record_count"] = 1
        con.execute(
            """
            UPDATE current_state_staffing_publications
            SET report_json = ?
            WHERE is_current = 1
            """,
            [json.dumps(report)],
        )
        con.commit()


def _demand() -> StaffingDemand:
    return StaffingDemand(
        project_id='project-atlas-990001', start_period='2026-08', end_period='2026-08',
        effort=0.6, role='developer', minimum_allocation=0.2,
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


def test_feasibility_accepts_capacity_and_surfaces_hiref_context(isolated_db) -> None:
    _seed_staffing_facts(isolated_db)

    result = assess_feasibility(_demand())
    candidates = {candidate['member_id']: candidate for candidate in result['candidates']}

    assert result['feasible'] is True
    assert result['selections'] == [
        {'member_id': '990101', 'name': 'Alex Example', 'allocation': 0.4},
        {'member_id': '990102', 'name': 'Blair Example', 'allocation': 0.2},
    ]
    assert candidates['990103']['reasons'] == ['insufficient_capacity']
    assert candidates['990104']['reasons'] == []
    assert candidates['990104']['hiref_context']['status'] == 'partial_coverage'
    assert (
        candidates['990104']['hiref_context']['recommended_action']
        == 'submit_or_extend_hiref'
    )


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
            """
            UPDATE monthly_allocations
            SET allocation = allocation + 0.4
            WHERE employee_id = '990101'
              AND project_id = 'project-atlas-990001'
              AND year = 2026
              AND month = 8
              AND plan_version_id = 'plan-2026-08'
            """
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
        ({'minimum_allocation': 0.3}, False, 'insufficient_capacity'),
        ({'maximum_people': 1}, False, None),
        ({'effort': 1.1}, False, None),
        ({'priority': 'high'}, True, None),
        ({'role': 'architect'}, True, None),
        ({'start_period': '2026-09', 'end_period': '2026-09'}, True, None),
        ({'plan_version_id': None}, True, None),
    ],
)
def test_golden_staffing_feasibility_matrix(isolated_db, overrides, expected_feasible, expected_reason) -> None:
    _seed_staffing_facts(isolated_db)
    demand = _demand().model_copy(update=overrides)

    result = assess_feasibility(demand)

    assert result['feasible'] is expected_feasible
    assert result['rule_version'] == 'staffing-feasibility-v2'
    assert {item['state'] for item in result['source_states']} == {'fresh'}
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
         '--effort', '0.6', '--maximum-people', '2', '--plan-version', 'plan-2026-08'],
    )
    assert result.exit_code == 0, result.output
    assert '"feasible": true' in result.output


def test_manager_cli_rejects_retired_skills_option(isolated_db) -> None:
    _seed_staffing_facts(isolated_db)
    result = CliRunner().invoke(
        app_module.app,
        [
            'staffing', 'assess', '--project', 'project-atlas-990001', '--start', '2026-08',
            '--end', '2026-08', '--effort', '0.6', '--skills', 'python',
        ],
    )

    assert result.exit_code != 0
    assert "No such option: --skills" in result.output


def test_manager_cli_records_hiref_action_for_conditional_proposal(
    isolated_db,
) -> None:
    _seed_staffing_facts(isolated_db)
    with sqlite3.connect(isolated_db) as con:
        con.execute(
            """
            UPDATE monthly_allocations
            SET allocation = 0.95
            WHERE employee_id IN ('990101', '990102')
              AND project_id = 'project-atlas-990001'
              AND year = 2026
              AND month = 8
              AND plan_version_id = 'plan-2026-08'
            """
        )
        con.commit()

    result = CliRunner().invoke(
        app_module.app,
        [
            "staffing",
            "propose",
            "--project",
            "project-atlas-990001",
            "--start",
            "2026-08",
            "--end",
            "2026-08",
            "--effort",
            "0.4",
            "--minimum",
            "0.2",
            "--maximum-people",
            "1",
            "--plan-version",
            "plan-2026-08",
            "--acknowledge-hiref-actions",
            "--hiref-action-note",
            "Submit an extend HIREF before charge-code use.",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "proposed"
    assert (
        payload["preview"]["hiref_action_acknowledgement"]["note"]
        == "Submit an extend HIREF before charge-code use."
    )


def test_role_is_visible_reference_context_but_never_filters_or_ranks(isolated_db) -> None:
    _seed_staffing_facts(isolated_db)

    result = assess_feasibility(
        _demand().model_copy(update={"role": "architect"})
    )

    assert result["feasible"] is True
    assert result["decision_ready"] is True
    assert [item["member_id"] for item in result["selections"]] == [
        "990101",
        "990102",
    ]
    candidates = {item["member_id"]: item for item in result["candidates"]}
    assert candidates["990101"]["role"] == "Back-end Engineer"
    assert candidates["990102"]["role"] == "Front-end Engineer"
    assert candidates["990102"]["role_reference"] == {
        "requested_role": "architect",
        "member_role": "Front-end Engineer",
        "policy": "reference_only",
        "affects_eligibility": False,
        "affects_ranking": False,
    }
    assert candidates["990101"]["monthly_context"] == [
        {
            "period": "2026-08",
            "current_load": 0.6,
            "available_allocation": 0.4,
        }
    ]
    assert result["project_context"]["tech_stack"] == ["python", "react"]


def test_non_fresh_sources_allow_assessment_but_block_proposal_by_default(
    isolated_db,
) -> None:
    _seed_staffing_facts(isolated_db)
    _fail_source(isolated_db, "import-hiref-report")
    service = StaffingProposalService()

    assessment = assess_feasibility(_demand())
    proposed = service.propose(_demand())

    assert assessment["feasible"] is True
    assert assessment["decision_ready"] is False
    assert {
        (item.get("source_id"), item.get("state"))
        for item in assessment["safety_blockers"]
    } >= {("import-hiref-report", "unavailable")}
    assert proposed["status"] == "blocked"
    with sqlite3.connect(isolated_db) as con:
        assert con.execute("SELECT COUNT(*) FROM staffing_proposals").fetchone()[0] == 0


def test_retired_skills_source_is_not_registered_or_reported(isolated_db) -> None:
    _seed_staffing_facts(isolated_db)

    with pytest.raises(ValueError, match="not registered"):
        repository.start_sync_run(
            "import-skills-matrix",
            triggered_by="synthetic-test",
        )

    assessment = assess_feasibility(_demand())
    proposed = StaffingProposalService().propose(_demand())

    assert assessment["decision_ready"] is True
    assert {item["source_id"] for item in assessment["source_states"]} == {
        "current-state-staffing-publication",
        "import-hiref-report",
    }
    assert all(
        blocker.get("source_id") != "import-skills-matrix"
        for blocker in assessment["safety_blockers"]
    )
    assert proposed["status"] == "proposed"
    with sqlite3.connect(isolated_db) as con:
        source_ids = {
            row[0]
            for row in con.execute("SELECT id FROM data_sources").fetchall()
        }
    assert "import-skills-matrix" not in source_ids


def test_init_db_retires_preexisting_skills_source_without_breaking_history(
    isolated_db,
) -> None:
    init_db(quiet=True)
    with sqlite3.connect(isolated_db) as con:
        con.execute(
            """
            INSERT OR REPLACE INTO data_sources
                (id, source_type, source_name, ingestion_mode, refresh_sla_hours,
                 active, config_json, notes)
            VALUES
                ('import-skills-matrix', 'json', 'Skills Matrix Import', 'file', 720,
                 1, '{}', 'Legacy skills import')
            """
        )
        con.commit()

    run_id = repository.start_sync_run(
        "import-skills-matrix",
        triggered_by="synthetic-test",
    )
    repository.finish_sync_run(run_id, status="success")

    init_db(quiet=True)

    with sqlite3.connect(isolated_db) as con:
        row = con.execute(
            """
            SELECT source_name, active, notes
            FROM data_sources
            WHERE id = 'import-skills-matrix'
            """
        ).fetchone()

    assert row is not None
    assert row[0] == "Retired Skills Matrix Import"
    assert row[1] == 0
    assert "historical sync-run integrity" in row[2]


def test_dm_can_authorize_non_fresh_proposal_with_audited_reason(
    isolated_db,
) -> None:
    _seed_staffing_facts(isolated_db)
    _fail_source(isolated_db, "import-hiref-report")
    service = StaffingProposalService()

    proposed = service.propose(
        _demand(),
        allow_non_fresh=True,
        freshness_override_reason="DM reviewed the current local HIREF evidence.",
    )
    confirmed = service.confirm(
        proposed["proposal_id"],
        proposed["confirmation_token"],
    )

    assert proposed["status"] == "proposed"
    assert proposed["preview"]["freshness_override"]["authorized"] is True
    assert confirmed["status"] == "confirmed"
    with sqlite3.connect(isolated_db) as con:
        chosen = json.loads(
            con.execute(
                "SELECT chosen FROM decision_log WHERE id=?",
                [confirmed["decision_id"]],
            ).fetchone()[0]
        )
    safety = chosen["decision_safety"]
    assert safety["decision_fingerprint"] == proposed["preview"]["decision_fingerprint"]
    assert (
        safety["freshness_override"]["reason"]
        == "DM reviewed the current local HIREF evidence."
    )
    assert {
        item["state"] for item in safety["source_states"]
    } == {"fresh", "unavailable"}


def test_non_fresh_override_requires_both_flag_and_reason(isolated_db) -> None:
    _seed_staffing_facts(isolated_db)
    _mark_current_state_publication_stale(isolated_db)
    service = StaffingProposalService()

    flag_only = service.propose(_demand(), allow_non_fresh=True)
    reason_only = service.propose(
        _demand(),
        freshness_override_reason="Reviewed by the Delivery Manager.",
    )

    assert flag_only["status"] == reason_only["status"] == "blocked"


def test_partial_current_state_publication_blocks_proposal(isolated_db) -> None:
    _seed_staffing_facts(isolated_db)
    _mark_current_state_publication_partial(isolated_db)

    assessment = assess_feasibility(_demand())
    proposed = StaffingProposalService().propose(_demand())

    assert assessment["decision_ready"] is False
    assert {
        (item["source_id"], item["state"])
        for item in assessment["safety_blockers"]
        if item["code"] == "source_not_fresh"
    } >= {("current-state-staffing-publication", "partial")}
    assert proposed["status"] == "blocked"


def test_source_run_change_after_proposal_invalidates_confirmation(
    isolated_db,
) -> None:
    _seed_staffing_facts(isolated_db)
    service = StaffingProposalService()
    proposed = service.propose(_demand())
    _fail_source(isolated_db, "import-hiref-report")

    result = service.confirm(
        proposed["proposal_id"],
        proposed["confirmation_token"],
    )

    assert result["status"] == "invalid"
    assert "facts changed" in result["warning"]
    with sqlite3.connect(isolated_db) as con:
        assert con.execute("SELECT COUNT(*) FROM assignments").fetchone()[0] == 0


def test_stfte_without_hiref_remains_visible_with_action_context(isolated_db) -> None:
    _seed_staffing_facts(isolated_db)
    with sqlite3.connect(isolated_db) as con:
        con.execute("UPDATE employees SET current_hiref='' WHERE id='990104'")

    result = assess_feasibility(_demand())
    candidates = {item["member_id"]: item for item in result["candidates"]}

    assert candidates["990104"]["reasons"] == []
    assert candidates["990104"]["hiref_context"]["status"] == "missing"
    assert (
        candidates["990104"]["hiref_context"]["recommended_action"]
        == "submit_new_hiref"
    )


def test_selected_stfte_hiref_gap_requires_dm_action_note(isolated_db) -> None:
    _seed_staffing_facts(isolated_db)
    with sqlite3.connect(isolated_db) as con:
        con.execute(
            """
            UPDATE monthly_allocations
            SET allocation = 0.95
            WHERE employee_id IN ('990101', '990102')
              AND project_id = 'project-atlas-990001'
              AND year = 2026
              AND month = 8
              AND plan_version_id = 'plan-2026-08'
            """
        )
        con.commit()
    demand = _demand().model_copy(
        update={"effort": 0.4, "maximum_people": 1}
    )
    service = StaffingProposalService()

    assessment = assess_feasibility(demand)
    blocked = service.propose(demand)
    proposed = service.propose(
        demand,
        acknowledge_hiref_actions=True,
        hiref_action_note="Submit an extend HIREF before charge-code use.",
    )
    confirmed = service.confirm(
        proposed["proposal_id"],
        proposed["confirmation_token"],
    )

    assert assessment["feasible"] is True
    assert assessment["decision_ready"] is False
    assert assessment["selections"][0]["member_id"] == "990104"
    assert assessment["decision_conditions"] == [
        {
            "code": "hiref_action_required",
            "member_id": "990104",
            "hiref_status": "partial_coverage",
            "recommended_action": "submit_or_extend_hiref",
        }
    ]
    assert blocked["status"] == "blocked"
    assert proposed["status"] == "proposed"
    assert confirmed["status"] == "confirmed"
    assert (
        proposed["preview"]["hiref_action_acknowledgement"]["note"]
        == "Submit an extend HIREF before charge-code use."
    )
    with sqlite3.connect(isolated_db) as con:
        chosen = json.loads(
            con.execute(
                "SELECT chosen FROM decision_log WHERE id=?",
                [confirmed["decision_id"]],
            ).fetchone()[0]
        )
    assert (
        chosen["decision_safety"]["hiref_action_acknowledgement"]["note"]
        == "Submit an extend HIREF before charge-code use."
    )


def test_current_and_next_hiref_can_jointly_cover_target_period(isolated_db) -> None:
    _seed_staffing_facts(isolated_db)
    with sqlite3.connect(isolated_db) as con:
        con.execute(
            """INSERT INTO hiref
               (id, project, request_type, start_date, end_date)
               VALUES ('HIREF-990104-NEXT', 'Project Atlas', 'extend',
                       '2026-08-16', '2026-12-31')"""
        )
        con.execute(
            "UPDATE employees SET next_hiref='HIREF-990104-NEXT' "
            "WHERE id='990104'"
        )

    result = assess_feasibility(_demand())
    candidates = {item["member_id"]: item for item in result["candidates"]}

    assert candidates["990104"]["hiref_context"]["status"] == "covered"
    assert [record["request_type"] for record in candidates["990104"]["hiref_context"]["records"]] == [
        "extend",
        "extend",
    ]


def test_unknown_plan_version_blocks_proposal(isolated_db) -> None:
    _seed_staffing_facts(isolated_db)
    demand = _demand().model_copy(update={"plan_version_id": "unknown-plan"})

    assessment = assess_feasibility(demand)
    proposed = StaffingProposalService().propose(demand)

    assert assessment["decision_ready"] is False
    assert {"code": "requested_plan_version_not_found"} in assessment["safety_blockers"]
    assert proposed["status"] == "blocked"
    with sqlite3.connect(isolated_db) as con:
        assert con.execute("SELECT COUNT(*) FROM staffing_proposals").fetchone()[0] == 0


def test_unknown_target_project_blocks_proposal(isolated_db) -> None:
    _seed_staffing_facts(isolated_db)
    demand = _demand().model_copy(update={"project_id": "project-unknown"})

    assessment = assess_feasibility(demand)
    proposed = StaffingProposalService().propose(demand)

    assert {"code": "target_project_not_found"} in assessment["safety_blockers"]
    assert proposed["status"] == "blocked"
