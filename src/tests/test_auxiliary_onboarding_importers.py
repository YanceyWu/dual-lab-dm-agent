from __future__ import annotations

import csv
import json
import sqlite3
from datetime import date
from pathlib import Path

from openpyxl import Workbook
from typer.testing import CliRunner

from pm_agent.cli.app import app
from pm_agent.dashboard import server as dashboard_server
from pm_agent.database.bootstrap import main as init_db
from pm_agent.use_cases.weekly_report import WeeklyReportService

runner = CliRunner()


def _invoke(*args: str):
    return runner.invoke(app, list(args))


def _payload(result) -> dict:
    return json.loads(result.stdout)


def _write_project_profile_workbook(path: Path, rows: list[list[object]]) -> Path:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Project Profiles"
    worksheet.append(["Synthetic project profiles"])
    worksheet.append(["Portable onboarding regression workbook"])
    worksheet.append([None] * 12)
    worksheet.append(
        [
            "Project Name",
            "Team Size",
            "Phase",
            "Phase Detail",
            "Priority",
            "Focus",
            "Objective",
            "Milestones",
            "Risks",
            "Stakeholders",
            "Special Rules",
            "Project ID",
        ]
    )
    for row in rows:
        worksheet.append(row)
    workbook.save(path)
    return path


def _write_change_request_csv(path: Path, rows: list[dict[str, str]]) -> Path:
    fieldnames = [
        "Number",
        "Short Description",
        "State",
        "Priority",
        "Change Type",
        "Assignment Group",
        "Assigned To",
        "Requested By",
        "Planned Start Date",
        "Planned End Date",
        "Project",
        "Unexpected Column",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return path


def test_onboarding_project_profile_workbook_round_trip_preserves_dashboard_projects_surface(
    isolated_db: Path,
    tmp_path: Path,
) -> None:
    init_db(quiet=True)
    with sqlite3.connect(isolated_db) as connection:
        connection.execute(
            """
            INSERT INTO projects (id, name, status, priority)
            VALUES ('project-atlas-990001', 'Project Atlas', 'active', 1)
            """
        )
        connection.commit()

    workbook_path = _write_project_profile_workbook(
        tmp_path / "project_profiles.xlsx",
        [
            [
                "Project Atlas",
                6,
                "delivery",
                "stabilization",
                1,
                "Y",
                "Complete the synthetic release cutover.",
                "2026-08-07 | Test sign-off",
                "Regression leakage | high",
                "Alex Example, Blair Example",
                "Weekly steering update",
                "project-atlas-990001",
            ]
        ],
    )

    saved = _invoke(
        "onboarding",
        "profile",
        "save",
        "--profile-key",
        "project-profiles",
        "--source-type",
        "project-profile-workbook",
        "--file",
        str(workbook_path),
    )
    assert saved.exit_code == 0, saved.output
    assert _payload(saved)["profile"]["source_type"] == "project-profile-workbook"

    preview = _payload(
        _invoke("onboarding", "preview", "--profile-key", "project-profiles")
    )
    assert preview["status"] == "previewed"
    assert preview["source_contract"]["source_type"] == "project-profile-workbook"
    assert preview["counts"] == {
        "source_rows": 1,
        "actionable_profiles": 1,
        "planned_profile_updates": 1,
        "unchanged_profiles": 0,
        "skipped_phase_rows": 0,
        "missing_project_rows": 0,
    }
    assert preview["planned_domain_operations"][0]["capability"] == "project_profile_import"
    assert preview["planned_domain_operations"][0]["counts"] == preview["counts"]
    assert preview["planned_domain_operations"][0]["publication_id"] is not None
    assert preview["planned_domain_operations"][0]["status"] == "planned"

    confirmed = _payload(_invoke("onboarding", "confirm", "--run-id", preview["run_id"]))
    assert confirmed["status"] == "completed"
    assert confirmed["published_domain_operations"][0]["capability"] == "project_profile_import"

    shown = _payload(_invoke("onboarding", "run", "show", "--run-id", preview["run_id"]))
    assert shown["run"]["state"] == "completed"
    assert shown["run"]["domain_links"][0]["capability"] == "project_profile_import"

    payload = dashboard_server.app.test_client().get("/api/projects").get_json()
    atlas = next(project for project in payload if project["id"] == "project-atlas-990001")
    assert atlas["phase"] == "delivery"
    assert atlas["objective"] == "Complete the synthetic release cutover."
    assert atlas["is_focus"] == 1

    replay_preview = _payload(
        _invoke("onboarding", "preview", "--profile-key", "project-profiles")
    )
    assert replay_preview["status"] == "already_completed"
    replay_confirm = _payload(
        _invoke("onboarding", "confirm", "--run-id", replay_preview["run_id"])
    )
    assert replay_confirm["status"] == "completed"
    assert replay_confirm["replay_identity"]["idempotent"] is True


def test_onboarding_project_profile_workbook_rejects_missing_required_sheet(
    isolated_db: Path,
    tmp_path: Path,
) -> None:
    init_db(quiet=True)
    workbook = Workbook()
    workbook.active.title = "Not Project Profiles"
    workbook_path = tmp_path / "wrong_project_profiles.xlsx"
    workbook.save(workbook_path)

    saved = _invoke(
        "onboarding",
        "profile",
        "save",
        "--profile-key",
        "bad-project-profiles",
        "--source-type",
        "project-profile-workbook",
        "--file",
        str(workbook_path),
    )
    assert saved.exit_code == 0, saved.output

    preview = _payload(
        _invoke("onboarding", "preview", "--profile-key", "bad-project-profiles")
    )
    assert preview["status"] == "rejected"
    assert preview["blockers"] == [
        {
            "severity": "blocker",
            "code": "PROJECT_PROFILE_WORKBOOK_SHEET_MISSING",
            "message": "Workbook must contain worksheet 'Project Profiles'.",
            "location": "source_locator",
        }
    ]


def test_onboarding_change_request_csv_round_trip_preserves_weekly_report_consumer(
    isolated_db: Path,
    tmp_path: Path,
) -> None:
    init_db(quiet=True)
    with sqlite3.connect(isolated_db) as connection:
        connection.execute(
            """
            INSERT INTO projects (id, name, jira_key, status, priority)
            VALUES ('project-atlas-990001', 'Project Atlas', 'ATL', 'active', 1)
            """
        )
        connection.commit()

    csv_path = _write_change_request_csv(
        tmp_path / "servicenow_changes.csv",
        [
            {
                "Number": "CHG-001",
                "Short Description": "Atlas release deployment",
                "State": "Implement",
                "Priority": "2 - High",
                "Change Type": "Normal",
                "Assignment Group": "Synthetic Delivery Team",
                "Assigned To": "Alex Example",
                "Requested By": "Requestor Example",
                "Planned Start Date": "2026-08-03 09:00:00",
                "Planned End Date": "2026-08-03 11:00:00",
                "Project": "ATL",
                "Unexpected Column": "retained as raw data",
            }
        ],
    )

    saved = _invoke(
        "onboarding",
        "profile",
        "save",
        "--profile-key",
        "change-requests",
        "--source-type",
        "servicenow-change-request-csv",
        "--file",
        str(csv_path),
    )
    assert saved.exit_code == 0, saved.output
    assert _payload(saved)["profile"]["source_type"] == "servicenow-change-request-csv"

    preview = _payload(_invoke("onboarding", "preview", "--profile-key", "change-requests"))
    assert preview["status"] == "previewed"
    assert preview["source_contract"]["source_type"] == "servicenow-change-request-csv"
    assert preview["counts"] == {
        "change_requests": 1,
        "planned_inserts": 1,
        "planned_updates": 0,
        "unchanged_records": 0,
        "project_codes": 1,
        "unmapped_columns": 1,
    }
    assert preview["planned_domain_operations"][0]["capability"] == "change_request_import"
    assert any(
        warning["code"] == "SERVICENOW_CHANGE_REQUEST_UNMAPPED_COLUMNS_STORED"
        for warning in preview["warnings"]
    )

    confirmed = _payload(_invoke("onboarding", "confirm", "--run-id", preview["run_id"]))
    assert confirmed["status"] == "completed"
    assert confirmed["published_domain_operations"][0]["capability"] == "change_request_import"

    shown = _payload(_invoke("onboarding", "run", "show", "--run-id", preview["run_id"]))
    assert shown["run"]["state"] == "completed"
    assert shown["run"]["domain_links"][0]["capability"] == "change_request_import"

    weekly = WeeklyReportService().weekly(reference_date=date(2026, 8, 4))
    assert weekly.success is True
    assert "Change Requests: 1 条开放" in weekly.data["report"]
    assert "CHG-001 | Implement | Atlas release deployment" in weekly.data["report"]

    replay_preview = _payload(
        _invoke("onboarding", "preview", "--profile-key", "change-requests")
    )
    assert replay_preview["status"] == "already_completed"
    replay_confirm = _payload(
        _invoke("onboarding", "confirm", "--run-id", replay_preview["run_id"])
    )
    assert replay_confirm["status"] == "completed"
    assert replay_confirm["replay_identity"]["idempotent"] is True
