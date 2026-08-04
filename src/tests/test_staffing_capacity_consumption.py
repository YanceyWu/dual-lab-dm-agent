from __future__ import annotations

import json
import sqlite3
from copy import deepcopy
from pathlib import Path

import pytest

from current_state_staffing_test_helpers import publish_current_state_staffing_from_legacy
from pm_agent.database import repository, staffing_capacity
from pm_agent.database.bootstrap import main as init_db
from pm_agent.resource_intelligence.service import confirm_import, preview_import
from pm_agent.use_cases.staffing import (
    StaffingDemand,
    StaffingProposalService,
    assess_feasibility,
)
from pm_agent.workforce_planning_import.service import (
    confirm_import as confirm_workforce,
    preview_import as preview_workforce,
)

ROOT = Path(__file__).resolve().parents[1]


def _package(name: str) -> dict:
    return json.loads((ROOT / "sample-data/json" / name).read_text(encoding="utf-8"))


def _bootstrap_workforce(db_path: Path) -> None:
    init_db(quiet=True)
    workforce = preview_workforce(
        _package("workforce_planning_import.sample.json"), db_path=db_path
    )
    confirm_workforce(workforce["session_id"], db_path=db_path)
    publish_current_state_staffing_from_legacy(
        db_path,
        package_id="package-synthetic-current-state-staffing-001",
    )
    for source_id in (
        "import-resource-portal",
        "import-skills-matrix",
        "import-hiref-report",
    ):
        run_id = repository.start_sync_run(source_id, triggered_by="synthetic-test")
        repository.finish_sync_run(run_id, status="success")


def _publish_capacity(db_path: Path, package: dict | None = None) -> dict:
    preview = preview_import(
        package or _package("resource_capacity_import.sample.json"), db_path=db_path
    )
    return confirm_import(preview["session_id"], db_path=db_path)


def _demand(*, effort: float = 0.2) -> StaffingDemand:
    return StaffingDemand(
        project_id="project-synthetic-atlas",
        start_period="2026-08",
        end_period="2026-08",
        effort=effort,
        minimum_allocation=0.1,
        maximum_people=1,
        splittable=True,
        plan_version_id="plan-synthetic-baseline-001",
    )


def test_compatibility_marker_installs_disabled_and_requires_publication_to_enable(
    isolated_db: Path,
) -> None:
    init_db(quiet=True)

    assert staffing_capacity.capacity_required(db_path=isolated_db) is False
    with pytest.raises(ValueError, match="STAFFING_CAPACITY_PUBLICATION_REQUIRED"):
        staffing_capacity.enable_capacity_requirement(db_path=isolated_db)
    assert staffing_capacity.capacity_required(db_path=isolated_db) is False
    with sqlite3.connect(isolated_db) as database:
        database.execute("DELETE FROM staffing_capacity_policy")
    with pytest.raises(ValueError, match="STAFFING_CAPACITY_POLICY_NOT_FOUND"):
        staffing_capacity.capacity_required(db_path=isolated_db)
    with pytest.raises(ValueError, match="STAFFING_CAPACITY_POLICY_NOT_FOUND"):
        init_db(quiet=True)


def test_disabled_marker_preserves_legacy_staffing_assumption(isolated_db: Path) -> None:
    _bootstrap_workforce(isolated_db)

    result = assess_feasibility(_demand(effort=0.8))

    assert result["capacity_policy"]["required"] is False
    assert result["rule_version"] == "staffing-feasibility-v2"
    assert result["feasible"] is True


def test_enabled_marker_uses_published_capacity_for_assessment(isolated_db: Path) -> None:
    _bootstrap_workforce(isolated_db)
    publication = _publish_capacity(isolated_db)
    enabled = staffing_capacity.enable_capacity_requirement(db_path=isolated_db)

    result = assess_feasibility(_demand())
    candidates = {item["member_id"]: item for item in result["candidates"]}

    assert enabled["capacity_publication_id"] == publication["report"]["publication_id"]
    assert result["capacity_policy"]["required"] is True
    assert result["rule_version"] == "staffing-effective-capacity-v1"
    assert result["selections"] == [
        {"member_id": "member-synthetic-002", "name": "Synthetic Member 002", "allocation": 0.2}
    ]
    assert candidates["member-synthetic-001"]["available_allocation"] == 0.2
    evidence = candidates["member-synthetic-001"]["capacity_evidence"][0]
    assert evidence["effective_capacity"] == 0.7
    assert evidence["planned_project_allocation"] == 0.5
    assert evidence["current_planned_allocation"] == 0.5
    assert evidence["staffing_available_capacity"] == 0.2
    assert evidence["derivation_id"].startswith("resource-capacity-derivation-")


def test_capacity_aware_proposal_confirmation_is_atomic_and_idempotent(
    isolated_db: Path,
) -> None:
    _bootstrap_workforce(isolated_db)
    _publish_capacity(isolated_db)
    staffing_capacity.enable_capacity_requirement(db_path=isolated_db)
    service = StaffingProposalService()

    proposed = service.propose(_demand())
    confirmed = service.confirm(proposed["proposal_id"], proposed["confirmation_token"])
    repeated = service.confirm(proposed["proposal_id"], proposed["confirmation_token"])

    assert proposed["status"] == "proposed"
    assert proposed["preview"]["capacity_policy"]["required"] is True
    assert confirmed["status"] == "confirmed"
    assert repeated == {**confirmed, "idempotent": True}
    with sqlite3.connect(isolated_db) as database:
        allocation = database.execute(
            """SELECT allocation FROM monthly_allocations
               WHERE employee_id='member-synthetic-002'
                 AND project_id='project-synthetic-atlas'"""
        ).fetchone()[0]
        chosen = json.loads(database.execute(
            "SELECT chosen FROM decision_log WHERE id=?", [confirmed["decision_id"]]
        ).fetchone()[0])
    assert allocation == 0.2
    assert chosen["decision_safety"]["capacity_policy"]["required"] is True
    assert chosen["decision_safety"]["capacity_evidence"][0]["periods"][0][
        "derivation_id"
    ]
    refreshed = assess_feasibility(_demand())
    selected = next(
        item
        for item in refreshed["candidates"]
        if item["member_id"] == "member-synthetic-002"
    )
    assert selected["available_allocation"] == 0.7


def test_confirmation_transaction_rejects_plan_change_without_partial_write(
    isolated_db: Path,
) -> None:
    _bootstrap_workforce(isolated_db)
    _publish_capacity(isolated_db)
    staffing_capacity.enable_capacity_requirement(db_path=isolated_db)
    service = StaffingProposalService()
    proposed = service.propose(_demand())
    stored = repository.get_staffing_proposal(proposed["proposal_id"])
    with sqlite3.connect(isolated_db) as database:
        database.execute(
            """UPDATE monthly_allocations SET allocation=0.1
               WHERE employee_id='member-synthetic-002'"""
        )

    with pytest.raises(ValueError, match="Planned allocation changed after proposal"):
        repository.confirm_staffing_proposal(
            proposed["proposal_id"], proposed["confirmation_token"], stored["proposal"]
        )
    with sqlite3.connect(isolated_db) as database:
        assert database.execute(
            "SELECT COUNT(*) FROM assignments WHERE status='planned'"
        ).fetchone()[0] == 0
        assert database.execute(
            "SELECT status FROM staffing_proposals WHERE proposal_id=?",
            [proposed["proposal_id"]],
        ).fetchone()[0] == "proposed"


def test_confirmation_transaction_enforces_effective_capacity_not_one(
    isolated_db: Path,
) -> None:
    _bootstrap_workforce(isolated_db)
    _publish_capacity(isolated_db)
    staffing_capacity.enable_capacity_requirement(db_path=isolated_db)
    service = StaffingProposalService()
    proposed = service.propose(_demand())
    stored = repository.get_staffing_proposal(proposed["proposal_id"])
    stored["proposal"]["selections"][0]["allocation"] = 0.95

    with pytest.raises(ValueError, match="exceed effective capacity"):
        repository.confirm_staffing_proposal(
            proposed["proposal_id"], proposed["confirmation_token"], stored["proposal"]
        )
    with sqlite3.connect(isolated_db) as database:
        assert database.execute(
            "SELECT COUNT(*) FROM assignments WHERE status='planned'"
        ).fetchone()[0] == 0


def test_superseded_capacity_invalidates_proposal_without_domain_write(
    isolated_db: Path,
) -> None:
    _bootstrap_workforce(isolated_db)
    package = _package("resource_capacity_import.sample.json")
    _publish_capacity(isolated_db, package)
    staffing_capacity.enable_capacity_requirement(db_path=isolated_db)
    service = StaffingProposalService()
    proposed = service.propose(_demand())

    replacement = deepcopy(package)
    replacement["package_id"] = "package-synthetic-resource-capacity-002"
    replacement["idempotency_key"] = "resource-capacity-synthetic-002"
    for observation in replacement["observations"]:
        observation["source_observation_version"] = 2
    replacement["observations"][4]["fraction"] = 0.8
    _publish_capacity(isolated_db, replacement)

    result = service.confirm(proposed["proposal_id"], proposed["confirmation_token"])

    assert result["status"] == "invalid"
    with sqlite3.connect(isolated_db) as database:
        assert database.execute(
            "SELECT COUNT(*) FROM assignments WHERE status='planned'"
        ).fetchone()[0] == 0


def test_stale_capacity_is_not_a_staffing_candidate(isolated_db: Path) -> None:
    _bootstrap_workforce(isolated_db)
    package = _package("resource_capacity_import.sample.json")
    for observation in package["observations"]:
        observation["observed_at"] = "2026-06-01T00:00:00+00:00"
    _publish_capacity(isolated_db, package)
    staffing_capacity.enable_capacity_requirement(db_path=isolated_db)

    result = assess_feasibility(_demand())

    assert result["feasible"] is False
    assert {
        reason for candidate in result["candidates"] for reason in candidate["reasons"]
    } == {"effective_capacity_not_known"}


def test_missing_capacity_month_fails_closed_for_multi_month_demand(
    isolated_db: Path,
) -> None:
    _bootstrap_workforce(isolated_db)
    _publish_capacity(isolated_db)
    staffing_capacity.enable_capacity_requirement(db_path=isolated_db)

    result = assess_feasibility(
        _demand().model_copy(update={"end_period": "2026-09"})
    )

    assert result["feasible"] is False
    assert all(
        "effective_capacity_not_known" in candidate["reasons"]
        for candidate in result["candidates"]
    )
    assert all(
        {item["period"] for item in candidate["capacity_evidence"]}
        == {"2026-08", "2026-09"}
        for candidate in result["candidates"]
    )
