from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path

from current_state_staffing_test_helpers import publish_current_state_staffing_from_legacy
from pm_agent.current_state_staffing import service as current_state_staffing_service
from pm_agent.database.bootstrap import main as init_db
from pm_agent.rules import scoring
from pm_agent.use_cases.resource_planning import AllocationRequest, ResourcePlanningService
from pm_agent.use_cases.weekly_report import WeeklyReportService


def _seed_basic_projects(con: sqlite3.Connection) -> None:
    con.executemany(
        """
        INSERT INTO projects
            (id, name, jira_key, status, priority, start_date)
        VALUES (?, ?, ?, 'active', ?, '2026-01-01')
        """,
        [
            ("project-atlas-990001", "Project Atlas", "990001", 1),
            ("project-beacon-990002", "Project Beacon", "990002", 2),
        ],
    )


def test_confirm_allocation_reuses_existing_active_assignment(isolated_db: Path) -> None:
    init_db(quiet=True)
    con = sqlite3.connect(isolated_db)
    try:
        _seed_basic_projects(con)
        con.execute(
            """
            INSERT INTO employees
                (id, wd_id, name, level, status, skills)
            VALUES
                ('990102', '990102', 'Alex Example', 'mid', 'active', '{"python": 0.8}')
            """
        )
        con.execute(
            """
            INSERT INTO assignments
                (employee_id, project_id, role, allocation, start_date, status)
            VALUES
                ('990102', 'project-atlas-990001', 'developer', 0.2, '2026-07-01', 'active')
            """
        )
        con.commit()
    finally:
        con.close()

    service = ResourcePlanningService()
    request = AllocationRequest(query="allocate", project_id="project-atlas-990001")
    chosen_member = scoring.ScoringResult(
        member_id="990102",
        member_name="Alex Example",
        score=0.8,
        breakdown={"availability": 0.8},
        reason_text="Already active on the project",
    )
    chosen_option = scoring.AllocationOption(
        label="方案A",
        members=[chosen_member],
        combined_score=0.8,
    )

    result = service.confirm(
        request,
        chosen_option,
        all_scored=[chosen_member],
        all_options=[chosen_option],
    )

    assert result.success is True
    assert result.decision_id is not None

    con = sqlite3.connect(isolated_db)
    con.row_factory = sqlite3.Row
    try:
        assignment_rows = con.execute(
            """
            SELECT id, employee_id, project_id, allocation, status
            FROM assignments
            WHERE employee_id = '990102' AND project_id = 'project-atlas-990001'
            """
        ).fetchall()
        decision_count = con.execute("SELECT COUNT(*) FROM decision_log").fetchone()[0]
    finally:
        con.close()

    assert len(assignment_rows) == 1
    assert assignment_rows[0]["status"] == "active"
    assert assignment_rows[0]["allocation"] == 0.2
    assert decision_count == 1


def test_weekly_report_includes_confluence_and_change_request_signals(
    isolated_db: Path,
) -> None:
    init_db(quiet=True)
    con = sqlite3.connect(isolated_db)
    try:
        _seed_basic_projects(con)
        con.execute(
            """
            INSERT INTO employees
                (id, wd_id, name, level, status, skills)
            VALUES
                ('990101', '990101', 'Blair Example', 'senior', 'active', '{"delivery": 0.9}')
            """
        )
        con.execute(
            """
            INSERT INTO assignments
                (employee_id, project_id, role, allocation, start_date, status)
            VALUES
                ('990101', 'project-atlas-990001', 'pm', 0.8, '2026-07-01', 'active')
            """
        )
        con.execute(
            """
            INSERT INTO jira_board_configs
                (id, name, project_key, base_jql, pm_project_id, active)
            VALUES
                ('atlas', 'Project Atlas', 'ATL', 'project = ATL', 'project-atlas-990001', 1)
            """
        )
        con.execute(
            """
            INSERT INTO confluence_pages
                (id, board_id, title, page_type, last_synced, last_modified, content_summary)
            VALUES
                ('990000001', 'atlas', 'Project Atlas Weekly Status', 'weekly_status',
                 '2026-07-10T09:00:00Z', '2026-07-10T08:40:00Z',
                 'Sample weekly status page for Project Atlas project sync')
            """
        )
        con.execute(
            """
            INSERT INTO change_requests
                (id, short_desc, state, priority, category, assignment_group,
                 assigned_to, requested_by, project_code, planned_start, planned_end)
            VALUES
                ('CHG-990001', 'Project Atlas release deployment', 'Implement', '2', 'Normal',
                 'Project Atlas Delivery Team', 'Blair Example', 'Casey Example', '990001',
                 '2026-07-15', '2026-07-15')
            """
        )
        con.commit()
    finally:
        con.close()

    result = WeeklyReportService().weekly(reference_date=date(2026, 7, 13))

    assert result.success is True
    report = result.data["report"]
    assert "Confluence:" in report
    assert "Project Atlas Weekly Status" in report
    assert "Change Requests:" in report
    assert "CHG-990001 | Implement | Project Atlas release deployment" in report

    raw = result.data["raw"]
    assert raw["confluence_signals"]["project-atlas-990001"]["source"] == "page_registry"
    assert raw["change_request_summaries"]["project-atlas-990001"]["open_changes"] == 1


def test_recommendation_reads_current_state_staffing_publication(
    isolated_db: Path,
) -> None:
    init_db(quiet=True)
    con = sqlite3.connect(isolated_db)
    try:
        _seed_basic_projects(con)
        con.execute(
            """
            INSERT INTO employees
                (id, wd_id, name, level, status, skills)
            VALUES
                ('990103', '990103', 'Casey Example', 'senior', 'active', '{"python": 0.9}')
            """
        )
        con.execute(
            """
            INSERT INTO assignments
                (employee_id, project_id, role, allocation, start_date, status)
            VALUES
                ('990103', 'project-atlas-990001', 'developer', 0.6, '2026-07-01', 'active')
            """
        )
        con.commit()
    finally:
        con.close()

    publish_current_state_staffing_from_legacy(
        isolated_db,
        package_id="package-allocation-current-state-r1",
    )

    with sqlite3.connect(isolated_db) as con:
        con.execute("DELETE FROM assignments")
        con.commit()

    result = ResourcePlanningService().recommend(
        AllocationRequest(
            query="allocate",
            project_id="project-atlas-990001",
            required_skills=["python"],
        )
    )

    assert result.success is True
    candidate = result.data["all_scores"][0]
    assert candidate["breakdown"]["availability"] == 0.4
    assert "已在该项目组" in candidate["reason"]


def test_recommendation_omits_publication_only_members(
    isolated_db: Path,
) -> None:
    init_db(quiet=True)
    with sqlite3.connect(isolated_db) as con:
        _seed_basic_projects(con)
        con.execute(
            """
            INSERT INTO employees
                (id, wd_id, name, level, status, skills)
            VALUES
                ('990104', '990104', 'Dana Example', 'senior', 'active', '{"python": 0.9}')
            """
        )
        con.commit()

    package = {
        "dataset_marker": "TEST_CURRENT_STATE_STAFFING",
        "package_id": "package-allocation-ghost-r1",
        "schema_version": current_state_staffing_service.PACKAGE_SCHEMA_VERSION,
        "generated_at": "2026-08-15T00:00:00+00:00",
        "source_id": "source-test-current-state-staffing",
        "publication_scope": {
            "scope_key": "test-current-state-staffing",
            "as_of_date": "2026-08-15",
            "effective_year": 2026,
            "effective_month": 8,
        },
        "manifest": {
            "member_ids": ["ghost-990201"],
            "project_ids": ["project-atlas-990001"],
            "assignment_keys": [],
        },
        "members": [
            {
                "member_id": "ghost-990201",
                "display_name": "Ghost Example",
                "status": "active",
                "role": "developer",
                "level": "senior",
                "resource_type": "LTFTE",
                "current_hiref_id": None,
                "hiref_end_date": None,
            }
        ],
        "projects": [
            {
                "project_id": "project-atlas-990001",
                "display_name": "Project Atlas",
                "status": "active",
                "priority": 1,
            }
        ],
        "assignments": [],
    }
    preview = current_state_staffing_service.preview_import(package, db_path=isolated_db)
    current_state_staffing_service.confirm_import(preview["session_id"], db_path=isolated_db)

    result = ResourcePlanningService().recommend(
        AllocationRequest(
            query="allocate",
            project_id="project-atlas-990001",
            required_skills=["python"],
        )
    )

    assert result.success is False
    assert result.message == "当前态人员负载不可用，无法生成推荐方案。"
