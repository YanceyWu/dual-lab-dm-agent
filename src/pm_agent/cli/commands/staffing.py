"""Local manager commands for deterministic staffing assessment and confirmation."""

from __future__ import annotations

import json
from typing import Optional

import typer

from pm_agent.use_cases.staffing import StaffingDemand, StaffingProposalService, assess_feasibility

staffing_app = typer.Typer(help="Period-aware staffing assessment and confirmation", no_args_is_help=True)
service = StaffingProposalService()


def _demand(
    project: str, start: str, end: str, effort: float, role: str,
    minimum: float, maximum_people: int, splittable: bool, plan_version: Optional[str],
) -> StaffingDemand:
    return StaffingDemand(
        project_id=project, start_period=start, end_period=end, effort=effort, role=role,
        minimum_allocation=minimum, maximum_people=maximum_people, splittable=splittable,
        plan_version_id=plan_version,
    )


def _emit(payload: dict) -> None:
    typer.echo(json.dumps(payload, ensure_ascii=False, sort_keys=True))


@staffing_app.command("assess")
def assess(
    project: str = typer.Option(..., "--project"), start: str = typer.Option(..., "--start"),
    end: str = typer.Option(..., "--end"), effort: float = typer.Option(..., "--effort"),
    role: str = typer.Option("", "--role"),
    minimum: float = typer.Option(0.1, "--minimum"), maximum_people: int = typer.Option(1, "--maximum-people"),
    splittable: bool = typer.Option(True, "--splittable/--no-split"), plan_version: Optional[str] = typer.Option(None, "--plan-version"),
):
    """Assess whether a demand is feasible; does not write data."""
    _emit(assess_feasibility(_demand(project, start, end, effort, role, minimum, maximum_people, splittable, plan_version)))


@staffing_app.command("propose")
def propose(
    project: str = typer.Option(..., "--project"), start: str = typer.Option(..., "--start"),
    end: str = typer.Option(..., "--end"), effort: float = typer.Option(..., "--effort"),
    role: str = typer.Option("", "--role"),
    minimum: float = typer.Option(0.1, "--minimum"), maximum_people: int = typer.Option(1, "--maximum-people"),
    splittable: bool = typer.Option(True, "--splittable/--no-split"), plan_version: Optional[str] = typer.Option(None, "--plan-version"),
    expires_minutes: int = typer.Option(30, "--expires-minutes", min=1, max=1440),
    allow_non_fresh: bool = typer.Option(
        False,
        "--allow-non-fresh",
        help="Explicitly allow a DM-reviewed proposal using non-fresh source facts.",
    ),
    freshness_override_reason: str = typer.Option(
        "",
        "--freshness-override-reason",
        help="Required audit reason when --allow-non-fresh is used.",
    ),
    acknowledge_hiref_actions: bool = typer.Option(
        False,
        "--acknowledge-hiref-actions",
        help="Acknowledge that selected SFTE/STFTE options require HIREF action.",
    ),
    hiref_action_note: str = typer.Option(
        "",
        "--hiref-action-note",
        help="Required DM plan for submitting, extending, or changing HIREF.",
    ),
):
    """Create an expiring staffing proposal; no assignment is written."""
    _emit(
        service.propose(
            _demand(
                project,
                start,
                end,
                effort,
                role,
                minimum,
                maximum_people,
                splittable,
                plan_version,
            ),
            expires_minutes,
            allow_non_fresh=allow_non_fresh,
            freshness_override_reason=freshness_override_reason,
            acknowledge_hiref_actions=acknowledge_hiref_actions,
            hiref_action_note=hiref_action_note,
        )
    )


@staffing_app.command("preview")
def preview(proposal_id: str):
    """Preview an unconfirmed proposal."""
    _emit(service.preview(proposal_id) or {"status": "unavailable"})


@staffing_app.command("confirm")
def confirm(proposal_id: str, token: str = typer.Option(..., "--token")):
    """Explicitly confirm a proposal after deterministic revalidation."""
    _emit(service.confirm(proposal_id, token))


@staffing_app.command("cancel")
def cancel(proposal_id: str, reason: str = typer.Option("", "--reason")):
    """Cancel an unconfirmed proposal without changing assignments."""
    _emit(service.cancel(proposal_id, reason))


@staffing_app.command("reject")
def reject(proposal_id: str, reason: str = typer.Option("", "--reason")):
    """Reject an unconfirmed proposal without changing assignments."""
    _emit(service.reject(proposal_id, reason))
