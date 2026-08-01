from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from pm_agent.cli import app as app_module
from pm_agent.database.bootstrap import main as init_db
from pm_agent.resource_intelligence.service import confirm_import, preview_import
from pm_agent.use_cases import use_case_executor
from pm_agent.use_cases.service import UseCaseRequest
from pm_agent.workforce_planning_import.service import (
    confirm_import as confirm_workforce,
    preview_import as preview_workforce,
)

ROOT = Path(__file__).resolve().parents[1]


def _package(name: str) -> dict:
    return json.loads((ROOT / "sample-data/json" / name).read_text(encoding="utf-8"))


def _publish_capacity(db_path: Path) -> None:
    init_db(quiet=True)
    workforce = preview_workforce(
        _package("workforce_planning_import.sample.json"), db_path=db_path
    )
    confirm_workforce(workforce["session_id"], db_path=db_path)
    capacity = preview_import(
        _package("resource_capacity_import.sample.json"), db_path=db_path
    )
    confirm_import(capacity["session_id"], db_path=db_path)


def _request(**parameters) -> UseCaseRequest:
    return UseCaseRequest(
        use_case_id="resource-capacity-heatmap",
        parameters={
            "year": 2026,
            "month": 8,
            "plan_version_id": "plan-synthetic-baseline-001",
            **parameters,
        },
    )


def test_heatmap_projects_published_capacity_without_recalculation(isolated_db: Path) -> None:
    _publish_capacity(isolated_db)

    result = use_case_executor.execute(_request())

    assert result.status == "success"
    assert [row["member_id"] for row in result.data["rows"]] == [
        "member-synthetic-001",
        "member-synthetic-002",
    ]
    first = result.data["rows"][0]
    assert first["effective_capacity"] == 0.7
    assert first["available_capacity"] == 0.2
    assert len(result.facts) == len(result.signals) == 2
    assert result.facts[0].value["derivation_id"] == first["derivation_id"]
    assert result.signals[0].signal_type == "resource_overload"
    assert result.recommendations == []
    assert result.execution_metadata["read_only"] is True


def test_heatmap_filters_exact_members_and_rejects_invalid_state(isolated_db: Path) -> None:
    _publish_capacity(isolated_db)

    filtered = use_case_executor.execute(
        _request(member_ids=["member-synthetic-002"], states=["known"])
    )
    invalid = use_case_executor.execute(_request(states=["green"]))

    assert [row["member_id"] for row in filtered.data["rows"]] == [
        "member-synthetic-002"
    ]
    assert invalid.status == "invalid"
    assert invalid.warnings == [{"code": "RESOURCE_CAPACITY_STATE_FILTER_INVALID"}]
    excessive = use_case_executor.execute(
        _request(member_ids=[f"member-synthetic-{index:03d}" for index in range(201)])
    )
    assert excessive.status == "invalid"
    assert excessive.warnings == [
        {"code": "RESOURCE_CAPACITY_MEMBER_IDS_LIMIT_EXCEEDED"}
    ]


def test_heatmap_absence_is_unavailable_not_empty_healthy(isolated_db: Path) -> None:
    init_db(quiet=True)

    result = use_case_executor.execute(_request())

    assert result.status == "unavailable"
    assert result.data["rows"] == []
    assert result.warnings == ["RESOURCE_CAPACITY_HEATMAP_NOT_AVAILABLE"]
    assert result.facts == result.signals == []


def test_generic_cli_exposes_same_read_only_heatmap_contract(isolated_db: Path) -> None:
    _publish_capacity(isolated_db)
    runner = CliRunner()

    described = runner.invoke(
        app_module.app, ["tool", "describe", "resource-capacity-heatmap"]
    )
    queried = runner.invoke(
        app_module.app,
        [
            "tool", "query", "resource-capacity-heatmap",
            "--param", "year=2026", "--param", "month=8",
            "--param", "plan_version_id=plan-synthetic-baseline-001",
        ],
    )

    assert described.exit_code == queried.exit_code == 0
    descriptor = json.loads(described.output)["data"]["use_case"]
    result = json.loads(queried.output)
    assert descriptor["read_only"] is True
    assert descriptor["intelligence_capabilities"] == {
        "facts": True, "signals": True, "recommendations": False
    }
    assert result["status"] == "success"
    assert len(result["data"]["rows"]) == 2
