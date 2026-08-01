"""Opt-in Weekly Brief v2 query and controlled capture commands."""

from __future__ import annotations

import json

import typer

from pm_agent.use_cases import use_case_executor
from pm_agent.use_cases.service import UseCaseRequest
from pm_agent.weekly_brief.operations import confirm_capture, preview_capture

weekly_brief_app = typer.Typer(help="Opt-in Weekly Brief v2 and snapshot capture")


def _emit(value: dict) -> None:
    typer.echo(json.dumps(value, ensure_ascii=False, sort_keys=True))
    if value.get("status") not in {"success", "previewed", "confirmed", "already_confirmed", "expired", "stale"}:
        raise typer.Exit(2)


@weekly_brief_app.command("query")
def query(project_ids: str = typer.Option("", "--project-ids"), plan_version_id: str = typer.Option("", "--plan-version-id"), attention_limit: int = typer.Option(10, "--attention-limit"), baseline_snapshot_id: str = typer.Option("", "--baseline-snapshot-id")) -> None:
    """Run opt-in v2; legacy ``pm report`` remains unchanged."""
    parameters = {"attention_limit": attention_limit}
    if project_ids:
        parameters["project_ids"] = project_ids.split(",")
    if plan_version_id:
        parameters["plan_version_id"] = plan_version_id
    if baseline_snapshot_id:
        parameters["baseline_snapshot_id"] = baseline_snapshot_id
    _emit(use_case_executor.execute(UseCaseRequest(contract_version="2.0", use_case_id="weekly-dm-brief-v2", actor="copilot", parameters=parameters, requested_output="json")).model_dump(mode="json"))


@weekly_brief_app.command("snapshot-preview")
def snapshot_preview(candidate_json: str = typer.Option(..., "--candidate-json"), idempotency_key: str = typer.Option(..., "--idempotency-key")) -> None:
    """Preview capture of the exact candidate returned by v2 query."""
    try:
        candidate = json.loads(candidate_json)
    except json.JSONDecodeError:
        _emit({"status": "failed", "warnings": ["WEEKLY_BRIEF_CAPTURE_CANDIDATE_INVALID"]})
        return
    _emit(preview_capture(candidate=candidate, actor_id="copilot", idempotency_key=idempotency_key))


@weekly_brief_app.command("snapshot-confirm")
def snapshot_confirm(operation_id: str = typer.Option(..., "--operation-id"), confirmation_token: str = typer.Option(..., "--confirmation-token")) -> None:
    """Confirm one exact preview after explicit approval."""
    _emit(confirm_capture(operation_id=operation_id, confirmation_token=confirmation_token))
