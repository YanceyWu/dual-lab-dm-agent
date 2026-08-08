from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from typer.testing import CliRunner

from pm_agent.cli import app as app_module
from pm_agent.database.bootstrap import main as init_db

ROOT = Path(__file__).resolve().parents[2]
runner = CliRunner()


def _invoke(*args: str):
    return runner.invoke(app_module.app, list(args))


def _payload(result) -> dict:
    return json.loads(result.stdout)


def test_interaction_memory_status_is_empty_after_clean_bootstrap(isolated_db) -> None:
    init_db(quiet=True)
    result = _invoke(
        "interaction-memory",
        "status",
        "--repo-root",
        str(ROOT),
    )
    assert result.exit_code == 0, result.output
    payload = _payload(result)
    assert payload["status"] == "success"
    assert payload["capability_state"] == "empty"
    assert payload["enabled"] is True
    assert payload["scope"]["scope_source"] == "repo_root_fingerprint"
    assert payload["summary"]["total_entries"] == 0


def test_interaction_memory_status_reports_unavailable_when_schema_is_missing(
    isolated_db,
) -> None:
    result = _invoke(
        "interaction-memory",
        "status",
        "--project-id",
        "proj-synthetic-001",
    )
    assert result.exit_code == 0, result.output
    payload = _payload(result)
    assert payload["status"] == "success"
    assert payload["capability_state"] == "unavailable"
    assert payload["diagnostics"] == {
        "reason": "interaction_memory_schema_missing",
        "state": "not_initialized",
    }

    if isolated_db.exists():
        with sqlite3.connect(isolated_db) as database:
            tables = {
                row[0]
                for row in database.execute(
                    """
                    SELECT name
                      FROM sqlite_master
                     WHERE type='table'
                       AND name LIKE 'interaction_memory_%'
                    """
                ).fetchall()
            }
        assert tables == set()


def test_interaction_memory_demo_seed_bootstraps_capability_tables_on_first_use(
    isolated_db,
) -> None:
    seeded = _invoke(
        "interaction-memory",
        "demo-seed",
        "--project-id",
        "proj-synthetic-001",
    )
    assert seeded.exit_code == 0, seeded.output
    payload = _payload(seeded)
    assert payload["status"] == "success"
    assert payload["summary"]["total_entries"] == 7

    with sqlite3.connect(isolated_db) as database:
        tables = {
            row[0]
            for row in database.execute(
                """
                SELECT name
                  FROM sqlite_master
                 WHERE type='table'
                   AND name LIKE 'interaction_memory_%'
                """
            ).fetchall()
        }

    assert tables == {
        "interaction_memory_scopes",
        "interaction_memory_entries",
        "interaction_memory_audit",
    }


def test_interaction_memory_demo_seed_resolve_and_disable_enable_round_trip(
    isolated_db,
) -> None:
    init_db(quiet=True)
    seeded = _invoke(
        "interaction-memory",
        "demo-seed",
        "--repo-root",
        str(ROOT),
    )
    assert seeded.exit_code == 0, seeded.output
    seed_payload = _payload(seeded)
    assert seed_payload["operation"] == "demo_seed"
    assert seed_payload["summary"]["total_entries"] == 7

    inspected = _invoke(
        "interaction-memory",
        "inspect",
        "--repo-root",
        str(ROOT),
    )
    assert inspected.exit_code == 0, inspected.output
    inspect_payload = _payload(inspected)
    assert inspect_payload["capability_state"] == "enabled"
    assert inspect_payload["summary"]["by_kind"] == {
        "context": 2,
        "follow_up": 1,
        "preference": 2,
        "strategy": 2,
    }

    resolved = _invoke(
        "interaction-memory",
        "resolve",
        "--repo-root",
        str(ROOT),
        "--message",
        "先看下谁还有容量，我准备补本周 brief。",
    )
    assert resolved.exit_code == 0, resolved.output
    resolve_payload = _payload(resolved)
    assert resolve_payload["status"] == "success"
    assert resolve_payload["data"]["capability_state"] == "enabled"
    assert resolve_payload["data"]["turn"]["intent_tags"] == [
        "capacity",
        "weekly_brief",
    ]
    assert (
        resolve_payload["data"]["working_context"]["answer_preferences"]["language"]
        == "zh-CN"
    )
    assert (
        resolve_payload["data"]["working_context"]["answer_preferences"]["answer_shape"]
        == "conclusion-first"
    )
    assert (
        "team-workload-overview"
        in resolve_payload["data"]["working_context"]["routing_hints"]
    )
    assert (
        "surface-relevant-followup-once"
        in resolve_payload["data"]["working_context"]["strategy_flags"]
    )
    assert resolve_payload["data"]["working_context"]["follow_up_hints"] == [
        "Weekly brief snapshot is still pending confirmation."
    ]

    disabled = _invoke(
        "interaction-memory",
        "disable",
        "--repo-root",
        str(ROOT),
    )
    assert disabled.exit_code == 0, disabled.output
    assert _payload(disabled)["capability_state"] == "disabled"

    disabled_resolve = _invoke(
        "interaction-memory",
        "resolve",
        "--repo-root",
        str(ROOT),
        "--message",
        "先看下谁还有容量",
    )
    assert disabled_resolve.exit_code == 0, disabled_resolve.output
    disabled_payload = _payload(disabled_resolve)
    assert disabled_payload["data"]["capability_state"] == "disabled"
    assert disabled_payload["warnings"] == [{"code": "INTERACTION_MEMORY_DISABLED"}]
    assert disabled_payload["data"]["selected_memory"] == {
        "preferences": [],
        "contexts": [],
        "follow_ups": [],
        "strategies": [],
    }

    enabled = _invoke(
        "interaction-memory",
        "enable",
        "--repo-root",
        str(ROOT),
    )
    assert enabled.exit_code == 0, enabled.output
    assert _payload(enabled)["capability_state"] == "enabled"


def test_interaction_memory_demo_seed_reports_disabled_scope_state(
    isolated_db,
) -> None:
    init_db(quiet=True)
    seeded = _invoke(
        "interaction-memory",
        "demo-seed",
        "--repo-root",
        str(ROOT),
    )
    assert seeded.exit_code == 0, seeded.output

    disabled = _invoke(
        "interaction-memory",
        "disable",
        "--repo-root",
        str(ROOT),
    )
    assert disabled.exit_code == 0, disabled.output

    reseeded = _invoke(
        "interaction-memory",
        "demo-seed",
        "--repo-root",
        str(ROOT),
    )
    assert reseeded.exit_code == 0, reseeded.output
    payload = _payload(reseeded)
    assert payload["capability_state"] == "disabled"
    assert payload["enabled"] is False
    assert payload["summary"]["total_entries"] == 7


def test_interaction_memory_enable_disable_audit_uses_actual_scope_state(
    isolated_db,
) -> None:
    init_db(quiet=True)
    seeded = _invoke(
        "interaction-memory",
        "demo-seed",
        "--repo-root",
        str(ROOT),
    )
    assert seeded.exit_code == 0, seeded.output

    first_enable = _invoke(
        "interaction-memory",
        "enable",
        "--repo-root",
        str(ROOT),
    )
    assert first_enable.exit_code == 0, first_enable.output

    first_disable = _invoke(
        "interaction-memory",
        "disable",
        "--repo-root",
        str(ROOT),
    )
    assert first_disable.exit_code == 0, first_disable.output

    second_disable = _invoke(
        "interaction-memory",
        "disable",
        "--repo-root",
        str(ROOT),
    )
    assert second_disable.exit_code == 0, second_disable.output

    with sqlite3.connect(isolated_db) as database:
        rows = database.execute(
            """
            SELECT operation_type, prior_state_json, new_state_json
              FROM interaction_memory_audit
             WHERE operation_type IN ('enable', 'disable')
             ORDER BY rowid
            """
        ).fetchall()

    assert [
        (row[0], json.loads(row[1]), json.loads(row[2]))
        for row in rows
    ] == [
        ("enable", {"enabled": True}, {"enabled": True}),
        ("disable", {"enabled": True}, {"enabled": False}),
        ("disable", {"enabled": False}, {"enabled": False}),
    ]
