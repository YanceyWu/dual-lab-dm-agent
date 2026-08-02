"""Controlled capacity-policy commands (R4 decision (b))."""

from __future__ import annotations

import json
import sqlite3

import typer

from pm_agent.database.staffing_capacity import (
    confirm_enable_capacity_requirement,
    policy_state,
    preview_enable_capacity_requirement,
)

capacity_policy_app = typer.Typer(
    help="Capacity-aware Staffing policy marker",
    no_args_is_help=True,
)

_TERMINAL_STATUSES = {
    "success",
    "proposed",
    "no_op",
    "confirmed",
    "idempotent",
    "expired",
    "rejected",
}


def _emit(value: dict) -> None:
    typer.echo(json.dumps(value, ensure_ascii=False, sort_keys=True))
    if value.get("status") not in _TERMINAL_STATUSES:
        raise typer.Exit(2)


def _failed(code: str) -> dict:
    return {"status": "failed", "warnings": [code]}


def _run(value_factory) -> None:
    try:
        _emit(value_factory())
    except ValueError as exc:
        _emit(_failed(str(exc)))
    except sqlite3.Error:
        _emit(_failed("DATA_ACCESS_FAILED"))


@capacity_policy_app.command("show")
def capacity_policy_show() -> None:
    """Show the capacity-required marker state (read-only)."""
    _run(lambda: {"status": "success", **policy_state()})


@capacity_policy_app.command("enable-preview")
def capacity_policy_enable_preview() -> None:
    """Preview enabling capacity-aware Staffing (never writes policy)."""
    _run(lambda: preview_enable_capacity_requirement(actor="copilot"))


@capacity_policy_app.command("enable-confirm")
def capacity_policy_enable_confirm(
    operation_id: str = typer.Option(..., "--operation-id"),
    token: str = typer.Option(..., "--token"),
) -> None:
    """Confirm one exact enable preview after fingerprint revalidation."""
    _run(
        lambda: confirm_enable_capacity_requirement(
            operation_id=operation_id,
            confirmation_token=token,
        )
    )
