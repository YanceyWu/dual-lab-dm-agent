from __future__ import annotations

import json
import sqlite3
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path

from openpyxl import Workbook
from typer.testing import CliRunner

from pm_agent.cli.app import app
from pm_agent.data_onboarding import repository as onboarding_repository
from pm_agent.data_onboarding import service as data_onboarding_service
from pm_agent.data_onboarding import workbook_source
from pm_agent.database import repository as legacy_repository
from pm_agent.database.bootstrap import main as init_db
from pm_agent.resource_intelligence.read_model import get_effective_capacity
from pm_agent.use_cases.layered_project_health import execute_layered_project_health_review
from pm_agent.use_cases.service import UseCaseRequest
from pm_agent.workbook_onboarding.presets import (
    DEFAULT_WORKBOOK_MAPPING_PRESET_ID,
    WORKBOOK_MAPPING_PRESET_ID_WITH_ALIASES,
)
from pm_agent.workbook_onboarding.parser import EXPECTED_HEADERS
from pm_agent.workbook_onboarding import service as workbook_service
from pm_agent.workbook_onboarding.service import (
    confirm_workbook_candidate as workbook_confirm_candidate,
)
from pm_agent.workforce_planning_import.service import (
    confirm_import as confirm_workforce_import,
    preview_import as preview_workforce_import,
)

runner = CliRunner()
ROOT = Path(__file__).resolve().parents[1]


def _invoke(*args: str):
    return runner.invoke(app, list(args))


def _payload(result) -> dict:
    return json.loads(result.stdout)


def _sample_json(name: str) -> dict:
    return json.loads((ROOT / "sample-data" / "json" / name).read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def _seed_workforce_publication(db_path: Path) -> None:
    preview = preview_workforce_import(
        _sample_json("workforce_planning_import.sample.json"),
        db_path=db_path,
    )
    confirm_workforce_import(preview["session_id"], db_path=db_path)


def _seed_project_health_boards(db_path: Path) -> None:
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            INSERT INTO jira_board_configs
                (id,name,project_key,base_jql,pm_project_id,active)
            VALUES
                ('atlas-board','Atlas Board','ATLAS','project = ATLAS','project-synthetic-atlas',1),
                ('beacon-board','Beacon Board','BEACON','project = BEACON','project-synthetic-beacon',1)
            """
        )


def _write_workbook(
    path: Path,
    *,
    setup_rows: list[list[object]],
    member_rows: list[list[object]],
    project_rows: list[list[object]],
    allocation_rows: list[list[object]],
    capacity_rows: list[list[object]],
    sheet_names: tuple[str, str, str, str, str] = (
        "Setup",
        "Members",
        "Projects",
        "Allocations",
        "Capacity",
    ),
    header_overrides: dict[str, list[str]] | None = None,
) -> Path:
    workbook = Workbook()
    first = workbook.active
    first.title = sheet_names[0]
    for title in sheet_names[1:]:
        workbook.create_sheet(title)
    header_overrides = header_overrides or {}
    logical_sheet_names = ("Setup", "Members", "Projects", "Allocations", "Capacity")
    rows_by_sheet = {
        "Setup": setup_rows,
        "Members": member_rows,
        "Projects": project_rows,
        "Allocations": allocation_rows,
        "Capacity": capacity_rows,
    }
    for logical_name, worksheet in zip(logical_sheet_names, workbook.worksheets, strict=True):
        worksheet.append(header_overrides.get(logical_name, EXPECTED_HEADERS[logical_name]))
        for row in rows_by_sheet[logical_name]:
            worksheet.append(row)
    workbook.save(path)
    return path


def _baseline_workbook(
    path: Path,
    *,
    allocation_value: float = 0.5,
    include_capacity: bool = False,
    sheet_names: tuple[str, str, str, str, str] = (
        "Setup",
        "Members",
        "Projects",
        "Allocations",
        "Capacity",
    ),
    header_overrides: dict[str, list[str]] | None = None,
) -> Path:
    return _write_workbook(
        path,
        setup_rows=[["FY26 Q4 Baseline", "2026-08-15", "2026-09", "2026-09"]],
        member_rows=[
            ["WD100001", "Alex Example", "LTFTE", "active", None, None, "Engineer", 7, "2026-09-01", None]
        ],
        project_rows=[["RP-PROJ-001", "Project Atlas", "active", 2, "2026-09-01", "2026-12-31"]],
        allocation_rows=[["WD100001", "RP-PROJ-001", "2026-09", allocation_value]],
        capacity_rows=[["WD100001", "2026-09", 0.0, 0.0, 0.0]] if include_capacity else [],
        sheet_names=sheet_names,
        header_overrides=header_overrides,
    )


def _confirm_staffing_adjustment(
    *,
    project_id: str,
    member_id: str,
    plan_version_id: str,
    month: str,
    allocation: float,
) -> None:
    proposal_id = "proposal-data-onboarding-adjustment-001"
    token = "token-data-onboarding-adjustment-001"
    legacy_repository.create_staffing_proposal(
        {
            "proposal_id": proposal_id,
            "expires_at": (
                datetime.now(timezone.utc) + timedelta(days=1)
            ).isoformat(timespec="seconds"),
            "confirmation_token": token,
            "request": {
                "project_id": project_id,
                "start_period": month,
                "role": "Engineer",
            },
            "evidence": {},
            "proposal": {
                "plan_version_id": plan_version_id,
                "periods": [{"year": 2026, "month": 9}],
                "selections": [{"member_id": member_id, "allocation": allocation}],
                "candidates": [],
            },
        }
    )
    result = legacy_repository.confirm_staffing_proposal(
        proposal_id,
        token,
        {
            "plan_version_id": plan_version_id,
            "periods": [{"year": 2026, "month": 9}],
            "selections": [{"member_id": member_id, "allocation": allocation}],
            "candidates": [],
        },
    )
    assert result["status"] == "confirmed"


ALIAS_SHEET_NAMES = (
    "Plan Setup",
    "Team Members",
    "Project List",
    "Project Allocations",
    "Member Capacity",
)

ALIAS_HEADERS = {
    "Setup": ["plan_name", "snapshot_date", "start_month", "end_month"],
    "Members": [
        "member_key",
        "member_name",
        "fte_type",
        "status",
        "hiref_id",
        "hiref_end_date",
        "role",
        "level",
        "effective_start",
        "effective_until",
        "next_hiref",
    ],
    "Projects": [
        "project_id",
        "display_name",
        "status",
        "priority",
        "start_date",
        "target_end_date",
    ],
    "Allocations": [
        "member_key",
        "project_id",
        "month",
        "allocation_fraction",
        "open_hiref_id",
    ],
    "Capacity": [
        "member_key",
        "month",
        "leave_fraction",
        "bau_fraction",
        "non_project_allocation",
    ],
}


def test_onboarding_profile_save_preview_and_run_show_round_trip(
    isolated_db: Path, tmp_path: Path
) -> None:
    init_db(quiet=True)
    workbook_path = _baseline_workbook(tmp_path / "team-project-capacity.xlsx")

    saved = _invoke(
        "onboarding",
        "profile",
        "save",
        "--profile-key",
        "FY26 Workbook",
        "--source-type",
        "workbook",
        "--file",
        str(workbook_path),
        "--display-name",
        "FY26 Workbook Baseline",
    )
    assert saved.exit_code == 0, saved.output
    profile = _payload(saved)
    assert profile["status"] == "saved"
    assert profile["profile"]["profile_key"] == "fy26-workbook"
    assert profile["profile"]["mapping_preset_id"] == "team-project-capacity-workbook-v1"
    assert profile["profile"]["source_options"]["required_sheets"] == [
        "Setup",
        "Members",
        "Projects",
        "Allocations",
        "Capacity",
    ]

    preview_result = _invoke("onboarding", "preview", "--profile-key", "FY26 Workbook")
    assert preview_result.exit_code == 0, preview_result.output
    preview = _payload(preview_result)
    assert preview["status"] == "previewed"
    assert preview["profile"]["display_name"] == "FY26 Workbook Baseline"
    assert preview["source"]["kind"] == "local_file"
    assert preview["source"]["exists"] is True
    assert preview["plan_version"]["version_name"] == "FY26 Q4 Baseline"
    assert preview["planned_domain_operations"] == [
        {
            "capability": "workforce_planning_import",
            "counts": {
                "allocation_keys": 1,
                "members": 1,
                "monthly_allocations": 1,
                "plan_versions": 1,
                "projects": 1,
                "workforce_periods": 1,
            },
            "package_id": "package-workbook-workforce-fy26-q4-baseline-r1",
            "plan_version_id": "plan-workbook-fy26-q4-baseline",
            "schema_version": "workforce-planning-import-v1",
            "status": "planned",
        },
        {
            "capability": "current_state_staffing",
            "counts": {
                "assigned_members": 1,
                "assignments": 1,
                "members": 1,
                "projects": 1,
                "unassigned_members": 0,
            },
            "package_id": "package-workbook-current-state-fy26-q4-baseline-r1",
            "publication_scope": {
                "as_of_date": "2026-08-15",
                "effective_month": 9,
                "effective_year": 2026,
                "scope_key": "workbook-current-state-staffing",
            },
            "schema_version": "current-state-staffing-v1",
            "status": "planned",
        },
        {
            "capability": "contract_coverage",
            "counts": {
                "contract_members": 0,
                "ltfte_members": 1,
                "members": 1,
                "stfte_members": 0,
                "unknown_resource_type_members": 0,
            },
            "package_id": "package-workbook-contract-coverage-fy26-q4-baseline-r1",
            "publication_scope": {
                "as_of_date": "2026-08-15",
                "scope_key": "workbook-contract-coverage",
            },
            "schema_version": "contract-coverage-v1",
            "status": "planned",
        },
    ]
    assert preview["coverage"]["capacity"] == {
        "state": "not_provided",
        "known_member_period_count": 0,
        "unknown_member_period_count": 1,
        "explicit_zero_observation_count": 0,
    }
    assert preview["coverage"]["contract_coverage"] == {
        "state": "complete",
        "member_count": 1,
        "stfte_member_count": 0,
        "ltfte_member_count": 1,
        "contract_member_count": 0,
        "missing_contract_member_count": 0,
        "unknown_resource_type_member_count": 0,
        "as_of_date": "2026-08-15",
    }
    assert preview["coverage"]["current_state_staffing"] == {
        "state": "complete",
        "member_count": 1,
        "project_count": 1,
        "assignment_count": 1,
        "assigned_member_count": 1,
        "unassigned_member_count": 0,
        "effective_period": {
            "year": 2026,
            "month": 9,
            "as_of_date": "2026-08-15",
        },
    }

    shown = _invoke("onboarding", "run", "show", "--run-id", preview["run_id"])
    assert shown.exit_code == 0, shown.output
    run_payload = _payload(shown)
    assert run_payload["run"]["state"] == "previewed"
    assert run_payload["run"]["payload"]["status"] == "previewed"
    assert run_payload["run"]["domain_links"] == []


def test_onboarding_preset_cli_inspection_lists_and_shows_packaged_presets() -> None:
    listed = _invoke("onboarding", "preset", "list")
    assert listed.exit_code == 0, listed.output
    payload = _payload(listed)
    assert payload["status"] == "success"
    assert [item["mapping_preset_id"] for item in payload["mapping_presets"]] == [
        DEFAULT_WORKBOOK_MAPPING_PRESET_ID,
        WORKBOOK_MAPPING_PRESET_ID_WITH_ALIASES,
    ]

    shown = _invoke(
        "onboarding",
        "preset",
        "show",
        "--mapping-preset",
        WORKBOOK_MAPPING_PRESET_ID_WITH_ALIASES,
    )
    assert shown.exit_code == 0, shown.output
    show_payload = _payload(shown)
    assert show_payload["mapping_preset"]["display_name"] == "Workbook v1 alias contract"
    setup_section = next(
        section
        for section in show_payload["mapping_preset"]["sections"]
        if section["section_key"] == "setup"
    )
    assert setup_section["accepted_sheet_names"] == ["Setup", "Plan Setup"]
    assert setup_section["header_aliases"]["plan_version_name"] == ["plan_name"]


def test_onboarding_contract_coverage_summary_counts_only_uncovered_stfte_members() -> None:
    summary = workbook_source.coverage_summary(
        {
            "workforce_package": {
                "manifest": {"workforce_periods": [{"member_id": "WD100001", "month": "2026-09"}]}
            },
            "contract_coverage_package": {
                "publication_scope": {
                    "scope_key": "workbook-contract-coverage",
                    "as_of_date": "2026-08-15",
                },
                "manifest": {
                    "member_ids": ["WD100001", "WD100002"],
                    "stfte_member_ids": ["WD100001"],
                    "ltfte_member_ids": ["WD100002"],
                    "contract_member_ids": ["WD100002"],
                    "unknown_resource_type_member_ids": [],
                },
                "members": [
                    {
                        "member_id": "WD100001",
                        "display_name": "Alex Example",
                        "status": "active",
                        "resource_type": "STFTE",
                        "current_hiref_id": None,
                        "hiref_end_date": None,
                    },
                    {
                        "member_id": "WD100002",
                        "display_name": "Blair Example",
                        "status": "active",
                        "resource_type": "LTFTE",
                        "current_hiref_id": "HIREF-002",
                        "hiref_end_date": "2026-12-31",
                    },
                ],
            },
        }
    )

    assert summary["contract_coverage"] == {
        "state": "partial",
        "member_count": 2,
        "stfte_member_count": 1,
        "ltfte_member_count": 1,
        "contract_member_count": 1,
        "missing_contract_member_count": 1,
        "unknown_resource_type_member_count": 0,
        "as_of_date": "2026-08-15",
    }


def test_onboarding_profile_persists_explicit_preset_selection_and_projects_metadata(
    isolated_db: Path, tmp_path: Path
) -> None:
    init_db(quiet=True)
    workbook_path = _baseline_workbook(
        tmp_path / "alias-profile.xlsx",
        sheet_names=ALIAS_SHEET_NAMES,
        header_overrides=ALIAS_HEADERS,
    )

    saved = _invoke(
        "onboarding",
        "profile",
        "save",
        "--profile-key",
        "alias-profile",
        "--file",
        str(workbook_path),
        "--mapping-preset",
        WORKBOOK_MAPPING_PRESET_ID_WITH_ALIASES,
    )
    assert saved.exit_code == 0, saved.output
    payload = _payload(saved)
    assert payload["profile"]["mapping_preset_id"] == WORKBOOK_MAPPING_PRESET_ID_WITH_ALIASES
    assert payload["profile"]["mapping_preset"]["display_name"] == "Workbook v1 alias contract"
    assert payload["profile"]["source_options"]["sheet_aliases"]["Setup"] == ["Plan Setup"]

    shown = _invoke("onboarding", "profile", "show", "--profile-key", "alias-profile")
    assert shown.exit_code == 0, shown.output
    shown_payload = _payload(shown)
    assert shown_payload["profile"]["mapping_preset_id"] == WORKBOOK_MAPPING_PRESET_ID_WITH_ALIASES
    assert shown_payload["profile"]["mapping_preset"]["status"] == "active"

    listed = _invoke("onboarding", "profile", "list")
    assert listed.exit_code == 0, listed.output
    listed_payload = _payload(listed)
    alias_profile = next(
        item for item in listed_payload["profiles"] if item["profile_key"] == "alias-profile"
    )
    assert alias_profile["mapping_preset"]["mapping_preset_id"] == (
        WORKBOOK_MAPPING_PRESET_ID_WITH_ALIASES
    )


def test_onboarding_profile_save_rejects_unknown_workbook_mapping_preset(
    tmp_path: Path,
) -> None:
    workbook_path = _baseline_workbook(tmp_path / "unknown-preset.xlsx")

    failed = _invoke(
        "onboarding",
        "profile",
        "save",
        "--profile-key",
        "bad-preset",
        "--file",
        str(workbook_path),
        "--mapping-preset",
        "workbook-preset-does-not-exist",
    )
    assert failed.exit_code == 2
    assert _payload(failed) == {
        "status": "failed",
        "warnings": ["DATA_ONBOARDING_WORKBOOK_MAPPING_PRESET_INVALID"],
    }


def test_onboarding_profile_show_and_list_tolerate_unknown_saved_preset(
    isolated_db: Path, tmp_path: Path
) -> None:
    init_db(quiet=True)
    workbook_path = _baseline_workbook(tmp_path / "stale-profile.xlsx")
    saved = data_onboarding_service.save_source_profile(
        profile_key="stale-profile",
        source_type="workbook",
        source_locator=str(workbook_path),
        db_path=isolated_db,
    )
    assert saved["status"] == "saved"

    with sqlite3.connect(isolated_db) as connection:
        connection.execute(
            """
            UPDATE onboarding_profiles
            SET mapping_preset_id=?
            WHERE profile_key=?
            """,
            ["stale-workbook-preset", "stale-profile"],
        )
        connection.commit()

    shown = data_onboarding_service.show_source_profile(
        "stale-profile",
        db_path=isolated_db,
    )
    assert shown["status"] == "success"
    assert shown["profile"]["mapping_preset_id"] == "stale-workbook-preset"
    assert shown["profile"]["mapping_preset"] == {
        "source_type": "workbook",
        "mapping_preset_id": "stale-workbook-preset",
        "display_name": None,
        "status": "unknown",
    }

    listed = data_onboarding_service.list_source_profiles(db_path=isolated_db)
    assert listed["status"] == "success"
    stale_profile = next(
        item for item in listed["profiles"] if item["profile_key"] == "stale-profile"
    )
    assert stale_profile["mapping_preset"]["status"] == "unknown"


def test_onboarding_preview_includes_preset_resolution_details(
    isolated_db: Path, tmp_path: Path
) -> None:
    init_db(quiet=True)
    workbook_path = _baseline_workbook(
        tmp_path / "alias-preview.xlsx",
        sheet_names=ALIAS_SHEET_NAMES,
        header_overrides=ALIAS_HEADERS,
        include_capacity=True,
    )
    assert _invoke(
        "onboarding",
        "profile",
        "save",
        "--profile-key",
        "alias-preview",
        "--file",
        str(workbook_path),
        "--mapping-preset",
        WORKBOOK_MAPPING_PRESET_ID_WITH_ALIASES,
    ).exit_code == 0

    preview_result = _invoke("onboarding", "preview", "--profile-key", "alias-preview")
    assert preview_result.exit_code == 0, preview_result.output
    payload = _payload(preview_result)
    assert payload["status"] == "previewed"
    assert payload["source_contract"]["mapping_preset"]["mapping_preset_id"] == (
        WORKBOOK_MAPPING_PRESET_ID_WITH_ALIASES
    )
    assert payload["source_contract"]["resolution"]["matched_via_alias"] is True
    sections = {
        section["section_key"]: section
        for section in payload["source_contract"]["resolution"]["sections"]
    }
    assert sections["setup"]["resolved_sheet_name"] == "Plan Setup"
    assert sections["setup"]["matched_via_alias"] is True
    assert any(
        match["field_key"] == "plan_version_name"
        and match["resolved_header_name"] == "plan_name"
        and match["matched_via_alias"] is True
        for match in sections["setup"]["header_matches"]
    )
    warning_codes = {item["code"] for item in payload["warnings"]}
    assert "WORKBOOK_SHEET_ALIAS_USED" in warning_codes
    assert "WORKBOOK_HEADER_ALIAS_USED" in warning_codes


def test_onboarding_preview_missing_file_preserves_preset_contract_and_unknown_preset(
    isolated_db: Path, tmp_path: Path
) -> None:
    init_db(quiet=True)
    missing_workbook = tmp_path / "missing.xlsx"
    saved = data_onboarding_service.save_source_profile(
        profile_key="missing-file",
        source_type="workbook",
        source_locator=str(missing_workbook),
        db_path=isolated_db,
    )
    assert saved["status"] == "saved"

    preview = data_onboarding_service.preview_source_profile(
        "missing-file",
        db_path=isolated_db,
    )
    assert preview["status"] == "rejected"
    assert preview["source_contract"]["mapping_preset"]["mapping_preset_id"] == (
        DEFAULT_WORKBOOK_MAPPING_PRESET_ID
    )
    assert preview["source_contract"]["resolution"] is None
    assert preview["blockers"][0]["code"] == "DATA_ONBOARDING_SOURCE_LOCATOR_NOT_FOUND"

    with sqlite3.connect(isolated_db) as connection:
        connection.execute(
            """
            UPDATE onboarding_profiles
            SET mapping_preset_id=?
            WHERE profile_key=?
            """,
            ["stale-workbook-preset", "missing-file"],
        )
        connection.commit()

    stale_preview = data_onboarding_service.preview_source_profile(
        "missing-file",
        db_path=isolated_db,
    )
    assert stale_preview["status"] == "rejected"
    assert stale_preview["source_contract"]["mapping_preset"] == {
        "source_type": "workbook",
        "mapping_preset_id": "stale-workbook-preset",
        "display_name": None,
        "status": "unknown",
    }
    assert stale_preview["blockers"][0]["code"] == "WORKBOOK_MAPPING_PRESET_UNKNOWN"


def test_onboarding_confirm_records_linkage_and_updates_profile(
    isolated_db: Path, tmp_path: Path
) -> None:
    init_db(quiet=True)
    workbook_path = _baseline_workbook(
        tmp_path / "team-project-capacity-with-capacity.xlsx",
        include_capacity=True,
    )

    saved = _invoke(
        "onboarding",
        "profile",
        "save",
        "--profile-key",
        "current-baseline",
        "--file",
        str(workbook_path),
    )
    assert saved.exit_code == 0, saved.output

    preview = _payload(_invoke("onboarding", "preview", "--profile-key", "current-baseline"))
    confirmed_result = _invoke("onboarding", "confirm", "--run-id", preview["run_id"])
    assert confirmed_result.exit_code == 0, confirmed_result.output
    confirmed = _payload(confirmed_result)
    assert confirmed["status"] == "completed"
    assert confirmed["publish_summary"] == {
        "completed_operation_count": 4,
        "partial_publication": False,
        "rejected_operation_count": 0,
    }
    operations = {
        item["capability"]: item for item in confirmed["published_domain_operations"]
    }
    assert operations["workforce_planning_import"]["domain_publication_id"] is not None
    assert operations["current_state_staffing"]["domain_publication_id"] is not None
    assert operations["contract_coverage"]["domain_publication_id"] is not None
    assert operations["resource_intelligence"]["domain_publication_id"] is not None

    shown_profile = _invoke(
        "onboarding",
        "profile",
        "show",
        "--profile-key",
        "current-baseline",
    )
    assert shown_profile.exit_code == 0, shown_profile.output
    profile = _payload(shown_profile)
    assert profile["profile"]["current_revision"] == 1
    assert profile["profile"]["last_successful_run_id"] == preview["run_id"]

    shown_run = _invoke("onboarding", "run", "show", "--run-id", preview["run_id"])
    assert shown_run.exit_code == 0, shown_run.output
    run_payload = _payload(shown_run)
    assert run_payload["run"]["state"] == "completed"
    assert len(run_payload["run"]["domain_links"]) == 4

    repeated_confirm = _invoke("onboarding", "confirm", "--run-id", preview["run_id"])
    assert repeated_confirm.exit_code == 0, repeated_confirm.output
    repeated = _payload(repeated_confirm)
    assert repeated["status"] == "completed"
    assert repeated["replay_identity"]["idempotent"] is True

    next_preview = _invoke("onboarding", "preview", "--profile-key", "current-baseline")
    assert next_preview.exit_code == 0, next_preview.output
    replayed_preview = _payload(next_preview)
    assert replayed_preview["status"] == "previewed"
    assert replayed_preview["revision_candidate"] == 2
    assert replayed_preview["plan_version"]["version_name"] == "FY26 Q4 Baseline-v2"


def test_onboarding_preview_preserves_workbook_conflict_blocking(
    isolated_db: Path, tmp_path: Path
) -> None:
    init_db(quiet=True)
    baseline_path = _baseline_workbook(tmp_path / "baseline.xlsx", allocation_value=0.5)

    assert _invoke(
        "onboarding",
        "profile",
        "save",
        "--profile-key",
        "baseline",
        "--file",
        str(baseline_path),
    ).exit_code == 0
    baseline_preview = _payload(_invoke("onboarding", "preview", "--profile-key", "baseline"))
    baseline_confirm = _payload(
        _invoke("onboarding", "confirm", "--run-id", baseline_preview["run_id"])
    )
    current_plan_id = baseline_confirm["plan_version"]["plan_version_id"]

    _confirm_staffing_adjustment(
        project_id="RP-PROJ-001",
        member_id="WD100001",
        plan_version_id=current_plan_id,
        month="2026-09",
        allocation=0.1,
    )

    conflicting_path = _baseline_workbook(
        tmp_path / "conflicting.xlsx",
        allocation_value=0.5,
    )
    assert _invoke(
        "onboarding",
        "profile",
        "save",
        "--profile-key",
        "baseline",
        "--file",
        str(conflicting_path),
    ).exit_code == 0
    conflicting_preview = _payload(
        _invoke("onboarding", "preview", "--profile-key", "baseline")
    )
    assert conflicting_preview["status"] == "rejected"
    assert conflicting_preview["conflicts"][0]["conflict_code"] == (
        "WORKBOOK_ONBOARDING_CONFIRMED_ADJUSTMENT_CONFLICT"
    )

    absorbed_path = _baseline_workbook(
        tmp_path / "absorbed.xlsx",
        allocation_value=0.6,
    )
    assert _invoke(
        "onboarding",
        "profile",
        "save",
        "--profile-key",
        "baseline",
        "--file",
        str(absorbed_path),
    ).exit_code == 0
    absorbed_preview = _payload(
        _invoke("onboarding", "preview", "--profile-key", "baseline")
    )
    assert absorbed_preview["status"] == "previewed"
    assert absorbed_preview["conflicts"] == []


def test_onboarding_confirm_rejects_when_profile_definition_changes_after_preview(
    isolated_db: Path, tmp_path: Path
) -> None:
    init_db(quiet=True)
    first_workbook = _baseline_workbook(tmp_path / "first.xlsx", allocation_value=0.4)
    second_workbook = _baseline_workbook(tmp_path / "second.xlsx", allocation_value=0.7)

    assert _invoke(
        "onboarding",
        "profile",
        "save",
        "--profile-key",
        "mutable-profile",
        "--file",
        str(first_workbook),
    ).exit_code == 0
    preview = _payload(_invoke("onboarding", "preview", "--profile-key", "mutable-profile"))

    assert _invoke(
        "onboarding",
        "profile",
        "save",
        "--profile-key",
        "mutable-profile",
        "--file",
        str(second_workbook),
    ).exit_code == 0
    confirmed = _invoke("onboarding", "confirm", "--run-id", preview["run_id"])
    assert confirmed.exit_code == 0, confirmed.output
    payload = _payload(confirmed)
    assert payload["status"] == "rejected"
    assert payload["blockers"][-1]["code"] == "DATA_ONBOARDING_PROFILE_CHANGED"

    assert _invoke(
        "onboarding",
        "profile",
        "save",
        "--profile-key",
        "mutable-profile",
        "--file",
        str(first_workbook),
    ).exit_code == 0
    fresh_preview_result = _invoke(
        "onboarding", "preview", "--profile-key", "mutable-profile"
    )
    assert fresh_preview_result.exit_code == 0, fresh_preview_result.output
    fresh_preview = _payload(fresh_preview_result)
    assert fresh_preview["status"] == "previewed"
    assert fresh_preview["run_id"] != preview["run_id"]

    replayed_preview_result = _invoke(
        "onboarding", "preview", "--profile-key", "mutable-profile"
    )
    assert replayed_preview_result.exit_code == 0, replayed_preview_result.output
    replayed_preview = _payload(replayed_preview_result)
    assert replayed_preview["status"] == "previewed"
    assert replayed_preview["run_id"] == fresh_preview["run_id"]


def test_onboarding_failed_confirm_can_retry_same_run(
    isolated_db: Path, tmp_path: Path, monkeypatch
) -> None:
    init_db(quiet=True)
    workbook_path = _baseline_workbook(tmp_path / "retryable.xlsx")
    assert _invoke(
        "onboarding",
        "profile",
        "save",
        "--profile-key",
        "retryable-profile",
        "--file",
        str(workbook_path),
    ).exit_code == 0
    preview = _payload(_invoke("onboarding", "preview", "--profile-key", "retryable-profile"))

    calls = {"count": 0}

    class UnexpectedConfirmError(Exception):
        pass

    def flaky_confirm(candidate, *, db_path=None):
        calls["count"] += 1
        if calls["count"] == 1:
            raise UnexpectedConfirmError("DATA_ONBOARDING_TEST_RETRYABLE_FAILURE")
        return workbook_confirm_candidate(candidate, db_path=db_path)

    monkeypatch.setattr(workbook_source, "confirm_workbook_candidate", flaky_confirm)

    failed = _invoke("onboarding", "confirm", "--run-id", preview["run_id"])
    assert failed.exit_code == 2
    assert _payload(failed) == {
        "status": "failed",
        "warnings": ["DATA_ONBOARDING_CONFIRMATION_FAILED"],
    }

    retried = _invoke("onboarding", "confirm", "--run-id", preview["run_id"])
    assert retried.exit_code == 0, retried.output
    assert _payload(retried)["status"] == "completed"


def test_onboarding_confirm_succeeds_even_if_legacy_profile_success_hook_is_patched(
    isolated_db: Path, tmp_path: Path, monkeypatch
) -> None:
    init_db(quiet=True)
    workbook_path = _baseline_workbook(tmp_path / "success-hook.xlsx")
    assert _invoke(
        "onboarding",
        "profile",
        "save",
        "--profile-key",
        "success-hook",
        "--file",
        str(workbook_path),
    ).exit_code == 0
    preview = _payload(_invoke("onboarding", "preview", "--profile-key", "success-hook"))

    def broken_record_profile_success(*args, **kwargs):
        raise AssertionError("record_profile_success should not be called")

    monkeypatch.setattr(
        data_onboarding_service.repository,
        "record_profile_success",
        broken_record_profile_success,
    )

    confirmed = _invoke("onboarding", "confirm", "--run-id", preview["run_id"])
    assert confirmed.exit_code == 0, confirmed.output
    assert _payload(confirmed)["status"] == "completed"


def test_onboarding_workforce_in_progress_is_retryable_not_cached_rejection(
    isolated_db: Path, tmp_path: Path, monkeypatch
) -> None:
    init_db(quiet=True)
    workbook_path = _baseline_workbook(tmp_path / "in-progress.xlsx")
    assert _invoke(
        "onboarding",
        "profile",
        "save",
        "--profile-key",
        "in-progress",
        "--file",
        str(workbook_path),
    ).exit_code == 0
    preview = _payload(_invoke("onboarding", "preview", "--profile-key", "in-progress"))

    monkeypatch.setattr(
        workbook_service,
        "preview_workforce_import",
        lambda *args, **kwargs: {"status": "in_progress", "session_id": "wf-session-1"},
    )

    failed = _invoke("onboarding", "confirm", "--run-id", preview["run_id"])
    assert failed.exit_code == 2
    assert _payload(failed) == {
        "status": "failed",
        "warnings": ["WORKBOOK_ONBOARDING_WORKFORCE_IN_PROGRESS"],
    }

    retryable_preview = _invoke("onboarding", "preview", "--profile-key", "in-progress")
    assert retryable_preview.exit_code == 0, retryable_preview.output
    payload = _payload(retryable_preview)
    assert payload["status"] == "retryable"
    assert payload["run_id"] == preview["run_id"]


def test_partially_completed_onboarding_run_can_resume_same_run_id(
    isolated_db: Path, tmp_path: Path, monkeypatch
) -> None:
    init_db(quiet=True)
    workbook_path = _baseline_workbook(
        tmp_path / "partial-resume.xlsx",
        include_capacity=True,
    )
    assert _invoke(
        "onboarding",
        "profile",
        "save",
        "--profile-key",
        "partial-resume",
        "--file",
        str(workbook_path),
    ).exit_code == 0
    preview = _payload(_invoke("onboarding", "preview", "--profile-key", "partial-resume"))

    original_confirm_capacity_import = workbook_service.confirm_capacity_import
    calls = {"count": 0}

    def flaky_confirm_capacity(session_id: str, *, db_path=None):
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("RESOURCE_CAPACITY_TEST_FAILURE")
        return original_confirm_capacity_import(session_id, db_path=db_path)

    monkeypatch.setattr(
        workbook_service,
        "confirm_capacity_import",
        flaky_confirm_capacity,
    )

    first_confirm = _invoke("onboarding", "confirm", "--run-id", preview["run_id"])
    assert first_confirm.exit_code == 0, first_confirm.output
    partial = _payload(first_confirm)
    assert partial["status"] == "partially_completed"
    operations = {
        item["capability"]: item for item in partial["published_domain_operations"]
    }
    assert operations["workforce_planning_import"]["status"] == "completed"
    assert operations["current_state_staffing"]["status"] == "completed"
    assert operations["contract_coverage"]["status"] == "completed"
    assert operations["resource_intelligence"]["status"] == "failed"
    assert operations["resource_intelligence"]["domain_session_id"] is not None
    assert (
        operations["resource_intelligence"]["details"]["failure_code"]
        == "RESOURCE_CAPACITY_TEST_FAILURE"
    )

    retried_confirm = _invoke("onboarding", "confirm", "--run-id", preview["run_id"])
    assert retried_confirm.exit_code == 0, retried_confirm.output
    completed = _payload(retried_confirm)
    assert completed["status"] == "completed"
    final_operations = {
        item["capability"]: item for item in completed["published_domain_operations"]
    }
    assert final_operations["current_state_staffing"]["status"] == "completed"
    assert final_operations["contract_coverage"]["status"] == "completed"
    assert final_operations["resource_intelligence"]["status"] == "completed"
    shown_profile = _payload(
        _invoke("onboarding", "profile", "show", "--profile-key", "partial-resume")
    )
    assert shown_profile["profile"]["current_revision"] == 1

    with sqlite3.connect(isolated_db) as connection:
        publication_count = connection.execute(
            "SELECT COUNT(*) FROM current_state_staffing_publications"
        ).fetchone()[0]
    assert publication_count == 1


def test_running_onboarding_run_is_recovered_and_resumable(
    isolated_db: Path, tmp_path: Path
) -> None:
    init_db(quiet=True)
    workbook_path = _baseline_workbook(tmp_path / "running-recovery.xlsx")
    assert _invoke(
        "onboarding",
        "profile",
        "save",
        "--profile-key",
        "running-recovery",
        "--file",
        str(workbook_path),
    ).exit_code == 0
    preview = _payload(
        _invoke("onboarding", "preview", "--profile-key", "running-recovery")
    )

    onboarding_repository.start_run_attempt(
        preview["run_id"],
        started_at="2026-08-04T00:00:00+00:00",
        db_path=isolated_db,
    )
    onboarding_repository.claim_profile_revision(
        profile_key="running-recovery",
        expected_revision=1,
        db_path=isolated_db,
    )

    blocked = _invoke("onboarding", "confirm", "--run-id", preview["run_id"])
    assert blocked.exit_code == 2
    assert _payload(blocked) == {
        "status": "failed",
        "warnings": ["DATA_ONBOARDING_RUN_IN_PROGRESS"],
    }

    recovered = _invoke(
        "onboarding",
        "confirm",
        "--run-id",
        preview["run_id"],
        "--recover-running",
    )
    assert recovered.exit_code == 0, recovered.output
    assert _payload(recovered)["status"] == "completed"


def test_two_profiles_preview_distinct_reserved_plan_identities(
    isolated_db: Path, tmp_path: Path
) -> None:
    init_db(quiet=True)
    first_workbook = _baseline_workbook(tmp_path / "profile-a.xlsx", allocation_value=0.4)
    second_workbook = _baseline_workbook(tmp_path / "profile-b.xlsx", allocation_value=0.7)

    assert _invoke(
        "onboarding",
        "profile",
        "save",
        "--profile-key",
        "profile-a",
        "--file",
        str(first_workbook),
    ).exit_code == 0
    assert _invoke(
        "onboarding",
        "profile",
        "save",
        "--profile-key",
        "profile-b",
        "--file",
        str(second_workbook),
    ).exit_code == 0

    first_preview = _payload(_invoke("onboarding", "preview", "--profile-key", "profile-a"))
    second_preview = _payload(_invoke("onboarding", "preview", "--profile-key", "profile-b"))

    assert first_preview["plan_version"] == {
        "plan_version_id": "plan-workbook-fy26-q4-baseline",
        "version_name": "FY26 Q4 Baseline",
    }
    assert second_preview["plan_version"] == {
        "plan_version_id": "plan-workbook-fy26-q4-baseline-v2",
        "version_name": "FY26 Q4 Baseline-v2",
    }


def test_onboarding_preview_rejects_if_source_changes_during_preview(
    isolated_db: Path, tmp_path: Path, monkeypatch
) -> None:
    init_db(quiet=True)
    workbook_path = _baseline_workbook(tmp_path / "source-changes.xlsx", allocation_value=0.4)
    original_preview = workbook_source.preview_workbook_import

    def preview_then_mutate(path: Path, *args, **kwargs):
        result = original_preview(path, *args, **kwargs)
        _baseline_workbook(Path(path), allocation_value=0.7)
        return result

    monkeypatch.setattr(workbook_source, "preview_workbook_import", preview_then_mutate)

    saved = data_onboarding_service.save_source_profile(
        profile_key="source-changes",
        source_type="workbook",
        source_locator=str(workbook_path),
        db_path=isolated_db,
    )
    assert saved["status"] == "saved"

    preview = data_onboarding_service.preview_source_profile(
        "source-changes",
        db_path=isolated_db,
    )
    assert preview["status"] == "rejected"
    assert preview["source_contract"] == {
        "mapping_preset": {
            "source_type": "workbook",
            "mapping_preset_id": DEFAULT_WORKBOOK_MAPPING_PRESET_ID,
            "display_name": "Team/Project + Capacity workbook v1",
            "status": "active",
        },
        "resolution": None,
    }
    assert preview["blockers"] == [
        {
            "severity": "blocker",
            "code": "DATA_ONBOARDING_SOURCE_CHANGED_DURING_PREVIEW",
            "message": "Source content changed during preview; run preview again.",
            "location": "source",
        }
    ]

    shown = data_onboarding_service.show_onboarding_run(
        preview["run_id"],
        db_path=isolated_db,
    )
    assert shown["run"]["state"] == "rejected"
    with sqlite3.connect(isolated_db) as connection:
        reservation = connection.execute(
            """
            SELECT status
            FROM data_onboarding_plan_reservations
            WHERE run_id=?
            """,
            [preview["run_id"]],
        ).fetchone()
    assert reservation is None or reservation[0] == "released"


def test_partial_retry_after_profile_edit_preserves_existing_partial_summary(
    isolated_db: Path, tmp_path: Path, monkeypatch
) -> None:
    init_db(quiet=True)
    first_workbook = _baseline_workbook(
        tmp_path / "partial-original.xlsx",
        include_capacity=True,
    )
    changed_workbook = _baseline_workbook(
        tmp_path / "partial-changed.xlsx",
        allocation_value=0.7,
        include_capacity=True,
    )
    saved = data_onboarding_service.save_source_profile(
        profile_key="partial-edited",
        source_type="workbook",
        source_locator=str(first_workbook),
        db_path=isolated_db,
    )
    assert saved["status"] == "saved"
    preview = data_onboarding_service.preview_source_profile(
        "partial-edited",
        db_path=isolated_db,
    )
    assert preview["status"] == "previewed"

    original_confirm_capacity_import = workbook_service.confirm_capacity_import
    calls = {"count": 0}

    def flaky_confirm_capacity(session_id: str, *, db_path=None):
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("RESOURCE_CAPACITY_TEST_FAILURE")
        return original_confirm_capacity_import(session_id, db_path=db_path)

    monkeypatch.setattr(
        workbook_service,
        "confirm_capacity_import",
        flaky_confirm_capacity,
    )

    partial = data_onboarding_service.confirm_onboarding_run(
        preview["run_id"],
        db_path=isolated_db,
    )
    assert partial["status"] == "partially_completed"

    resaved = data_onboarding_service.save_source_profile(
        profile_key="partial-edited",
        source_type="workbook",
        source_locator=str(changed_workbook),
        db_path=isolated_db,
    )
    assert resaved["status"] == "saved"

    blocked = data_onboarding_service.confirm_onboarding_run(
        preview["run_id"],
        db_path=isolated_db,
    )
    assert blocked["status"] == "partially_completed"
    assert blocked["retry_blocked"] is True
    assert blocked["blockers"][-1]["code"] == "DATA_ONBOARDING_PROFILE_CHANGED"

    shown = data_onboarding_service.show_onboarding_run(
        preview["run_id"],
        db_path=isolated_db,
    )
    assert shown["run"]["state"] == "partially_completed"
    persisted = shown["run"]["payload"]
    assert "retry_blocked" not in persisted
    operations = {
        item["capability"]: item for item in persisted["published_domain_operations"]
    }
    assert operations["workforce_planning_import"]["status"] == "completed"
    assert operations["current_state_staffing"]["status"] == "completed"
    assert operations["contract_coverage"]["status"] == "completed"
    assert operations["resource_intelligence"]["status"] == "failed"


def test_bootstrap_backfills_legacy_default_onboarding_profile(
    isolated_db: Path,
) -> None:
    with sqlite3.connect(isolated_db) as connection:
        connection.execute(
            """
            CREATE TABLE onboarding_profiles (
                profile_id TEXT PRIMARY KEY,
                profile_key TEXT NOT NULL UNIQUE,
                member_key_type TEXT NOT NULL,
                project_key_type TEXT NOT NULL,
                baseline_source TEXT NOT NULL,
                adjustment_source TEXT NOT NULL,
                conflict_policy TEXT NOT NULL,
                current_revision INTEGER NOT NULL DEFAULT 0 CHECK(current_revision >= 0),
                status TEXT NOT NULL CHECK(status IN ('active','inactive')),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            INSERT INTO onboarding_profiles
                (profile_id,profile_key,member_key_type,project_key_type,baseline_source,
                 adjustment_source,conflict_policy,current_revision,status,created_at,updated_at)
            VALUES
                ('onboarding-profile-default','default','workday_id','resource_portal_project_id',
                 'workbook','copilot','copilot_wins_workbook_blocked',0,'active',
                 '2026-08-04T00:00:00+00:00','2026-08-04T00:00:00+00:00')
            """
        )
        connection.commit()

    init_db(quiet=True)

    shown = _invoke("onboarding", "profile", "show", "--profile-key", "default")
    assert shown.exit_code == 0, shown.output
    payload = _payload(shown)
    assert payload["profile"]["source_type"] == "workbook"
    assert payload["profile"]["mapping_preset_id"] == "team-project-capacity-workbook-v1"
    assert (
        payload["profile"]["plan_naming_policy"]
        == "workbook_setup_name_with_auto_suffix"
    )

    preview = _invoke("onboarding", "preview", "--profile-key", "default")
    assert preview.exit_code == 0, preview.output
    preview_payload = _payload(preview)
    assert preview_payload["status"] == "rejected"
    assert preview_payload["source_contract"]["mapping_preset"]["mapping_preset_id"] == (
        DEFAULT_WORKBOOK_MAPPING_PRESET_ID
    )
    assert preview_payload["blockers"][0]["code"] == "DATA_ONBOARDING_SOURCE_LOCATOR_NOT_FOUND"


def test_onboarding_workforce_planning_json_round_trip_and_replay(
    isolated_db: Path, tmp_path: Path
) -> None:
    init_db(quiet=True)
    source_path = _write_json(
        tmp_path / "workforce-planning.json",
        _sample_json("workforce_planning_import.sample.json"),
    )

    saved = _invoke(
        "onboarding",
        "profile",
        "save",
        "--profile-key",
        "workforce-json",
        "--source-type",
        "workforce-planning-json",
        "--file",
        str(source_path),
    )
    assert saved.exit_code == 0, saved.output

    preview = _payload(_invoke("onboarding", "preview", "--profile-key", "workforce-json"))
    assert preview["status"] == "previewed"
    assert preview["source_contract"]["source_type"] == "workforce-planning-json"
    assert preview["counts"] == {
        "members": 3,
        "projects": 2,
        "plan_versions": 1,
        "monthly_allocations": 6,
        "workforce_periods": 3,
        "allocation_keys": 6,
        "explicit_zero_allocations": 3,
    }
    assert preview["planned_domain_operations"] == [
        {
            "capability": "workforce_planning_import",
            "counts": preview["counts"],
            "package_id": "package-synthetic-workforce-planning-001",
            "plan_version_id": "plan-synthetic-baseline-001",
            "schema_version": "workforce-planning-import-v1",
            "status": "planned",
        }
    ]

    confirmed = _payload(_invoke("onboarding", "confirm", "--run-id", preview["run_id"]))
    assert confirmed["status"] == "completed"
    assert confirmed["published_domain_operations"][0]["capability"] == "workforce_planning_import"
    assert confirmed["published_domain_operations"][0]["domain_publication_id"] is not None

    replay_preview = _payload(
        _invoke("onboarding", "preview", "--profile-key", "workforce-json")
    )
    assert replay_preview["status"] == "already_completed"
    assert replay_preview["confirmation_required"] is True

    replay_confirm = _payload(
        _invoke("onboarding", "confirm", "--run-id", replay_preview["run_id"])
    )
    assert replay_confirm["status"] == "completed"
    assert replay_confirm["replay_identity"]["idempotent"] is True

    shown = _payload(_invoke("onboarding", "run", "show", "--run-id", preview["run_id"]))
    assert shown["run"]["domain_links"][0]["capability"] == "workforce_planning_import"
    with sqlite3.connect(isolated_db) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM workforce_planning_publications"
        ).fetchone()[0] == 1


def test_onboarding_resource_capacity_json_preserves_capacity_reader(
    isolated_db: Path, tmp_path: Path
) -> None:
    init_db(quiet=True)
    _seed_workforce_publication(isolated_db)
    source_path = _write_json(
        tmp_path / "resource-capacity.json",
        _sample_json("resource_capacity_import.sample.json"),
    )

    assert _invoke(
        "onboarding",
        "profile",
        "save",
        "--profile-key",
        "capacity-json",
        "--source-type",
        "resource-capacity-json",
        "--file",
        str(source_path),
    ).exit_code == 0

    preview = _payload(_invoke("onboarding", "preview", "--profile-key", "capacity-json"))
    assert preview["status"] == "previewed"
    assert preview["planned_domain_operations"][0]["capability"] == "resource_intelligence"
    confirmed = _payload(_invoke("onboarding", "confirm", "--run-id", preview["run_id"]))
    assert confirmed["status"] == "completed"
    capacity = get_effective_capacity(
        "member-synthetic-001",
        2026,
        8,
        "plan-synthetic-baseline-001",
        db_path=isolated_db,
    )
    assert capacity["state"] == "known"
    assert capacity["available_capacity"] == 0.2


def test_onboarding_milestone_json_round_trip_and_no_op_replay(
    isolated_db: Path, tmp_path: Path
) -> None:
    init_db(quiet=True)
    _seed_workforce_publication(isolated_db)
    source_path = _write_json(
        tmp_path / "milestones.json",
        _sample_json("milestone_import.sample.json"),
    )

    assert _invoke(
        "onboarding",
        "profile",
        "save",
        "--profile-key",
        "milestone-json",
        "--source-type",
        "milestone-json",
        "--file",
        str(source_path),
    ).exit_code == 0

    preview = _payload(_invoke("onboarding", "preview", "--profile-key", "milestone-json"))
    assert preview["status"] == "previewed"
    assert preview["planned_domain_operations"] == [
        {
            "capability": "execution_milestones",
            "changed_milestone_count": 6,
            "counts": {"milestones": 6, "projects": 2},
            "schema_version": "milestone-import-v1",
            "status": "planned",
        }
    ]
    confirmed = _payload(_invoke("onboarding", "confirm", "--run-id", preview["run_id"]))
    assert confirmed["status"] == "completed"

    replay_preview = _payload(
        _invoke("onboarding", "preview", "--profile-key", "milestone-json")
    )
    assert replay_preview["status"] == "already_completed"
    replay_confirm = _payload(
        _invoke("onboarding", "confirm", "--run-id", replay_preview["run_id"])
    )
    assert replay_confirm["status"] == "completed"
    assert replay_confirm["replay_identity"]["idempotent"] is True

    with sqlite3.connect(isolated_db) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM execution_milestones"
        ).fetchone()[0] == 6
        assert connection.execute(
            "SELECT COUNT(*) FROM milestone_import_operations WHERE status='confirmed'"
        ).fetchone()[0] == 1


def test_onboarding_project_health_json_preserves_layered_review(
    isolated_db: Path, tmp_path: Path
) -> None:
    init_db(quiet=True)
    _seed_workforce_publication(isolated_db)
    _seed_project_health_boards(isolated_db)
    source_path = _write_json(
        tmp_path / "project-health.json",
        _sample_json("project_health_reimport.sample.json"),
    )

    assert _invoke(
        "onboarding",
        "profile",
        "save",
        "--profile-key",
        "project-health-json",
        "--source-type",
        "project-health-reimport-json",
        "--file",
        str(source_path),
    ).exit_code == 0

    preview = _payload(
        _invoke("onboarding", "preview", "--profile-key", "project-health-json")
    )
    assert preview["status"] == "previewed"
    assert preview["planned_domain_operations"][0]["capability"] == "project_health"
    confirmed = _payload(_invoke("onboarding", "confirm", "--run-id", preview["run_id"]))
    assert confirmed["status"] == "completed"

    review = execute_layered_project_health_review(
        UseCaseRequest(
            use_case_id="layered-project-health-review",
            parameters={"project_id": "project-synthetic-atlas"},
        )
    )
    assert review.status == "success"
    assert review.data["assessments"][0]["project_id"] == "project-synthetic-atlas"


def test_onboarding_json_profile_change_rejects_confirm_after_preview(
    isolated_db: Path, tmp_path: Path
) -> None:
    init_db(quiet=True)
    first = _sample_json("workforce_planning_import.sample.json")
    second = deepcopy(first)
    second["package_id"] = "package-synthetic-workforce-planning-002"
    second["source_id"] = "source-synthetic-workforce-planning-002"
    first_path = _write_json(tmp_path / "workforce-a.json", first)
    second_path = _write_json(tmp_path / "workforce-b.json", second)

    assert _invoke(
        "onboarding",
        "profile",
        "save",
        "--profile-key",
        "mutable-json",
        "--source-type",
        "workforce-planning-json",
        "--file",
        str(first_path),
    ).exit_code == 0
    preview = _payload(_invoke("onboarding", "preview", "--profile-key", "mutable-json"))

    assert _invoke(
        "onboarding",
        "profile",
        "save",
        "--profile-key",
        "mutable-json",
        "--source-type",
        "workforce-planning-json",
        "--file",
        str(second_path),
    ).exit_code == 0
    confirmed = _payload(_invoke("onboarding", "confirm", "--run-id", preview["run_id"]))
    assert confirmed["status"] == "rejected"
    assert confirmed["blockers"][-1]["code"] == "DATA_ONBOARDING_PROFILE_CHANGED"


def test_onboarding_json_preview_rejects_invalid_json_with_persisted_run(
    isolated_db: Path, tmp_path: Path
) -> None:
    init_db(quiet=True)
    source_path = tmp_path / "invalid.json"
    source_path.write_text("{not-json", encoding="utf-8")

    assert _invoke(
        "onboarding",
        "profile",
        "save",
        "--profile-key",
        "invalid-json",
        "--source-type",
        "workforce-planning-json",
        "--file",
        str(source_path),
    ).exit_code == 0
    preview = _payload(_invoke("onboarding", "preview", "--profile-key", "invalid-json"))
    assert preview["status"] == "rejected"
    assert preview["blockers"][0]["code"] == "DATA_ONBOARDING_SOURCE_JSON_INVALID"

    shown = _payload(_invoke("onboarding", "run", "show", "--run-id", preview["run_id"]))
    assert shown["run"]["state"] == "rejected"
