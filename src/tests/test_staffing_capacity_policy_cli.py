"""Focused tests for the controlled capacity-policy CLI (R4 (b))."""

from __future__ import annotations

import json
import sqlite3
from copy import deepcopy
from pathlib import Path

from typer.testing import CliRunner

from pm_agent.cli import app as app_module
from pm_agent.database.bootstrap import main as init_db
from pm_agent.resource_intelligence.service import (
    confirm_import as confirm_capacity,
    preview_import as preview_capacity,
)
from pm_agent.workforce_planning_import.service import (
    confirm_import as confirm_workforce,
    preview_import as preview_workforce,
)

ROOT = Path(__file__).resolve().parents[1]
runner = CliRunner()


def _package(name: str) -> dict:
    return json.loads((ROOT / "sample-data/json" / name).read_text(encoding="utf-8"))


def _publish_capacity(db_path: str, *, version: int = 1) -> None:
    init_db(quiet=True)
    workforce = deepcopy(_package("workforce_planning_import.sample.json"))
    workforce_preview = preview_workforce(workforce, db_path=db_path)
    if workforce_preview["status"] == "previewed":
        confirm_workforce(workforce_preview["session_id"], db_path=db_path)
    capacity = deepcopy(_package("resource_capacity_import.sample.json"))
    if version > 1:
        capacity["package_id"] = f"package-synthetic-resource-capacity-{version:03d}"
        capacity["idempotency_key"] = f"resource-capacity-synthetic-{version:03d}"
        for observation in capacity["observations"]:
            observation["source_observation_version"] = version
    capacity_preview = preview_capacity(capacity, db_path=db_path)
    if capacity_preview["status"] == "previewed":
        confirm_capacity(capacity_preview["session_id"], db_path=db_path)


def _invoke(*args: str):
    return runner.invoke(app_module.app, list(args))


def _payload(result) -> dict:
    return json.loads(result.stdout)


def _operation_count(db_path: str) -> int:
    with sqlite3.connect(db_path) as connection:
        return connection.execute(
            "SELECT COUNT(*) FROM staffing_capacity_operations"
        ).fetchone()[0]


def test_capacity_policy_show_reports_disabled_default(isolated_db) -> None:
    init_db(quiet=True)
    result = _invoke("staffing", "capacity-policy", "show")
    assert result.exit_code == 0, result.output
    payload = _payload(result)
    assert payload["status"] == "success"
    assert payload["capacity_required"] is False
    assert payload["policy_version"] == "staffing-capacity-policy-v1"


def test_capacity_policy_enable_preview_requires_publication(isolated_db) -> None:
    init_db(quiet=True)
    result = _invoke("staffing", "capacity-policy", "enable-preview")
    assert result.exit_code == 2
    assert _payload(result) == {
        "status": "failed",
        "warnings": ["STAFFING_CAPACITY_PUBLICATION_REQUIRED"],
    }
    assert _operation_count(isolated_db) == 0


def test_capacity_policy_enable_round_trip_and_audit(isolated_db) -> None:
    _publish_capacity(isolated_db)
    preview = _invoke("staffing", "capacity-policy", "enable-preview")
    assert preview.exit_code == 0, preview.output
    proposed = _payload(preview)
    assert proposed["status"] == "proposed"
    assert proposed["policy"]["capacity_required"] is False
    assert proposed["publication_id"]

    before = _payload(_invoke("staffing", "capacity-policy", "show"))
    assert before["capacity_required"] is False

    confirmed = _invoke(
        "staffing",
        "capacity-policy",
        "enable-confirm",
        "--operation-id",
        proposed["operation_id"],
        "--token",
        proposed["confirmation_token"],
    )
    assert confirmed.exit_code == 0, confirmed.output
    result = _payload(confirmed)
    assert result["status"] == "confirmed"
    assert result["capacity_required"] is True
    assert result["actor"] == "copilot"

    after = _payload(_invoke("staffing", "capacity-policy", "show"))
    assert after["capacity_required"] is True
    with sqlite3.connect(isolated_db) as connection:
        status = connection.execute(
            "SELECT status, actor, confirmed_at FROM staffing_capacity_operations"
        ).fetchone()
    assert status[0] == "confirmed"
    assert status[1] == "copilot"
    assert status[2]


def test_capacity_policy_enable_preview_no_op_when_already_enabled(
    isolated_db,
) -> None:
    _publish_capacity(isolated_db)
    proposed = _payload(_invoke("staffing", "capacity-policy", "enable-preview"))
    _invoke(
        "staffing",
        "capacity-policy",
        "enable-confirm",
        "--operation-id",
        proposed["operation_id"],
        "--token",
        proposed["confirmation_token"],
    )
    repeat = _invoke("staffing", "capacity-policy", "enable-preview")
    assert repeat.exit_code == 0, repeat.output
    assert _payload(repeat)["status"] == "no_op"


def test_capacity_policy_confirm_rejects_wrong_token(isolated_db) -> None:
    _publish_capacity(isolated_db)
    proposed = _payload(_invoke("staffing", "capacity-policy", "enable-preview"))
    result = _invoke(
        "staffing",
        "capacity-policy",
        "enable-confirm",
        "--operation-id",
        proposed["operation_id"],
        "--token",
        "wrong-token",
    )
    assert result.exit_code == 2
    assert _payload(result) == {
        "status": "failed",
        "warnings": ["STAFFING_CAPACITY_CONFIRMATION_INVALID"],
    }


def test_capacity_policy_confirm_expired_operation(isolated_db) -> None:
    _publish_capacity(isolated_db)
    proposed = _payload(_invoke("staffing", "capacity-policy", "enable-preview"))
    with sqlite3.connect(isolated_db) as connection:
        connection.execute(
            """
            UPDATE staffing_capacity_operations
            SET expires_at = '2020-01-01T00:00:00+00:00'
            WHERE operation_id = ?
            """,
            [proposed["operation_id"]],
        )
    result = _invoke(
        "staffing",
        "capacity-policy",
        "enable-confirm",
        "--operation-id",
        proposed["operation_id"],
        "--token",
        proposed["confirmation_token"],
    )
    assert result.exit_code == 0, result.output
    assert _payload(result)["status"] == "expired"


def test_capacity_policy_confirm_rejected_when_publication_changed(
    isolated_db,
) -> None:
    _publish_capacity(isolated_db, version=1)
    proposed = _payload(_invoke("staffing", "capacity-policy", "enable-preview"))
    _publish_capacity(isolated_db, version=2)
    result = _invoke(
        "staffing",
        "capacity-policy",
        "enable-confirm",
        "--operation-id",
        proposed["operation_id"],
        "--token",
        proposed["confirmation_token"],
    )
    assert result.exit_code == 0, result.output
    assert _payload(result)["status"] == "rejected"
    assert _payload(result)["reason"] == "STALE_FINGERPRINT"
    assert _payload(_invoke("staffing", "capacity-policy", "show"))[
        "capacity_required"
    ] is False
