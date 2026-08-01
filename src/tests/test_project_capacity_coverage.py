from __future__ import annotations

import copy
import json
import sqlite3
from pathlib import Path

import pytest

from pm_agent.database.bootstrap import main as init_db
from pm_agent.project_health.evaluation import evaluate
from pm_agent.project_health.read_model import latest_assessments
from pm_agent.resource_intelligence.read_model import get_project_capacity_coverage
from pm_agent.resource_intelligence.service import confirm_import, preview_import
from pm_agent.workforce_planning_import.read_model import project_allocation_snapshot
from pm_agent.workforce_planning_import.service import (
    confirm_import as confirm_workforce,
    preview_import as preview_workforce,
)

ROOT = Path(__file__).resolve().parents[1]
PROJECT_ID = "project-synthetic-atlas"
PLAN_ID = "plan-synthetic-baseline-001"


def _package(name: str) -> dict:
    return json.loads((ROOT / "sample-data/json" / name).read_text(encoding="utf-8"))


def _publish(
    db_path: Path, *, allocation: float = 0.5, empty: bool = False, stale: bool = False
) -> None:
    init_db(quiet=True)
    workforce = copy.deepcopy(_package("workforce_planning_import.sample.json"))
    workforce["monthly_allocations"][0]["allocation"] = 0.0 if empty else allocation
    confirmed_workforce = preview_workforce(workforce, db_path=db_path)
    confirm_workforce(confirmed_workforce["session_id"], db_path=db_path)
    capacity = copy.deepcopy(_package("resource_capacity_import.sample.json"))
    if stale:
        for observation in capacity["observations"]:
            observation["observed_at"] = "2026-06-01T00:00:00+00:00"
    confirmed_capacity = preview_import(capacity, db_path=db_path)
    confirm_import(confirmed_capacity["session_id"], db_path=db_path)


def _factor(db_path: Path, assessment_run_id: str | None = None) -> dict:
    if assessment_run_id is None:
        assessment = latest_assessments(project_id=PROJECT_ID, db_path=db_path)[0]
        return next(
            item for item in assessment["factors"]
            if item["factor_id"] == "resource_capacity_coverage"
        )
    with sqlite3.connect(db_path) as database:
        state, detail = database.execute(
            """SELECT state,evidence_json FROM project_health_factor_results
               WHERE assessment_run_id=? AND factor_id='resource_capacity_coverage'""",
            [assessment_run_id],
        ).fetchone()
    return {"state": state, "detail": json.loads(detail)}


def test_project_allocation_snapshot_distinguishes_explicit_zero_from_missing(
    isolated_db: Path,
) -> None:
    _publish(isolated_db)

    known = project_allocation_snapshot(PROJECT_ID, 2026, 8, PLAN_ID, db_path=isolated_db)
    missing = project_allocation_snapshot(PROJECT_ID, 2026, 9, PLAN_ID, db_path=isolated_db)

    assert known["state"] == "known"
    assert known["assignment_state"] == "assigned"
    assert known["assignments"] == [
        {"member_id": "member-synthetic-001", "allocation": 0.5}
    ]
    assert known["explicit_zero_member_ids"] == ["member-synthetic-002"]
    assert missing["state"] == "unknown"
    assert missing["state_reason"] == "period_not_in_authoritative_manifest"


def test_capacity_coverage_uses_the_published_member_derivation(isolated_db: Path) -> None:
    _publish(isolated_db)

    coverage = get_project_capacity_coverage(
        PROJECT_ID, 2026, 8, PLAN_ID, db_path=isolated_db
    )

    assert coverage["state"] == "known"
    assert coverage["value"] == {
        "assignment_state": "assigned",
        "assigned_member_count": 1,
        "overload_state": "clear",
        "overloaded_member_count": 0,
    }
    derivation = coverage["evidence"]["capacity_derivations"][0]
    assert derivation["derivation_rule_version"] == "effective-capacity-v1"
    assert derivation["plan_version_id"] == PLAN_ID
    assert derivation["derivation_id"]


def test_project_health_publishes_green_only_for_complete_clear_coverage(
    isolated_db: Path,
) -> None:
    _publish(isolated_db)

    legacy = evaluate(PROJECT_ID, db_path=isolated_db)
    current = evaluate(
        PROJECT_ID,
        capacity_year=2026,
        capacity_month=8,
        capacity_plan_version_id=PLAN_ID,
        db_path=isolated_db,
    )

    assert legacy["dimensions"]["resource"] == "not_available"
    assert current["dimensions"]["resource"] == "green"
    factor = _factor(isolated_db, current["assessment_run_id"])
    assert factor["state"] == "green"
    assert factor["detail"]["reason_codes"] == ["CAPACITY_COVERAGE_COMPLETE"]
    capacity_evidence = factor["detail"]["evidence_refs"][0]["evidence"]
    assert capacity_evidence["capacity_derivations"][0]["derivation_id"]
    with sqlite3.connect(isolated_db) as database:
        assert database.execute("SELECT COUNT(*) FROM attention_signals").fetchone()[0] == 0


def test_authoritative_empty_assignment_is_known_but_never_green(isolated_db: Path) -> None:
    _publish(isolated_db, empty=True)

    coverage = get_project_capacity_coverage(
        PROJECT_ID, 2026, 8, PLAN_ID, db_path=isolated_db
    )
    result = evaluate(
        PROJECT_ID,
        capacity_year=2026,
        capacity_month=8,
        capacity_plan_version_id=PLAN_ID,
        db_path=isolated_db,
    )

    assert coverage["state"] == "known"
    assert coverage["value"]["assignment_state"] == "empty"
    assert result["dimensions"]["resource"] == "unknown"
    assert _factor(isolated_db)["detail"]["reason_codes"] == [
        "CAPACITY_COVERAGE_AUTHORITATIVE_EMPTY"
    ]


@pytest.mark.parametrize(
    ("publish_options", "expected_state", "expected_reason"),
    [
        ({"stale": True}, "stale", "CAPACITY_COVERAGE_STALE"),
        ({"allocation": 0.9}, "red", "CAPACITY_OVERLOAD_RED"),
    ],
)
def test_project_health_preserves_capacity_risk_and_limited_state(
    isolated_db: Path,
    publish_options: dict,
    expected_state: str,
    expected_reason: str,
) -> None:
    _publish(isolated_db, **publish_options)

    result = evaluate(
        PROJECT_ID,
        capacity_year=2026,
        capacity_month=8,
        capacity_plan_version_id=PLAN_ID,
        db_path=isolated_db,
    )

    assert result["dimensions"]["resource"] == expected_state
    factor = _factor(isolated_db)
    assert factor["state"] == expected_state
    assert factor["detail"]["reason_codes"] == [expected_reason]


@pytest.mark.parametrize(
    ("capacity_state", "expected_state"),
    [("missing", "unknown"), ("unknown", "unknown"), ("conflicting", "conflicting")],
)
def test_assigned_member_capacity_gaps_never_publish_resource_green(
    isolated_db: Path, capacity_state: str, expected_state: str
) -> None:
    _publish(isolated_db)
    with sqlite3.connect(isolated_db) as database:
        if capacity_state == "missing":
            database.execute(
                "DELETE FROM resource_capacity_derivations WHERE member_id='member-synthetic-001'"
            )
        else:
            database.execute(
                """UPDATE resource_capacity_derivations SET state=?
                   WHERE member_id='member-synthetic-001'""",
                [capacity_state],
            )

    coverage = get_project_capacity_coverage(
        PROJECT_ID, 2026, 8, PLAN_ID, db_path=isolated_db
    )
    result = evaluate(
        PROJECT_ID,
        capacity_year=2026,
        capacity_month=8,
        capacity_plan_version_id=PLAN_ID,
        db_path=isolated_db,
    )

    assert coverage["state"] == expected_state
    assert result["dimensions"]["resource"] == expected_state


def test_invalid_known_overload_state_fails_closed(isolated_db: Path) -> None:
    _publish(isolated_db)
    with sqlite3.connect(isolated_db) as database:
        database.execute(
            """UPDATE resource_capacity_derivations SET overload_state=NULL
               WHERE member_id='member-synthetic-001'"""
        )

    coverage = get_project_capacity_coverage(
        PROJECT_ID, 2026, 8, PLAN_ID, db_path=isolated_db
    )

    assert coverage["state"] == "unknown"
    assert coverage["state_reason"] == "assigned_member_overload_state_invalid"


def test_execution_fact_cannot_bypass_capacity_reader_boundary(isolated_db: Path) -> None:
    _publish(isolated_db)
    with sqlite3.connect(isolated_db) as database:
        database.execute(
            """INSERT INTO execution_derivation_runs VALUES
               ('run-capacity-bypass',?,'board-capacity-bypass','v1','fp-capacity-bypass',
                'complete','fresh','[]',0,'2026-08-01T00:00:00+00:00',
                '2026-08-01T00:00:01+00:00')""",
            [PROJECT_ID],
        )
        database.execute(
            """INSERT INTO execution_facts VALUES
               ('fact-capacity-bypass','run-capacity-bypass',?,'project_month',?,
                'capacity_coverage',?, 'known','fresh','{}')""",
            [
                PROJECT_ID,
                PROJECT_ID,
                json.dumps({"assignment_state": "assigned", "overload_state": "clear"}),
            ],
        )

    result = evaluate(PROJECT_ID, db_path=isolated_db)

    assert result["dimensions"]["resource"] == "not_available"


def test_project_health_requires_an_exact_capacity_scope(isolated_db: Path) -> None:
    init_db(quiet=True)

    with pytest.raises(ValueError, match="PROJECT_HEALTH_CAPACITY_SCOPE_INCOMPLETE"):
        evaluate(PROJECT_ID, capacity_year=2026, db_path=isolated_db)
