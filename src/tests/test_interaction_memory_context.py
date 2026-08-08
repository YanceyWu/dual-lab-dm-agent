from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest
from typer.testing import CliRunner

from pm_agent.cli import app as app_module
from pm_agent.database.bootstrap import main as init_db
from pm_agent.interaction_memory import repository
from pm_agent.interaction_memory.service import demo_seed
from pm_agent.interaction_memory.service import resolve_scope, resolve_turn_context
from pm_agent.use_cases import use_case_executor
from pm_agent.use_cases.service import UseCaseRequest

ROOT = Path(__file__).resolve().parents[2]


def test_interaction_memory_context_use_case_and_tool_query_share_contract(
    isolated_db,
) -> None:
    init_db(quiet=True)
    demo_seed(repo_root=ROOT)
    direct = use_case_executor.execute(
        UseCaseRequest(
            use_case_id="interaction-memory-context",
            parameters={
                "message": "准备补本周 brief，先看谁还有容量",
                "repo_root": str(ROOT),
            },
        )
    )
    cli = CliRunner().invoke(
        app_module.app,
        [
            "tool",
            "query",
            "interaction-memory-context",
            "--param",
            "message=准备补本周 brief，先看谁还有容量",
            "--param",
            f"repo_root={ROOT}",
        ],
    )
    assert cli.exit_code == 0, cli.output
    cli_payload = json.loads(cli.output)
    assert cli_payload["status"] == "success"
    assert cli_payload["data"] == direct.data
    assert cli_payload["evidence"] == direct.evidence
    assert cli_payload["warnings"] == direct.warnings
    assert cli_payload["context"]["context_type"] == "interaction_memory_context"


def test_interaction_memory_context_tool_query_fails_open_when_schema_is_missing(
    isolated_db,
) -> None:
    cli = CliRunner().invoke(
        app_module.app,
        [
            "tool",
            "query",
            "interaction-memory-context",
            "--param",
            "message=先看下谁还有容量",
            "--param",
            f"repo_root={ROOT}",
        ],
    )
    assert cli.exit_code == 0, cli.output
    payload = json.loads(cli.output)
    assert payload["status"] == "success"
    assert payload["data"]["capability_state"] == "unavailable"
    assert payload["warnings"] == [{"code": "INTERACTION_MEMORY_UNAVAILABLE"}]
    assert payload["data"]["diagnostics"] == {
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


def test_interaction_memory_context_tool_query_accepts_stdin_message_without_mutation(
    isolated_db,
) -> None:
    init_db(quiet=True)
    demo_seed(repo_root=ROOT)
    cli = CliRunner().invoke(
        app_module.app,
        [
            "tool",
            "query",
            "interaction-memory-context",
            "--param-stdin",
            "message",
            "--param",
            f"repo_root={ROOT}",
        ],
        input='show "Atlas" $HOME capacity\n',
    )
    assert cli.exit_code == 0, cli.output
    payload = json.loads(cli.output)
    assert payload["status"] == "success"
    assert payload["data"]["turn"]["message"] == 'show "Atlas" $HOME capacity'


def test_interaction_memory_context_resolve_skips_integrity_scan_on_hot_path(
    isolated_db,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    init_db(quiet=True)
    demo_seed(repo_root=ROOT)

    def fail_if_called():
        raise AssertionError("resolve_turn_context must not run integrity_report")

    monkeypatch.setattr(repository, "integrity_report", fail_if_called)
    payload = resolve_turn_context(
        message="准备补本周 brief，先看谁还有容量",
        repo_root=ROOT,
    )
    assert payload["capability_state"] == "enabled"
    assert payload["diagnostics"] == {"state": "not_run"}


def test_interaction_memory_context_keeps_highest_ranked_preference_per_category(
    isolated_db,
) -> None:
    init_db(quiet=True)
    demo_seed(repo_root=ROOT)
    scope = resolve_scope(repo_root=ROOT)
    repository.upsert_entry(
        scope_id=scope.scope_id,
        memory_kind="preference",
        category="answer-language",
        title="en-US",
        summary="Respond in English for this repository.",
        state="active",
        confidence=0.1,
        weight=0.1,
        metadata={"value": "en-US", "intent_tags": ["all"]},
        interaction_event_ref={
            "repo_scope_id": scope.scope_id,
            "conversation_id": "test",
            "turn_id": "duplicate-preference",
            "operation_kind": "test_seed",
            "event_key": "duplicate-preference",
        },
    )

    payload = resolve_turn_context(
        message="准备补本周 brief，先看谁还有容量",
        repo_root=ROOT,
    )
    selected_languages = [
        entry["title"]
        for entry in payload["selected_memory"]["preferences"]
        if entry["category"] == "answer-language"
    ]
    assert selected_languages == ["zh-CN"]
    assert payload["working_context"]["answer_preferences"]["language"] == "zh-CN"
