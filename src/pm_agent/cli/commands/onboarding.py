"""Structured data onboarding CLI commands."""

from __future__ import annotations

import json

import typer

from pm_agent.data_onboarding import service
from pm_agent.workbook_onboarding.presets import (
    get_workbook_preset,
    list_workbook_presets,
    serialize_workbook_preset,
    serialize_workbook_preset_summary,
)

onboarding_app = typer.Typer(
    help="Structured data onboarding profiles and runs",
    no_args_is_help=True,
)
profile_app = typer.Typer(
    help="Saved source profiles",
    no_args_is_help=True,
)
run_app = typer.Typer(
    help="Onboarding run inspection",
    no_args_is_help=True,
)
preset_app = typer.Typer(
    help="Packaged workbook mapping presets",
    no_args_is_help=True,
)
onboarding_app.add_typer(profile_app, name="profile")
onboarding_app.add_typer(run_app, name="run")
onboarding_app.add_typer(preset_app, name="preset")

_TERMINAL_STATUSES = {
    "saved",
    "success",
    "previewed",
    "rejected",
    "completed",
    "partially_completed",
    "already_completed",
    "retryable",
    "in_progress",
}


def _emit(value: dict[str, object]) -> None:
    typer.echo(json.dumps(value, ensure_ascii=False, sort_keys=True))
    if str(value.get("status")) not in _TERMINAL_STATUSES:
        raise typer.Exit(2)


def _failed(code: str) -> dict[str, object]:
    return {"status": "failed", "warnings": [code]}


@profile_app.command("save")
def profile_save(
    profile_key: str = typer.Option(..., "--profile-key", help="Stable source-profile key."),
    source_type: str = typer.Option("workbook", "--source-type", help="Registered source type."),
    source_locator: str = typer.Option(
        ...,
        "--source-locator",
        "--file",
        help="Approved local source locator (workbook path for the workbook source type).",
    ),
    display_name: str = typer.Option("", "--display-name", help="Human-readable profile name."),
    mapping_preset_id: str = typer.Option("", "--mapping-preset", help="Optional mapping preset identifier."),
    member_key_type: str = typer.Option("", "--member-key-type", help="Optional member key strategy override."),
    project_key_type: str = typer.Option("", "--project-key-type", help="Optional project key strategy override."),
    baseline_source: str = typer.Option("", "--baseline-source", help="Optional baseline source override."),
    adjustment_source: str = typer.Option("", "--adjustment-source", help="Optional adjustment source override."),
    conflict_policy: str = typer.Option("", "--conflict-policy", help="Optional conflict policy override."),
    plan_naming_policy: str = typer.Option("", "--plan-naming-policy", help="Optional plan naming policy override."),
    status: str = typer.Option("active", "--status", help="active / inactive"),
) -> None:
    """Create or update one saved source profile."""

    try:
        result = service.save_source_profile(
            profile_key=profile_key,
            source_type=source_type,
            source_locator=source_locator,
            display_name=display_name,
            mapping_preset_id=mapping_preset_id,
            member_key_type=member_key_type,
            project_key_type=project_key_type,
            baseline_source=baseline_source,
            adjustment_source=adjustment_source,
            conflict_policy=conflict_policy,
            plan_naming_policy=plan_naming_policy,
            status=status,
        )
    except ValueError as exc:
        _emit(_failed(str(exc)))
        return
    _emit(result)


@profile_app.command("show")
def profile_show(
    profile_key: str = typer.Option(..., "--profile-key"),
) -> None:
    """Show one saved source profile."""

    try:
        result = service.show_source_profile(profile_key)
    except ValueError as exc:
        _emit(_failed(str(exc)))
        return
    _emit(result)


@profile_app.command("list")
def profile_list(
    status: str = typer.Option("", "--status", help="Optional active / inactive filter."),
) -> None:
    """List saved source profiles."""

    try:
        result = service.list_source_profiles(status=status or None)
    except ValueError as exc:
        _emit(_failed(str(exc)))
        return
    _emit(result)


@preset_app.command("list")
def preset_list() -> None:
    """List packaged workbook mapping presets."""

    _emit(
        {
            "status": "success",
            "mapping_presets": [
                serialize_workbook_preset_summary(preset)
                for preset in list_workbook_presets()
            ],
        }
    )


@preset_app.command("show")
def preset_show(
    mapping_preset_id: str = typer.Option(..., "--mapping-preset"),
) -> None:
    """Show one packaged workbook mapping preset."""

    try:
        preset = get_workbook_preset(mapping_preset_id.strip())
    except ValueError as exc:
        code = str(exc)
        if code == "WORKBOOK_MAPPING_PRESET_UNKNOWN":
            code = "DATA_ONBOARDING_WORKBOOK_MAPPING_PRESET_INVALID"
        _emit(_failed(code))
        return
    _emit({"status": "success", "mapping_preset": serialize_workbook_preset(preset)})


@onboarding_app.command("preview")
def onboarding_preview(
    profile_key: str = typer.Option(..., "--profile-key"),
) -> None:
    """Preview one source-profile onboarding run."""

    try:
        result = service.preview_source_profile(profile_key)
    except ValueError as exc:
        _emit(_failed(str(exc)))
        return
    _emit(result)


@onboarding_app.command("confirm")
def onboarding_confirm(
    run_id: str = typer.Option(..., "--run-id"),
    recover_running: bool = typer.Option(
        False,
        "--recover-running",
        help="Recover and retry a previously abandoned running onboarding attempt.",
    ),
) -> None:
    """Confirm one previewed onboarding run."""

    try:
        result = service.confirm_onboarding_run(
            run_id,
            recover_running=recover_running,
        )
    except ValueError as exc:
        _emit(_failed(str(exc)))
        return
    except RuntimeError as exc:
        _emit(_failed(str(exc)))
        return
    _emit(result)


@run_app.command("show")
def run_show(
    run_id: str = typer.Option(..., "--run-id"),
) -> None:
    """Inspect one onboarding run plus its domain linkage."""

    try:
        result = service.show_onboarding_run(run_id)
    except ValueError as exc:
        _emit(_failed(str(exc)))
        return
    _emit(result)
