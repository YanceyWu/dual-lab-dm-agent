"""JSON-only Delivery Attention preview and confirmation commands."""

from __future__ import annotations

import json
from typing import Optional

import typer

from pm_agent.attention import AttentionService

attention_app = typer.Typer(
    help="Delivery Attention preview and confirmation",
    no_args_is_help=True,
)
service = AttentionService()
CLI_ACTOR = "copilot"


def _emit(result: dict) -> None:
    typer.echo(json.dumps(result, ensure_ascii=False, sort_keys=True))
    if result.get("status") not in {"proposed", "success"}:
        raise typer.Exit(2)


@attention_app.command("reconcile-preview")
def reconcile_preview(
    rule: Optional[list[str]] = typer.Option(None, "--rule"),
    subject_kind: Optional[str] = typer.Option(None, "--subject-kind"),
    subject_id: Optional[str] = typer.Option(None, "--subject-id"),
) -> None:
    """Preview a bounded reconciliation without mutating Attention state."""
    _emit(
        service.preview_reconciliation(
            actor=CLI_ACTOR,
            rule_keys=rule,
            subject_kind=subject_kind,
            subject_id=subject_id,
        )
    )


@attention_app.command("acknowledge-preview")
def acknowledge_preview(
    attention_id: str = typer.Argument(...),
) -> None:
    """Preview acknowledgement of one current Attention item."""
    _emit(
        service.preview_acknowledgement(
            attention_id=attention_id,
            actor=CLI_ACTOR,
        )
    )


@attention_app.command("snooze-preview")
def snooze_preview(
    attention_id: str = typer.Argument(...),
    until: str = typer.Option(..., "--until"),
) -> None:
    """Preview snoozing one current Attention item."""
    _emit(
        service.preview_snooze(
            attention_id=attention_id,
            actor=CLI_ACTOR,
            snoozed_until=until,
        )
    )


@attention_app.command("resolve-preview")
def resolve_preview(
    attention_id: str = typer.Argument(...),
) -> None:
    """Preview resolution of one clear Attention item."""
    _emit(
        service.preview_resolution(
            attention_id=attention_id,
            actor=CLI_ACTOR,
        )
    )


@attention_app.command("confirm")
def confirm(
    operation_id: str = typer.Argument(...),
    token: str = typer.Option(..., "--token"),
) -> None:
    """Confirm one exact runtime-issued Attention preview."""
    _emit(
        service.confirm(
            operation_id=operation_id,
            confirmation_token=token,
        )
    )
