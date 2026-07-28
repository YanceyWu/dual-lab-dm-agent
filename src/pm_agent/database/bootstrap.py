"""
pm_agent.database.bootstrap — Create all tables and views.
Run once via `pm init` or `python3 scripts/init_db.py`.
Safe to re-run (IF NOT EXISTS everywhere).
"""

from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from pm_agent.config import settings
from pm_agent.rules.identity import (
    build_default_resource_portal_id,
    build_placeholder_id,
    derive_workday_id,
    is_placeholder_identifier,
    normalize_name,
)

DDL = """
-- ────────────────────────────────────────────
-- TABLES
-- ────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS employees (
    id              TEXT PRIMARY KEY,        -- canonical Workday ID
    name            TEXT NOT NULL,
    email           TEXT UNIQUE,
    role            TEXT,                    -- 'Backend Developer'
    level           TEXT DEFAULT 'mid',      -- 'junior'|'mid'|'senior'|'lead'
    team            TEXT,
    lead_id         TEXT REFERENCES employees(id),
    max_parallel    INTEGER DEFAULT 2,       -- max concurrent projects
    status          TEXT DEFAULT 'active',   -- 'active'|'on_leave'|'offboarded'
    notes           TEXT,
    skills          TEXT DEFAULT '{}',       -- JSON: {"java": 0.8, "python": 0.6}
    metadata        TEXT DEFAULT '{}',       -- JSON: extensible
    resource_type   TEXT DEFAULT '',         -- 'LTFTE'|'STFTE'
    billing_rate    TEXT DEFAULT '',
    billing_end_date TEXT DEFAULT '',
    hiref_id        TEXT DEFAULT '',
    current_hiref   TEXT DEFAULT '',
    next_hiref      TEXT DEFAULT '',
    wd_id           TEXT DEFAULT '',         -- compatibility mirror of the canonical Workday ID
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS projects (
    id              TEXT PRIMARY KEY,        -- slug: 'payment-gateway'
    name            TEXT NOT NULL,
    jira_key        TEXT,                    -- optional external project key
    status          TEXT DEFAULT 'active',   -- 'planning'|'active'|'at_risk'|'done'
    priority        INTEGER DEFAULT 3,       -- 1 (highest) ~ 5
    lead_id         TEXT REFERENCES employees(id),
    tech_stack      TEXT DEFAULT '[]',       -- JSON: ["java","react"]
    start_date      TEXT,
    target_end      TEXT,
    actual_end      TEXT,
    notes           TEXT,
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS assignments (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id     TEXT NOT NULL REFERENCES employees(id),
    project_id      TEXT NOT NULL REFERENCES projects(id),
    role            TEXT,                    -- 'developer'|'tech_lead'|'reviewer'
    allocation      REAL NOT NULL DEFAULT 0.5
                    CHECK(allocation >= 0.0 AND allocation <= 1.0),
    start_date      TEXT,
    end_date        TEXT,                    -- NULL = ongoing
    status          TEXT DEFAULT 'active',   -- 'active'|'ended'|'planned'
    created_at      TEXT DEFAULT (datetime('now')),
    UNIQUE(employee_id, project_id, status)
);

CREATE TABLE IF NOT EXISTS action_items (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    title           TEXT NOT NULL,
    owner_id        TEXT REFERENCES employees(id),
    source          TEXT,                    -- 'meeting:2026-05-20'|'manual'
    priority        TEXT DEFAULT 'medium',   -- 'high'|'medium'|'low'
    status          TEXT DEFAULT 'open',     -- 'open'|'done'|'cancelled'
    due_date        TEXT,
    notes           TEXT,
    created_at      TEXT DEFAULT (datetime('now')),
    completed_at    TEXT
);

CREATE TABLE IF NOT EXISTS decision_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    type            TEXT NOT NULL,           -- 'allocation'|'priority'|'risk_accept'|'manual'
    description     TEXT NOT NULL,           -- human-readable summary
    context         TEXT NOT NULL,           -- JSON snapshot of state at decision time
    candidates      TEXT,                    -- JSON: [{member_id, score, breakdown}]
    chosen          TEXT NOT NULL,           -- JSON: chosen option
    alternatives    TEXT,                    -- JSON: other options considered
    outcome         TEXT DEFAULT 'pending',  -- 'pending'|'success'|'delayed'|'failed'|'cancelled'
    outcome_note    TEXT,
    outcome_at      TEXT,
    created_by      TEXT DEFAULT 'system',
    created_at      TEXT DEFAULT (datetime('now')),
    project_id      TEXT,
    member_ids      TEXT                     -- JSON: [...] redundant for fast queries
);

-- ────────────────────────────────────────────
-- CHANGE REQUESTS  (imported from ServiceNow)
-- ────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS change_requests (
    id              TEXT PRIMARY KEY,            -- SNOW number: CHG0012345
    short_desc      TEXT NOT NULL,               -- short description
    state           TEXT,                        -- New|Assess|Authorize|Scheduled|Implement|Review|Closed|Cancelled
    priority        TEXT,                        -- 1-Critical|2-High|3-Moderate|4-Low
    category        TEXT,                        -- Normal|Standard|Emergency
    assignment_group TEXT,
    assigned_to     TEXT,
    requested_by    TEXT,
    project_code    TEXT,                        -- linked project jira/SNOW code
    planned_start   TEXT,
    planned_end     TEXT,
    actual_start    TEXT,
    actual_end      TEXT,
    created_on      TEXT,
    updated_on      TEXT,
    close_code      TEXT,
    close_notes     TEXT,
    raw_data        TEXT DEFAULT '{}',           -- JSON: full row from CSV for extra fields
    imported_at     TEXT DEFAULT (datetime('now')),
    UNIQUE(id)
);

CREATE INDEX IF NOT EXISTS idx_cr_state    ON change_requests(state);
CREATE INDEX IF NOT EXISTS idx_cr_project  ON change_requests(project_code);
CREATE INDEX IF NOT EXISTS idx_cr_assigned ON change_requests(assigned_to);
CREATE INDEX IF NOT EXISTS idx_cr_start    ON change_requests(planned_start);

-- ────────────────────────────────────────────
-- JIRA Board / Stream Configurations
-- Each row = one logical delivery stream (for example, Atlas Delivery)
-- base_jql   = authoritative board filter (defines WHAT belongs to this stream)
-- version_name_pattern = SQLite LIKE pattern to match release versions for THIS stream
--              e.g. '%eRecruit%', '%BAU%', 'DCS%'
--              If NULL, no release version tracking for this stream.
-- ────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS jira_board_configs (
    id                   TEXT PRIMARY KEY,    -- stable stream slug
    name                 TEXT NOT NULL,       -- display name
    project_key          TEXT NOT NULL,       -- JIRA project key
    base_jql             TEXT NOT NULL,       -- board filter JQL (source of truth for scope)
    version_name_pattern TEXT,               -- LIKE pattern for matching release versions e.g. '%eRecruit%'
    board_id             TEXT,               -- JIRA board id (optional)
    board_url            TEXT,               -- browser URL (optional)
    pm_project_id        TEXT REFERENCES projects(id),
    active               INTEGER DEFAULT 1,
    notes                TEXT,
    created_at           TEXT DEFAULT (datetime('now')),
    updated_at           TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_jbc_project ON jira_board_configs(project_key);

-- Per-stream release version progress
-- board_id links back to jira_board_configs
-- Same JIRA version_id can appear multiple times (once per stream that tracks it)
-- progress_pct     = issue-count-based progress (done/total)
-- sp_progress_pct  = story-point-based progress (done_sp/total_sp) — primary KPI
CREATE TABLE IF NOT EXISTS jira_stream_versions (
    id                TEXT NOT NULL,         -- JIRA version id
    board_id          TEXT NOT NULL REFERENCES jira_board_configs(id),
    project_key       TEXT NOT NULL,
    name              TEXT NOT NULL,
    release_date      TEXT,
    start_date        TEXT,
    status            TEXT,                  -- unreleased|released|archived
    released          INTEGER DEFAULT 0,
    total_issues      INTEGER DEFAULT 0,
    done_issues       INTEGER DEFAULT 0,
    inprogress_issues INTEGER DEFAULT 0,
    todo_issues       INTEGER DEFAULT 0,
    progress_pct      REAL DEFAULT 0.0,      -- count-based %
    total_sp          REAL DEFAULT 0.0,      -- total story points
    done_sp           REAL DEFAULT 0.0,      -- done story points
    inprogress_sp     REAL DEFAULT 0.0,
    todo_sp           REAL DEFAULT 0.0,
    sp_progress_pct   REAL DEFAULT 0.0,      -- SP-based % (primary)
    raw_data          TEXT DEFAULT '{}',
    synced_at         TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (id, board_id)
);

CREATE INDEX IF NOT EXISTS idx_jsv_board   ON jira_stream_versions(board_id);
CREATE INDEX IF NOT EXISTS idx_jsv_date    ON jira_stream_versions(release_date);
CREATE INDEX IF NOT EXISTS idx_jsv_project ON jira_stream_versions(project_key);

-- Individual issue store — one row per issue per board
-- Allows drill-down analysis: unestimated issues, assignee breakdown, type breakdown
CREATE TABLE IF NOT EXISTS jira_issues (
    id              TEXT NOT NULL,           -- JIRA issue key
    board_id        TEXT NOT NULL REFERENCES jira_board_configs(id),
    version_id      TEXT,                    -- fixVersion id (jira_stream_versions.id)
    project_key     TEXT NOT NULL,
    summary         TEXT,
    issue_type      TEXT,                    -- Story / Bug / Task / Sub-task / Epic
    status          TEXT,
    status_category TEXT,                    -- todo / indeterminate / done
    story_points    REAL,                    -- NULL = unestimated
    assignee_id     TEXT,
    assignee_name   TEXT,
    synced_at       TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (id, board_id)
);

CREATE INDEX IF NOT EXISTS idx_ji_board   ON jira_issues(board_id);
CREATE INDEX IF NOT EXISTS idx_ji_version ON jira_issues(version_id);
CREATE INDEX IF NOT EXISTS idx_ji_status  ON jira_issues(status_category);

-- ────────────────────────────────────────────
-- INDEXES
-- ────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_assignments_employee ON assignments(employee_id, status);
CREATE INDEX IF NOT EXISTS idx_assignments_project  ON assignments(project_id, status);
CREATE INDEX IF NOT EXISTS idx_action_items_owner   ON action_items(owner_id, status);
CREATE INDEX IF NOT EXISTS idx_action_items_due     ON action_items(due_date, status);
CREATE INDEX IF NOT EXISTS idx_decision_type        ON decision_log(type, outcome);
CREATE INDEX IF NOT EXISTS idx_decision_project     ON decision_log(project_id);

-- ────────────────────────────────────────────
-- VIEWS  (query shortcuts, no stored data)
-- ────────────────────────────────────────────

DROP VIEW IF EXISTS v_member_load;
CREATE VIEW v_member_load AS
SELECT
    e.id,
    e.name,
    e.level,
    e.team,
    e.status                                                   AS employee_status,
    e.max_parallel,
    COALESCE(SUM(a.allocation), 0.0)                           AS current_load,
    COUNT(a.id)                                                AS active_projects,
    e.skills
FROM employees e
LEFT JOIN assignments a
       ON e.id = a.employee_id AND a.status = 'active'
WHERE e.status = 'active'
GROUP BY e.id;

DROP VIEW IF EXISTS v_project_team;
CREATE VIEW v_project_team AS
SELECT
    p.id           AS project_id,
    p.name         AS project_name,
    p.status       AS project_status,
    p.priority,
    p.jira_key,
    p.target_end,
    e.id           AS member_id,
    e.name         AS member_name,
    a.role,
    a.allocation
FROM projects p
JOIN assignments a ON p.id = a.project_id  AND a.status = 'active'
JOIN employees  e ON a.employee_id = e.id
ORDER BY p.priority, p.name;

DROP VIEW IF EXISTS v_overdue_actions;
CREATE VIEW v_overdue_actions AS
SELECT
    ai.*,
    e.name AS owner_name
FROM action_items ai
LEFT JOIN employees e ON ai.owner_id = e.id
WHERE ai.status = 'open'
  AND ai.due_date IS NOT NULL
  AND ai.due_date < date('now');
"""

EXTRA_DDL = """
-- ────────────────────────────────────────────
-- V1.5 / RUNTIME TABLES
-- ────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS execution_traces (
    execution_id       TEXT PRIMARY KEY,
    use_case_id        TEXT NOT NULL,
    operation          TEXT NOT NULL,
    actor              TEXT DEFAULT '',
    correlation_id     TEXT DEFAULT '',
    status             TEXT NOT NULL,
    started_at         TEXT NOT NULL,
    finished_at        TEXT NOT NULL,
    duration_ms        INTEGER NOT NULL DEFAULT 0,
    evidence_summary_json  TEXT NOT NULL DEFAULT '[]',
    freshness_summary_json TEXT NOT NULL DEFAULT '[]',
    warning_codes_json     TEXT NOT NULL DEFAULT '[]',
    proposed_write_count   INTEGER NOT NULL DEFAULT 0,
    created_at         TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_execution_traces_use_case_finished
    ON execution_traces(use_case_id, finished_at);

CREATE TABLE IF NOT EXISTS dashboard_operations (
    operation_id        TEXT PRIMARY KEY,
    action              TEXT NOT NULL,
    actor               TEXT NOT NULL,
    status              TEXT NOT NULL,
    scope_json          TEXT NOT NULL,
    token_hash          TEXT NOT NULL,
    created_at          TEXT NOT NULL,
    expires_at          TEXT NOT NULL,
    confirmed_at        TEXT DEFAULT '',
    finished_at         TEXT DEFAULT '',
    result_json         TEXT NOT NULL DEFAULT '{}',
    failure_code        TEXT DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_dashboard_operations_status_expiry
    ON dashboard_operations(status, expires_at);

CREATE TABLE IF NOT EXISTS staffing_proposals (
    proposal_id          TEXT PRIMARY KEY,
    status               TEXT NOT NULL DEFAULT 'proposed',
    created_at           TEXT NOT NULL DEFAULT (datetime('now')),
    expires_at           TEXT NOT NULL,
    confirmed_at         TEXT DEFAULT '',
    confirmation_token_hash TEXT NOT NULL UNIQUE,
    request_json         TEXT NOT NULL,
    evidence_json        TEXT NOT NULL DEFAULT '{}',
    proposal_json        TEXT NOT NULL,
    decision_id          INTEGER REFERENCES decision_log(id),
    failure_reason       TEXT DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_staffing_proposals_status_expiry
    ON staffing_proposals(status, expires_at);

CREATE TABLE IF NOT EXISTS employee_external_ids (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id     TEXT NOT NULL REFERENCES employees(id),
    system_name     TEXT NOT NULL,
    id_type         TEXT NOT NULL,
    external_id     TEXT NOT NULL,
    external_name   TEXT DEFAULT '',
    notes           TEXT DEFAULT '',
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now')),
    UNIQUE(system_name, external_id),
    UNIQUE(employee_id, system_name, id_type)
);

CREATE INDEX IF NOT EXISTS idx_employee_external_ids_employee
    ON employee_external_ids(employee_id, system_name);

CREATE TABLE IF NOT EXISTS staffing_placeholders (
    placeholder_id      TEXT PRIMARY KEY,
    display_name        TEXT NOT NULL,
    source_system       TEXT DEFAULT 'resource_portal',
    source_employee_id  TEXT DEFAULT '',
    hiref_id            TEXT DEFAULT '',
    linked_employee_id  TEXT REFERENCES employees(id),
    resource_type       TEXT DEFAULT '',
    status              TEXT DEFAULT 'planned',
    notes               TEXT DEFAULT '',
    metadata            TEXT DEFAULT '{}',
    created_at          TEXT DEFAULT (datetime('now')),
    updated_at          TEXT DEFAULT (datetime('now'))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_staffing_placeholders_source_employee
    ON staffing_placeholders(source_employee_id)
    WHERE COALESCE(source_employee_id, '') != '';

CREATE UNIQUE INDEX IF NOT EXISTS idx_staffing_placeholders_hiref
    ON staffing_placeholders(hiref_id)
    WHERE COALESCE(hiref_id, '') != '';

CREATE INDEX IF NOT EXISTS idx_staffing_placeholders_linked_employee
    ON staffing_placeholders(linked_employee_id, status);

CREATE TABLE IF NOT EXISTS plan_versions (
    plan_version_id TEXT PRIMARY KEY,
    version_name    TEXT NOT NULL,
    scenario_type   TEXT DEFAULT 'baseline', -- baseline|forecast|approved|what_if
    as_of_date      TEXT,
    version_status  TEXT DEFAULT 'active',   -- active|draft|archived
    notes           TEXT DEFAULT '',
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_plan_versions_status
    ON plan_versions(version_status, scenario_type, as_of_date);

CREATE TABLE IF NOT EXISTS monthly_allocations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id     TEXT NOT NULL REFERENCES employees(id),
    project_id      TEXT NOT NULL REFERENCES projects(id),
    year            INTEGER NOT NULL,
    month           INTEGER NOT NULL CHECK(month BETWEEN 1 AND 12),
    allocation      REAL NOT NULL DEFAULT 0.0
                    CHECK(allocation >= 0.0 AND allocation <= 1.0),
    plan_version_id TEXT NOT NULL DEFAULT ''
                    REFERENCES plan_versions(plan_version_id),
    UNIQUE(employee_id, project_id, year, month, plan_version_id)
);

CREATE INDEX IF NOT EXISTS idx_monthly_allocations_employee_month
    ON monthly_allocations(employee_id, year, month);

CREATE INDEX IF NOT EXISTS idx_monthly_allocations_project_month
    ON monthly_allocations(project_id, year, month);

CREATE TABLE IF NOT EXISTS placeholder_monthly_allocations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    placeholder_id  TEXT NOT NULL REFERENCES staffing_placeholders(placeholder_id),
    project_id      TEXT NOT NULL REFERENCES projects(id),
    year            INTEGER NOT NULL,
    month           INTEGER NOT NULL CHECK(month BETWEEN 1 AND 12),
    allocation      REAL NOT NULL DEFAULT 0.0
                    CHECK(allocation >= 0.0 AND allocation <= 1.0),
    plan_version_id TEXT NOT NULL DEFAULT ''
                    REFERENCES plan_versions(plan_version_id),
    UNIQUE(placeholder_id, project_id, year, month, plan_version_id)
);

CREATE INDEX IF NOT EXISTS idx_placeholder_allocations_placeholder_month
    ON placeholder_monthly_allocations(placeholder_id, year, month);

CREATE INDEX IF NOT EXISTS idx_placeholder_allocations_project_month
    ON placeholder_monthly_allocations(project_id, year, month);

CREATE TABLE IF NOT EXISTS hiref (
    id              TEXT PRIMARY KEY,
    project         TEXT NOT NULL,
    request_type    TEXT NOT NULL,
    start_date      TEXT NOT NULL,
    end_date        TEXT NOT NULL,
    notes           TEXT,
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_hiref_end_date
    ON hiref(end_date);

CREATE TABLE IF NOT EXISTS project_profiles (
    project_id      TEXT PRIMARY KEY REFERENCES projects(id),
    phase           TEXT DEFAULT '',
    phase_detail    TEXT DEFAULT '',
    priority_tier   INTEGER DEFAULT 2,
    focus_level     INTEGER DEFAULT 0,
    objective       TEXT DEFAULT '',
    milestones      TEXT DEFAULT '[]',
    key_risks       TEXT DEFAULT '[]',
    dependencies    TEXT DEFAULT '[]',
    tech_stack      TEXT DEFAULT '[]',
    stakeholders    TEXT DEFAULT '[]',
    decisions       TEXT DEFAULT '[]',
    special_rules   TEXT DEFAULT '',
    is_focus        INTEGER DEFAULT 0,
    updated_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS memory_facts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    category        TEXT NOT NULL,
    subject         TEXT NOT NULL,
    fact            TEXT NOT NULL,
    confidence      REAL DEFAULT 1.0,
    source          TEXT DEFAULT '',
    valid_until     TEXT,
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_memory_facts_category_subject
    ON memory_facts(category, subject);

CREATE TABLE IF NOT EXISTS use_cases (
    id                  TEXT PRIMARY KEY,
    name                TEXT NOT NULL,
    use_case_type       TEXT DEFAULT 'business',
    problem_statement   TEXT DEFAULT '',
    decision_type       TEXT DEFAULT 'status',
    source_systems_json TEXT DEFAULT '[]',
    core_tables_json    TEXT DEFAULT '[]',
    outputs_json        TEXT DEFAULT '[]',
    priority            INTEGER DEFAULT 3,
    complexity          INTEGER DEFAULT 1,
    status              TEXT DEFAULT 'active',
    owner               TEXT DEFAULT '',
    notes               TEXT DEFAULT '',
    created_at          TEXT DEFAULT (datetime('now')),
    updated_at          TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_use_cases_status_priority
    ON use_cases(status, use_case_type, priority, id);

CREATE TABLE IF NOT EXISTS data_sources (
    id                TEXT PRIMARY KEY,
    source_type       TEXT NOT NULL,
    source_name       TEXT NOT NULL,
    ingestion_mode    TEXT DEFAULT 'manual',
    refresh_sla_hours INTEGER DEFAULT 24,
    active            INTEGER DEFAULT 1,
    config_json       TEXT DEFAULT '{}',
    notes             TEXT DEFAULT '',
    created_at        TEXT DEFAULT (datetime('now')),
    updated_at        TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_data_sources_active_type
    ON data_sources(active, source_type, id);

CREATE TABLE IF NOT EXISTS sync_runs (
    id                 TEXT PRIMARY KEY,
    source_id          TEXT NOT NULL REFERENCES data_sources(id),
    run_type           TEXT DEFAULT 'manual',
    started_at         TEXT DEFAULT (datetime('now')),
    finished_at        TEXT DEFAULT '',
    status             TEXT DEFAULT 'running',
    rows_in            INTEGER DEFAULT 0,
    rows_changed       INTEGER DEFAULT 0,
    target_tables_json TEXT DEFAULT '[]',
    artifact_path      TEXT DEFAULT '',
    triggered_by       TEXT DEFAULT 'cli',
    error_message      TEXT DEFAULT '',
    notes              TEXT DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_sync_runs_source_started
    ON sync_runs(source_id, started_at);

CREATE INDEX IF NOT EXISTS idx_sync_runs_status_started
    ON sync_runs(status, started_at);

CREATE TABLE IF NOT EXISTS project_snapshots (
    id                     TEXT PRIMARY KEY,
    project_id             TEXT NOT NULL REFERENCES projects(id),
    snapshot_date          TEXT NOT NULL,
    artifact_kind          TEXT DEFAULT 'plan',
    horizon                TEXT DEFAULT 'ad_hoc',
    artifact_state         TEXT DEFAULT 'draft',
    health                 TEXT DEFAULT 'unknown',
    title                  TEXT DEFAULT '',
    summary                TEXT NOT NULL DEFAULT '',
    priorities_json        TEXT DEFAULT '[]',
    milestones_json        TEXT DEFAULT '[]',
    actions_json           TEXT DEFAULT '[]',
    risks_json             TEXT DEFAULT '[]',
    assumptions_json       TEXT DEFAULT '[]',
    decisions_json         TEXT DEFAULT '[]',
    dependencies_json      TEXT DEFAULT '[]',
    changes_json           TEXT DEFAULT '[]',
    staffing_scenario_id   TEXT REFERENCES plan_versions(plan_version_id),
    supersedes_snapshot_id TEXT REFERENCES project_snapshots(id),
    origin_context         TEXT DEFAULT '',
    generation_mode        TEXT DEFAULT 'user',
    source_run_id          TEXT REFERENCES sync_runs(id),
    created_by             TEXT DEFAULT 'user',
    created_at             TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_project_snapshots_project_date
    ON project_snapshots(project_id, snapshot_date, artifact_kind, artifact_state);

CREATE INDEX IF NOT EXISTS idx_project_snapshots_health_date
    ON project_snapshots(health, snapshot_date);

CREATE INDEX IF NOT EXISTS idx_project_snapshots_origin_date
    ON project_snapshots(origin_context, created_at);

CREATE TABLE IF NOT EXISTS jira_sprints (
    id              TEXT NOT NULL,
    board_id        TEXT NOT NULL REFERENCES jira_board_configs(id),
    name            TEXT,
    state           TEXT,
    start_date      TEXT,
    end_date        TEXT,
    goal            TEXT,
    committed_sp    REAL DEFAULT 0.0,
    delivered_sp    REAL DEFAULT 0.0,
    completion_pct  REAL DEFAULT 0.0,
    total_issues    INTEGER DEFAULT 0,
    done_issues     INTEGER DEFAULT 0,
    bug_count       INTEGER DEFAULT 0,
    defect_count    INTEGER DEFAULT 0,
    synced_at       TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (id, board_id)
);

CREATE TABLE IF NOT EXISTS jira_health_snapshots (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    board_id              TEXT NOT NULL REFERENCES jira_board_configs(id),
    version_id            TEXT,
    snapshot_date         TEXT NOT NULL,
    sprint_id             TEXT,
    sprint_name           TEXT,
    velocity_score        REAL DEFAULT 0.0,
    sprint_score          REAL DEFAULT 0.0,
    defect_score          REAL DEFAULT 0.0,
    scope_score           REAL DEFAULT 0.0,
    overall_score         REAL DEFAULT 0.0,
    overall_grade         TEXT,
    remaining_sp          REAL DEFAULT 0.0,
    done_sp               REAL DEFAULT 0.0,
    total_sp              REAL DEFAULT 0.0,
    sp_progress_pct       REAL DEFAULT 0.0,
    sprint_completion_pct REAL DEFAULT 0.0,
    new_bugs_p1p2         INTEGER DEFAULT 0,
    new_bugs_p3p4         INTEGER DEFAULT 0,
    total_defects         INTEGER DEFAULT 0,
    done_stories          INTEGER DEFAULT 0,
    scope_added_sp        REAL DEFAULT 0.0,
    scope_removed_sp      REAL DEFAULT 0.0,
    unestimated_count     INTEGER DEFAULT 0,
    unestimated_pct       REAL DEFAULT 0.0,
    raw_sprint_issues     TEXT DEFAULT '{}',
    raw_defects           TEXT DEFAULT '{}',
    summary_text          TEXT DEFAULT '',
    risks_json            TEXT DEFAULT '[]',
    created_at            TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_jira_health_board_date
    ON jira_health_snapshots(board_id, snapshot_date);

CREATE TABLE IF NOT EXISTS confluence_pages (
    id              TEXT PRIMARY KEY,
    board_id        TEXT,
    title           TEXT,
    page_type       TEXT,
    last_synced     TEXT,
    last_modified   TEXT,
    content_summary TEXT
);

CREATE TABLE IF NOT EXISTS confluence_status_snapshots (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    board_id        TEXT NOT NULL,
    page_id         TEXT,
    page_title      TEXT,
    snapshot_date   TEXT NOT NULL,
    rag_status      TEXT,
    status_as_of    TEXT,
    owner           TEXT,
    summary_text    TEXT,
    risks_text      TEXT,
    impact_text     TEXT,
    sprint_iteration TEXT,
    milestones_text TEXT,
    raw_content     TEXT,
    synced_at       TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_confluence_snapshots_board_date
    ON confluence_status_snapshots(board_id, snapshot_date);

CREATE TABLE IF NOT EXISTS action_tracker (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    page_id         TEXT,
    item            TEXT NOT NULL,
    action_required TEXT,
    assignee        TEXT,
    due_date        TEXT,
    status          TEXT,
    remarks         TEXT,
    synced_date     TEXT,
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now'))
);
"""

ATTENTION_DDL = """
-- ────────────────────────────────────────────
-- PHASE 2 / DELIVERY ATTENTION FOUNDATION
-- ────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS attention_rules (
    rule_key            TEXT NOT NULL,
    rule_version        TEXT NOT NULL,
    is_current          INTEGER NOT NULL DEFAULT 1
                        CHECK(is_current IN (0, 1)),
    enabled             INTEGER NOT NULL CHECK(enabled IN (0, 1)),
    parameters_json     TEXT NOT NULL DEFAULT '{}'
                        CHECK(json_valid(parameters_json)),
    created_at          TEXT NOT NULL,
    updated_at          TEXT NOT NULL,
    PRIMARY KEY(rule_key, rule_version),
    CHECK(
        rule_key != 'pending_decision_attention'
        OR enabled = 0
    )
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_attention_rules_one_current
    ON attention_rules(rule_key)
    WHERE is_current = 1;

CREATE TABLE IF NOT EXISTS attention_operations (
    operation_id        TEXT PRIMARY KEY,
    action              TEXT NOT NULL CHECK(
        action IN ('reconcile', 'acknowledge', 'snooze', 'resolve')
    ),
    actor               TEXT NOT NULL,
    status              TEXT NOT NULL CHECK(
        status IN ('proposed', 'claimed', 'success', 'failed', 'expired')
    ),
    scope_json          TEXT NOT NULL CHECK(json_valid(scope_json)),
    token_hash          TEXT NOT NULL UNIQUE,
    proposed_json       TEXT NOT NULL DEFAULT '{}'
                        CHECK(json_valid(proposed_json)),
    result_json         TEXT NOT NULL DEFAULT '{}'
                        CHECK(json_valid(result_json)),
    failure_code        TEXT NOT NULL DEFAULT '',
    created_at          TEXT NOT NULL,
    expires_at          TEXT NOT NULL,
    claimed_at          TEXT NOT NULL DEFAULT '',
    finished_at         TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_attention_operations_status_expiry
    ON attention_operations(status, expires_at);

CREATE TABLE IF NOT EXISTS attention_reconciliations (
    reconciliation_id  TEXT PRIMARY KEY,
    operation_id       TEXT NOT NULL UNIQUE
                       REFERENCES attention_operations(operation_id),
    status              TEXT NOT NULL CHECK(
        status IN ('success', 'partial', 'failed', 'invalid')
    ),
    actor               TEXT NOT NULL,
    started_at          TEXT NOT NULL,
    finished_at         TEXT NOT NULL,
    rule_set_version    TEXT NOT NULL,
    warning_codes_json  TEXT NOT NULL DEFAULT '[]'
                        CHECK(json_valid(warning_codes_json)),
    candidate_count     INTEGER NOT NULL DEFAULT 0 CHECK(candidate_count >= 0),
    created_count       INTEGER NOT NULL DEFAULT 0 CHECK(created_count >= 0),
    updated_count       INTEGER NOT NULL DEFAULT 0 CHECK(updated_count >= 0),
    cleared_count       INTEGER NOT NULL DEFAULT 0 CHECK(cleared_count >= 0),
    reopened_count      INTEGER NOT NULL DEFAULT 0 CHECK(reopened_count >= 0)
);

CREATE INDEX IF NOT EXISTS idx_attention_reconciliations_finished
    ON attention_reconciliations(finished_at);

CREATE TABLE IF NOT EXISTS attention_signals (
    attention_id           TEXT PRIMARY KEY,
    rule_key               TEXT NOT NULL,
    rule_version           TEXT NOT NULL,
    subject_kind           TEXT NOT NULL,
    subject_id             TEXT NOT NULL,
    rule_state             TEXT NOT NULL CHECK(
        rule_state IN ('active', 'clear', 'unknown', 'unavailable')
    ),
    attention_state        TEXT NOT NULL CHECK(
        attention_state IN ('open', 'acknowledged', 'snoozed', 'resolved')
    ),
    evaluation_status      TEXT NOT NULL DEFAULT 'complete' CHECK(
        evaluation_status IN ('complete', 'partial', 'failed', 'disabled')
    ),
    severity               TEXT NOT NULL CHECK(
        severity IN ('critical', 'high', 'medium', 'low', 'none')
    ),
    first_seen_at          TEXT NOT NULL,
    last_seen_at           TEXT NOT NULL,
    last_reconciliation_id TEXT NOT NULL
                           REFERENCES attention_reconciliations(reconciliation_id),
    acknowledged_at        TEXT NOT NULL DEFAULT '',
    acknowledged_by        TEXT NOT NULL DEFAULT '',
    snoozed_until          TEXT NOT NULL DEFAULT '',
    snoozed_by             TEXT NOT NULL DEFAULT '',
    resolved_at            TEXT NOT NULL DEFAULT '',
    resolved_by            TEXT NOT NULL DEFAULT '',
    resolution_reason      TEXT NOT NULL DEFAULT '',
    observation_hash       TEXT NOT NULL,
    observation_json       TEXT NOT NULL CHECK(json_valid(observation_json)),
    created_at             TEXT NOT NULL,
    updated_at             TEXT NOT NULL,
    UNIQUE(rule_key, subject_kind, subject_id),
    FOREIGN KEY(rule_key, rule_version)
        REFERENCES attention_rules(rule_key, rule_version)
);

CREATE INDEX IF NOT EXISTS idx_attention_signals_active_ranking
    ON attention_signals(attention_state, rule_state, severity, updated_at);

CREATE INDEX IF NOT EXISTS idx_attention_signals_subject
    ON attention_signals(subject_kind, subject_id, rule_key);

CREATE TABLE IF NOT EXISTS attention_history (
    event_id              TEXT PRIMARY KEY,
    attention_id          TEXT NOT NULL REFERENCES attention_signals(attention_id),
    operation_id          TEXT NOT NULL REFERENCES attention_operations(operation_id),
    reconciliation_id     TEXT REFERENCES attention_reconciliations(reconciliation_id),
    event_type            TEXT NOT NULL CHECK(
        event_type IN (
            'detected', 'observed_again', 'cleared', 'reopened',
            'acknowledged', 'snoozed', 'snooze_expired', 'resolved',
            'evaluation_limited', 'rule_disabled'
        )
    ),
    prior_rule_state      TEXT NOT NULL DEFAULT '',
    new_rule_state        TEXT NOT NULL DEFAULT '',
    prior_attention_state TEXT NOT NULL DEFAULT '',
    new_attention_state   TEXT NOT NULL DEFAULT '',
    severity              TEXT NOT NULL,
    rule_version          TEXT NOT NULL,
    actor                 TEXT NOT NULL,
    observation_json      TEXT NOT NULL DEFAULT '{}'
                          CHECK(json_valid(observation_json)),
    created_at            TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_attention_history_attention_recent
    ON attention_history(attention_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_attention_history_reconciliation
    ON attention_history(reconciliation_id, created_at);
"""


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type IN ('table','view') AND name=?",
        [table_name],
    ).fetchone()
    return row is not None


def _column_exists(conn: sqlite3.Connection, table_name: str, column_name: str) -> bool:
    if not _table_exists(conn, table_name):
        return False
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return any(row[1] == column_name for row in rows)


def _normalize_name(name: str) -> str:
    return normalize_name(name)


def _derive_workday_id_from_employee_id(employee_id: str) -> str | None:
    return derive_workday_id(employee_id)


def _is_placeholder_employee_row(row: sqlite3.Row | dict) -> bool:
    employee_id = row["id"] if isinstance(row, sqlite3.Row) else row.get("id", "")
    name = row["name"] if isinstance(row, sqlite3.Row) else row.get("name", "")
    return (
        is_placeholder_identifier(employee_id)
        or is_placeholder_identifier(name)
        or "to be hired" in (name or "").lower()
    )


def _derive_placeholder_hiref_id(row: sqlite3.Row | dict) -> str:
    candidates = [
        row["hiref_id"] if isinstance(row, sqlite3.Row) else row.get("hiref_id", ""),
        row["current_hiref"] if isinstance(row, sqlite3.Row) else row.get("current_hiref", ""),
        row["next_hiref"] if isinstance(row, sqlite3.Row) else row.get("next_hiref", ""),
        row["name"] if isinstance(row, sqlite3.Row) else row.get("name", ""),
        row["id"] if isinstance(row, sqlite3.Row) else row.get("id", ""),
    ]
    for candidate in candidates:
        value = (candidate or "").strip()
        if value and is_placeholder_identifier(value):
            return value if value.upper().startswith("HIREF") else value.upper()
    return ""


def _remap_json_employee_refs(
    node: object,
    id_map: dict[str, str],
    list_root_key: str | None = None,
) -> tuple[object, bool]:
    changed = False

    if isinstance(node, dict):
        updated: dict[object, object] = {}
        for key, value in node.items():
            if (
                isinstance(value, str)
                and key in {"member_id", "employee_id", "owner_id", "lead_id", "linked_employee_id"}
                and value in id_map
            ):
                updated[key] = id_map[value]
                changed = True
            else:
                updated_value, value_changed = _remap_json_employee_refs(value, id_map, key)
                updated[key] = updated_value
                changed = changed or value_changed
        return updated, changed

    if isinstance(node, list):
        updated_list: list[object] = []
        for item in node:
            if list_root_key == "member_ids" and isinstance(item, str) and item in id_map:
                updated_list.append(id_map[item])
                changed = True
            else:
                updated_item, item_changed = _remap_json_employee_refs(item, id_map, None)
                updated_list.append(updated_item)
                changed = changed or item_changed
        return updated_list, changed

    return node, False


def _rewrite_json_employee_refs(
    raw_json: str | None,
    id_map: dict[str, str],
    list_root_key: str | None = None,
) -> tuple[str | None, bool]:
    if not raw_json:
        return raw_json, False

    try:
        payload = json.loads(raw_json)
    except json.JSONDecodeError:
        return raw_json, False

    updated_payload, changed = _remap_json_employee_refs(payload, id_map, list_root_key)
    if not changed:
        return raw_json, False

    return json.dumps(updated_payload, ensure_ascii=False), True


def _migrate_decision_log_employee_refs(
    conn: sqlite3.Connection,
    id_map: dict[str, str],
) -> None:
    if not id_map or not _table_exists(conn, "decision_log"):
        return

    rows = conn.execute(
        """
        SELECT id, candidates, chosen, alternatives, member_ids
        FROM decision_log
        """
    ).fetchall()

    for row in rows:
        candidates, candidates_changed = _rewrite_json_employee_refs(row["candidates"], id_map)
        chosen, chosen_changed = _rewrite_json_employee_refs(row["chosen"], id_map)
        alternatives, alternatives_changed = _rewrite_json_employee_refs(row["alternatives"], id_map)
        member_ids, member_ids_changed = _rewrite_json_employee_refs(
            row["member_ids"],
            id_map,
            "member_ids",
        )

        if not any([candidates_changed, chosen_changed, alternatives_changed, member_ids_changed]):
            continue

        conn.execute(
            """
            UPDATE decision_log
            SET candidates = ?,
                chosen = ?,
                alternatives = ?,
                member_ids = ?
            WHERE id = ?
            """,
            [candidates, chosen, alternatives, member_ids, row["id"]],
        )


def _migrate_memory_fact_subjects(
    conn: sqlite3.Connection,
    id_map: dict[str, str],
) -> None:
    if not id_map or not _table_exists(conn, "memory_facts"):
        return

    for old_id, new_id in id_map.items():
        conn.execute(
            "UPDATE memory_facts SET subject = ? WHERE subject = ?",
            [new_id, old_id],
        )


def _should_run_v16_identity_migration(conn: sqlite3.Connection) -> bool:
    if not _table_exists(conn, "employees"):
        return False

    rows = conn.execute("SELECT id, name, wd_id FROM employees").fetchall()
    if not rows:
        return False

    for row in rows:
        if _is_placeholder_employee_row(row):
            return True

        canonical_id = (row["wd_id"] or "").strip() or _derive_workday_id_from_employee_id(row["id"])
        if not canonical_id or row["id"] != canonical_id or (row["wd_id"] or "").strip() != canonical_id:
            return True

    if _table_exists(conn, "employee_external_ids"):
        legacy_external_ids = conn.execute(
            """
            SELECT 1
            FROM employee_external_ids
            WHERE system_name IN ('workday', 'vendor', 'legacy_hr')
            LIMIT 1
            """
        ).fetchone()
        if legacy_external_ids:
            return True

    return False


def _migrate_employee_identity_v16(conn: sqlite3.Connection) -> None:
    if not _should_run_v16_identity_migration(conn):
        return

    default_plan_version = _ensure_default_plan_version(conn) or "baseline-imported-2026"
    current_year, current_month = [
        int(value)
        for value in conn.execute(
            "SELECT strftime('%Y', 'now'), strftime('%m', 'now')"
        ).fetchone()
    ]

    employee_rows = conn.execute("SELECT * FROM employees").fetchall()
    placeholder_rows: list[dict] = []
    employee_id_map: dict[str, str] = {}
    seen_canonical_ids: dict[str, str] = {}

    for row in employee_rows:
        if _is_placeholder_employee_row(row):
            placeholder_rows.append(dict(row))
            continue

        canonical_id = (row["wd_id"] or "").strip() or _derive_workday_id_from_employee_id(row["id"])
        if not canonical_id:
            raise ValueError(
                f"Employee '{row['id']}' is missing a Workday ID and cannot be migrated to the v1.6 canonical identity model."
            )

        existing = seen_canonical_ids.get(canonical_id)
        if existing and existing != row["id"]:
            raise ValueError(
                f"Employee identity collision detected: '{existing}' and '{row['id']}' both map to Workday ID '{canonical_id}'."
            )

        seen_canonical_ids[canonical_id] = row["id"]
        employee_id_map[row["id"]] = canonical_id

    changed_id_map = {
        old_id: new_id
        for old_id, new_id in employee_id_map.items()
        if old_id != new_id
    }

    fk_state = conn.execute("PRAGMA foreign_keys").fetchone()[0]
    conn.commit()
    conn.execute("PRAGMA foreign_keys = OFF")

    try:
        for row in placeholder_rows:
            old_id = row["id"]
            placeholder_id = build_placeholder_id(
                row.get("hiref_id") or row.get("current_hiref") or row.get("next_hiref") or old_id,
                row.get("name") or old_id,
            )
            hiref_id = _derive_placeholder_hiref_id(row)
            note_parts = [
                value
                for value in [row.get("notes", ""), "Migrated from employees during v1.6 identity redesign."]
                if value
            ]
            conn.execute(
                """
                INSERT INTO staffing_placeholders
                    (placeholder_id, display_name, source_system, source_employee_id, hiref_id,
                     linked_employee_id, resource_type, status, notes, metadata)
                VALUES
                    (?, ?, 'resource_portal', ?, ?, NULL, ?, ?, ?, ?)
                ON CONFLICT(placeholder_id) DO UPDATE SET
                    display_name = excluded.display_name,
                    source_system = excluded.source_system,
                    source_employee_id = excluded.source_employee_id,
                    hiref_id = excluded.hiref_id,
                    resource_type = excluded.resource_type,
                    status = excluded.status,
                    notes = excluded.notes,
                    metadata = excluded.metadata,
                    updated_at = datetime('now')
                """,
                [
                    placeholder_id,
                    row.get("name") or placeholder_id,
                    old_id,
                    hiref_id,
                    row.get("resource_type", ""),
                    row.get("status", "planned") or "planned",
                    " ".join(note_parts),
                    row.get("metadata", "{}") or "{}",
                ],
            )

            if _table_exists(conn, "monthly_allocations"):
                monthly_rows = conn.execute(
                    """
                    SELECT project_id, year, month, allocation, COALESCE(plan_version_id, '') AS plan_version_id
                    FROM monthly_allocations
                    WHERE employee_id = ?
                    """,
                    [old_id],
                ).fetchall()
                for alloc_row in monthly_rows:
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO placeholder_monthly_allocations
                            (placeholder_id, project_id, year, month, allocation, plan_version_id)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        [
                            placeholder_id,
                            alloc_row["project_id"],
                            alloc_row["year"],
                            alloc_row["month"],
                            alloc_row["allocation"],
                            alloc_row["plan_version_id"],
                        ],
                    )

            if _table_exists(conn, "assignments"):
                assignment_rows = conn.execute(
                    """
                    SELECT project_id, allocation, start_date
                    FROM assignments
                    WHERE employee_id = ?
                      AND status IN ('active', 'planned')
                    """,
                    [old_id],
                ).fetchall()
                for alloc_row in assignment_rows:
                    year = current_year
                    month = current_month
                    start_date = (alloc_row["start_date"] or "").strip()
                    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", start_date):
                        year = int(start_date[:4])
                        month = int(start_date[5:7])
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO placeholder_monthly_allocations
                            (placeholder_id, project_id, year, month, allocation, plan_version_id)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        [
                            placeholder_id,
                            alloc_row["project_id"],
                            year,
                            month,
                            alloc_row["allocation"],
                            default_plan_version,
                        ],
                    )

            if _table_exists(conn, "employee_external_ids"):
                conn.execute("DELETE FROM employee_external_ids WHERE employee_id = ?", [old_id])
            if _table_exists(conn, "monthly_allocations"):
                conn.execute("DELETE FROM monthly_allocations WHERE employee_id = ?", [old_id])
            if _table_exists(conn, "assignments"):
                conn.execute("DELETE FROM assignments WHERE employee_id = ?", [old_id])
            if _table_exists(conn, "action_items"):
                conn.execute("UPDATE action_items SET owner_id = NULL WHERE owner_id = ?", [old_id])
            conn.execute("UPDATE employees SET lead_id = NULL WHERE lead_id = ?", [old_id])
            if _table_exists(conn, "projects"):
                conn.execute("UPDATE projects SET lead_id = NULL WHERE lead_id = ?", [old_id])

        for old_id, new_id in changed_id_map.items():
            if _table_exists(conn, "assignments"):
                conn.execute(
                    "UPDATE assignments SET employee_id = ? WHERE employee_id = ?",
                    [new_id, old_id],
                )
            if _table_exists(conn, "monthly_allocations"):
                conn.execute(
                    "UPDATE monthly_allocations SET employee_id = ? WHERE employee_id = ?",
                    [new_id, old_id],
                )
            if _table_exists(conn, "employee_external_ids"):
                conn.execute(
                    "UPDATE employee_external_ids SET employee_id = ? WHERE employee_id = ?",
                    [new_id, old_id],
                )
            if _table_exists(conn, "action_items"):
                conn.execute(
                    "UPDATE action_items SET owner_id = ? WHERE owner_id = ?",
                    [new_id, old_id],
                )
            conn.execute(
                "UPDATE employees SET lead_id = ? WHERE lead_id = ?",
                [new_id, old_id],
            )
            if _table_exists(conn, "projects"):
                conn.execute(
                    "UPDATE projects SET lead_id = ? WHERE lead_id = ?",
                    [new_id, old_id],
                )
            if _table_exists(conn, "staffing_placeholders"):
                conn.execute(
                    "UPDATE staffing_placeholders SET linked_employee_id = ? WHERE linked_employee_id = ?",
                    [new_id, old_id],
                )

        for old_id, new_id in changed_id_map.items():
            conn.execute(
                "UPDATE employees SET id = ?, wd_id = ? WHERE id = ?",
                [new_id, new_id, old_id],
            )

        conn.execute("UPDATE employees SET wd_id = id WHERE COALESCE(wd_id, '') != id")

        for row in placeholder_rows:
            conn.execute("DELETE FROM employees WHERE id = ?", [row["id"]])

        _migrate_memory_fact_subjects(conn, changed_id_map)
        _migrate_decision_log_employee_refs(conn, changed_id_map)

        if _table_exists(conn, "employee_external_ids"):
            conn.execute(
                "DELETE FROM employee_external_ids WHERE system_name = 'workday' AND id_type = 'wd_id'"
            )
            conn.execute(
                """
                DELETE FROM employee_external_ids
                WHERE employee_id NOT IN (SELECT id FROM employees)
                """
            )

        fk_violations = conn.execute("PRAGMA foreign_key_check").fetchall()
        if fk_violations:
            raise ValueError(f"Foreign key violations after v1.6 identity migration: {fk_violations}")

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.execute(f"PRAGMA foreign_keys = {1 if fk_state else 0}")


def _relation_type(conn: sqlite3.Connection, relation_name: str) -> str | None:
    row = conn.execute(
        "SELECT type FROM sqlite_master WHERE type IN ('table', 'view') AND name = ?",
        [relation_name],
    ).fetchone()
    return row[0] if row else None


def _extract_legacy_snapshot_priorities(raw_plan_json: str | None) -> list[str]:
    if not raw_plan_json:
        return []
    try:
        payload = json.loads(raw_plan_json)
    except json.JSONDecodeError:
        return []

    if isinstance(payload, dict):
        items = payload.get("items", [])
        if isinstance(items, list):
            return [str(item).strip() for item in items if str(item).strip()]
        return []

    if isinstance(payload, list):
        return [str(item).strip() for item in payload if str(item).strip()]

    return []


def _classify_legacy_snapshot(row: sqlite3.Row) -> tuple[str, str, str]:
    legacy_type = (row["plan_type"] or "").strip()
    origin_context = (row["use_case_id"] or "").strip()
    created_by = (row["created_by"] or "").strip().lower()

    artifact_kind = "plan"
    horizon = "ad_hoc"
    generation_mode = created_by if created_by in {"user", "ai", "system"} else "user"

    if legacy_type == "weekly_plan":
        horizon = "weekly"
        if origin_context == "weekly-project-status":
            artifact_kind = "status"
    elif legacy_type == "milestone_plan":
        horizon = "milestone"
    elif legacy_type == "recovery_plan":
        artifact_kind = "recovery"
    elif legacy_type == "ai_draft":
        generation_mode = "ai"

    return artifact_kind, horizon, generation_mode


def _refresh_project_plan_snapshots_compat_view(conn: sqlite3.Connection) -> None:
    conn.execute("DROP VIEW IF EXISTS project_plan_snapshots")
    conn.execute(
        """
        CREATE VIEW project_plan_snapshots AS
        SELECT
            ps.id,
            ps.project_id,
            NULLIF(ps.origin_context, '') AS use_case_id,
            ps.staffing_scenario_id AS plan_version_id,
            ps.supersedes_snapshot_id AS supersedes_id,
            CASE
                WHEN ps.artifact_kind = 'recovery' THEN 'recovery_plan'
                WHEN ps.generation_mode = 'ai' THEN 'ai_draft'
                WHEN ps.horizon = 'milestone' THEN 'milestone_plan'
                WHEN ps.horizon = 'weekly' THEN 'weekly_plan'
                ELSE ps.artifact_kind
            END AS plan_type,
            ps.snapshot_date AS as_of_date,
            ps.artifact_state AS status,
            ps.title,
            ps.summary AS summary_text,
            json_object(
                'items', json(COALESCE(ps.priorities_json, '[]')),
                'milestones', json(COALESCE(ps.milestones_json, '[]')),
                'actions', json(COALESCE(ps.actions_json, '[]')),
                'decisions', json(COALESCE(ps.decisions_json, '[]')),
                'dependencies', json(COALESCE(ps.dependencies_json, '[]')),
                'changes', json(COALESCE(ps.changes_json, '[]'))
            ) AS plan_json,
            ps.assumptions_json,
            ps.risks_json,
            ps.source_run_id,
            ps.created_by,
            ps.created_at
        FROM project_snapshots ps
        """
    )


def _migrate_project_snapshots_v18(conn: sqlite3.Connection) -> None:
    if not _table_exists(conn, "project_snapshots"):
        return

    relation_type = _relation_type(conn, "project_plan_snapshots")
    if relation_type == "table":
        rows = conn.execute("SELECT * FROM project_plan_snapshots ORDER BY created_at, id").fetchall()
        valid_scenarios = set()
        if _table_exists(conn, "plan_versions"):
            valid_scenarios = {
                row["plan_version_id"]
                for row in conn.execute("SELECT plan_version_id FROM plan_versions").fetchall()
            }
        valid_run_ids = set()
        if _table_exists(conn, "sync_runs"):
            valid_run_ids = {
                row["id"] for row in conn.execute("SELECT id FROM sync_runs").fetchall()
            }

        supersedes_pairs: list[tuple[str, str]] = []
        for row in rows:
            artifact_kind, horizon, generation_mode = _classify_legacy_snapshot(row)
            staffing_scenario_id = (row["plan_version_id"] or "").strip() or None
            if staffing_scenario_id and staffing_scenario_id not in valid_scenarios:
                staffing_scenario_id = None
            source_run_id = (row["source_run_id"] or "").strip() or None
            if source_run_id and source_run_id not in valid_run_ids:
                source_run_id = None
            conn.execute(
                """
                INSERT OR IGNORE INTO project_snapshots
                    (id, project_id, snapshot_date, artifact_kind, horizon, artifact_state, health,
                     title, summary, priorities_json, milestones_json, actions_json, risks_json,
                     assumptions_json, decisions_json, dependencies_json, changes_json,
                     staffing_scenario_id, supersedes_snapshot_id, origin_context, generation_mode,
                     source_run_id, created_by, created_at)
                VALUES
                    (?, ?, ?, ?, ?, ?, 'unknown',
                     ?, ?, ?, '[]', '[]', ?, ?, '[]', '[]', '[]',
                     ?, NULL, ?, ?, ?, ?, ?)
                """,
                [
                    row["id"],
                    row["project_id"],
                    row["as_of_date"],
                    artifact_kind,
                    horizon,
                    row["status"] or "draft",
                    row["title"] or "",
                    row["summary_text"] or "",
                    json.dumps(_extract_legacy_snapshot_priorities(row["plan_json"]), ensure_ascii=False),
                    row["risks_json"] or "[]",
                    row["assumptions_json"] or "[]",
                    staffing_scenario_id,
                    (row["use_case_id"] or "").strip(),
                    generation_mode,
                    source_run_id,
                    row["created_by"] or "user",
                    row["created_at"] or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                ],
            )
            supersedes_id = (row["supersedes_id"] or "").strip()
            if supersedes_id:
                supersedes_pairs.append((row["id"], supersedes_id))

        for snapshot_id, supersedes_id in supersedes_pairs:
            exists = conn.execute(
                "SELECT 1 FROM project_snapshots WHERE id = ?",
                [supersedes_id],
            ).fetchone()
            if exists:
                conn.execute(
                    """
                    UPDATE project_snapshots
                    SET supersedes_snapshot_id = ?
                    WHERE id = ?
                    """,
                    [supersedes_id, snapshot_id],
                )

        conn.execute("DROP TABLE project_plan_snapshots")

    _refresh_project_plan_snapshots_compat_view(conn)


def _ensure_default_plan_version(conn: sqlite3.Connection) -> str | None:
    if not _table_exists(conn, "monthly_allocations"):
        return None

    row = conn.execute("SELECT COUNT(*) FROM monthly_allocations").fetchone()
    if not row or row[0] == 0:
        return None

    default_id = "baseline-imported-2026"
    conn.execute(
        """
        INSERT INTO plan_versions
            (plan_version_id, version_name, scenario_type, as_of_date, version_status, notes)
        VALUES
            (?, 'Imported Baseline 2026', 'baseline', date('now'), 'active',
             'Backfilled from pre-v1.5 monthly_allocations during migration')
        ON CONFLICT(plan_version_id) DO UPDATE SET
            version_name=excluded.version_name,
            scenario_type=excluded.scenario_type,
            version_status=excluded.version_status,
            notes=excluded.notes,
            updated_at=datetime('now')
        """,
        [default_id],
    )
    conn.execute(
        """
        UPDATE monthly_allocations
        SET plan_version_id = ?
        WHERE COALESCE(plan_version_id, '') = ''
        """,
        [default_id],
    )
    return default_id


def _table_sql(conn: sqlite3.Connection, table_name: str) -> str:
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
        [table_name],
    ).fetchone()
    return str(row[0] or "") if row else ""


def _assert_v24_allocation_rows_are_valid(
    conn: sqlite3.Connection,
    table_name: str,
) -> None:
    invalid = conn.execute(
        f"""
        SELECT COUNT(*)
        FROM {table_name}
        WHERE month IS NULL
           OR month NOT BETWEEN 1 AND 12
           OR allocation IS NULL
           OR allocation < 0.0
           OR allocation > 1.0
           OR plan_version_id IS NULL
        """
    ).fetchone()[0]
    if invalid:
        raise ValueError(
            f"{table_name} contains invalid month/allocation rows; "
            "repair them before applying v24 integrity constraints."
        )


def _migrate_allocation_integrity_v24(conn: sqlite3.Connection) -> None:
    if _table_exists(conn, "assignments"):
        invalid_assignments = conn.execute(
            """
            SELECT COUNT(*) FROM assignments
            WHERE allocation IS NULL
               OR allocation < 0.0
               OR allocation > 1.0
            """
        ).fetchone()[0]
        if invalid_assignments:
            raise ValueError(
                "assignments contains invalid allocation rows; repair them "
                "before applying v24 integrity constraints."
            )
        if "check(allocation >= 0.0 and allocation <= 1.0)" not in _table_sql(
            conn, "assignments"
        ).lower():
            dependent_views = [
                (row[0], row[1])
                for row in conn.execute(
                    """
                    SELECT name, sql
                    FROM sqlite_master
                    WHERE type = 'view'
                      AND LOWER(sql) LIKE '%assignments%'
                    ORDER BY name
                    """
                ).fetchall()
            ]
            conn.execute("SAVEPOINT assignments_integrity_v24")
            try:
                for view_name, _view_sql in dependent_views:
                    quoted_name = view_name.replace('"', '""')
                    conn.execute(f'DROP VIEW "{quoted_name}"')
                conn.execute(
                    """
                    CREATE TABLE assignments_v24 (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        employee_id TEXT NOT NULL REFERENCES employees(id),
                        project_id TEXT NOT NULL REFERENCES projects(id),
                        role TEXT,
                        allocation REAL NOT NULL DEFAULT 0.5
                            CHECK(allocation >= 0.0 AND allocation <= 1.0),
                        start_date TEXT,
                        end_date TEXT,
                        status TEXT DEFAULT 'active',
                        created_at TEXT DEFAULT (datetime('now')),
                        UNIQUE(employee_id, project_id, status)
                    )
                    """
                )
                conn.execute(
                    """
                    INSERT INTO assignments_v24
                        (id, employee_id, project_id, role, allocation,
                         start_date, end_date, status, created_at)
                    SELECT id, employee_id, project_id, role, allocation,
                           start_date, end_date, status, created_at
                    FROM assignments
                    """
                )
                conn.execute("DROP TABLE assignments")
                conn.execute(
                    "ALTER TABLE assignments_v24 RENAME TO assignments"
                )
                for _view_name, view_sql in dependent_views:
                    conn.execute(view_sql)
                conn.execute("RELEASE SAVEPOINT assignments_integrity_v24")
            except Exception:
                conn.execute("ROLLBACK TO SAVEPOINT assignments_integrity_v24")
                conn.execute("RELEASE SAVEPOINT assignments_integrity_v24")
                raise

    table_definitions = {
        "monthly_allocations": """
            CREATE TABLE monthly_allocations_v24 (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id TEXT NOT NULL REFERENCES employees(id),
                project_id TEXT NOT NULL REFERENCES projects(id),
                year INTEGER NOT NULL,
                month INTEGER NOT NULL CHECK(month BETWEEN 1 AND 12),
                allocation REAL NOT NULL DEFAULT 0.0
                    CHECK(allocation >= 0.0 AND allocation <= 1.0),
                plan_version_id TEXT NOT NULL DEFAULT ''
                    REFERENCES plan_versions(plan_version_id),
                UNIQUE(employee_id, project_id, year, month, plan_version_id)
            )
        """,
        "placeholder_monthly_allocations": """
            CREATE TABLE placeholder_monthly_allocations_v24 (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                placeholder_id TEXT NOT NULL
                    REFERENCES staffing_placeholders(placeholder_id),
                project_id TEXT NOT NULL REFERENCES projects(id),
                year INTEGER NOT NULL,
                month INTEGER NOT NULL CHECK(month BETWEEN 1 AND 12),
                allocation REAL NOT NULL DEFAULT 0.0
                    CHECK(allocation >= 0.0 AND allocation <= 1.0),
                plan_version_id TEXT NOT NULL DEFAULT ''
                    REFERENCES plan_versions(plan_version_id),
                UNIQUE(placeholder_id, project_id, year, month, plan_version_id)
            )
        """,
    }
    identity_columns = {
        "monthly_allocations": "employee_id",
        "placeholder_monthly_allocations": "placeholder_id",
    }
    for table_name, create_sql in table_definitions.items():
        if not _table_exists(conn, table_name):
            continue
        _assert_v24_allocation_rows_are_valid(conn, table_name)
        identity = identity_columns[table_name]
        duplicate = conn.execute(
            f"""
            SELECT 1
            FROM {table_name}
            GROUP BY {identity}, project_id, year, month, plan_version_id
            HAVING COUNT(*) > 1
            LIMIT 1
            """
        ).fetchone()
        if duplicate:
            raise ValueError(
                f"{table_name} contains duplicate period allocations; "
                "resolve them before applying v24 integrity constraints."
            )
        sql = _table_sql(conn, table_name).lower()
        if (
            "check(month between 1 and 12)" in sql
            and "check(allocation >= 0.0 and allocation <= 1.0)" in sql
            and f"unique({identity}, project_id, year, month, plan_version_id)" in sql
        ):
            continue
        replacement = f"{table_name}_v24"
        conn.execute(create_sql)
        conn.execute(
            f"""
            INSERT INTO {replacement}
                (id, {identity}, project_id, year, month, allocation,
                 plan_version_id)
            SELECT id, {identity}, project_id, year, month, allocation,
                   plan_version_id
            FROM {table_name}
            """
        )
        conn.execute(f"DROP TABLE {table_name}")
        conn.execute(f"ALTER TABLE {replacement} RENAME TO {table_name}")


def _migrate_staffing_token_hash_v24(conn: sqlite3.Connection) -> None:
    if not _table_exists(conn, "staffing_proposals"):
        return
    columns = {
        row[1] for row in conn.execute("PRAGMA table_info(staffing_proposals)")
    }
    if "confirmation_token_hash" in columns and "confirmation_token" not in columns:
        return
    if "confirmation_token" not in columns:
        raise ValueError("staffing_proposals has no supported confirmation token column")

    import hashlib

    rows = conn.execute("SELECT * FROM staffing_proposals").fetchall()
    conn.execute(
        """
        CREATE TABLE staffing_proposals_v24 (
            proposal_id TEXT PRIMARY KEY,
            status TEXT NOT NULL DEFAULT 'proposed',
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            confirmed_at TEXT DEFAULT '',
            confirmation_token_hash TEXT NOT NULL UNIQUE,
            request_json TEXT NOT NULL,
            evidence_json TEXT NOT NULL DEFAULT '{}',
            proposal_json TEXT NOT NULL,
            decision_id INTEGER REFERENCES decision_log(id),
            failure_reason TEXT DEFAULT ''
        )
        """
    )
    for row in rows:
        item = dict(row)
        token_hash = hashlib.sha256(
            str(item["confirmation_token"]).encode("utf-8")
        ).hexdigest()
        conn.execute(
            """
            INSERT INTO staffing_proposals_v24
                (proposal_id, status, created_at, expires_at, confirmed_at,
                 confirmation_token_hash, request_json, evidence_json,
                 proposal_json, decision_id, failure_reason)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                item["proposal_id"],
                item["status"],
                item["created_at"],
                item["expires_at"],
                item["confirmed_at"],
                token_hash,
                item["request_json"],
                item["evidence_json"],
                item["proposal_json"],
                item["decision_id"],
                item["failure_reason"],
            ],
        )
    conn.execute("DROP TABLE staffing_proposals")
    conn.execute(
        "ALTER TABLE staffing_proposals_v24 RENAME TO staffing_proposals"
    )


def _backfill_employee_external_ids(conn: sqlite3.Connection) -> None:
    if not _table_exists(conn, "employees") or not _table_exists(conn, "employee_external_ids"):
        return

    conn.execute(
        """
        UPDATE employee_external_ids
        SET system_name = 'resource_portal',
            id_type = 'employee_id',
            updated_at = datetime('now')
        WHERE (system_name = 'vendor' AND id_type = 'contractor_code')
           OR (system_name = 'legacy_hr' AND id_type = 'employee_no')
        """
    )
    conn.execute(
        "DELETE FROM employee_external_ids WHERE system_name = 'workday' AND id_type = 'wd_id'"
    )
    conn.execute(
        """
        DELETE FROM employee_external_ids
        WHERE employee_id NOT IN (SELECT id FROM employees)
        """
    )

    employee_rows = conn.execute(
        """
        SELECT id, name, wd_id, resource_type
        FROM employees
        """
    ).fetchall()

    for row in employee_rows:
        emp_id = row["id"]
        name = row["name"] or emp_id

        if (row["wd_id"] or "").strip() != emp_id:
            conn.execute(
                "UPDATE employees SET wd_id = ? WHERE id = ?",
                [emp_id, emp_id],
            )

        resource_portal_row = conn.execute(
            """
            SELECT id, external_id
            FROM employee_external_ids
            WHERE employee_id = ?
              AND system_name = 'resource_portal'
              AND id_type = 'employee_id'
            ORDER BY id
            LIMIT 1
            """,
            [emp_id],
        ).fetchone()
        if resource_portal_row:
            conn.execute(
                """
                UPDATE employee_external_ids
                SET external_name = ?,
                    updated_at = datetime('now')
                WHERE id = ?
                """,
                [name, resource_portal_row["id"]],
            )
        else:
            resource_portal_id = build_default_resource_portal_id(
                emp_id,
                row["resource_type"],
            )
            note = ""
            if resource_portal_id != emp_id:
                note = "derived from canonical Workday ID during v1.6 backfill"
            conn.execute(
                """
                INSERT INTO employee_external_ids
                    (employee_id, system_name, id_type, external_id, external_name, notes)
                VALUES (?, 'resource_portal', 'employee_id', ?, ?, ?)
                ON CONFLICT(employee_id, system_name, id_type) DO UPDATE SET
                    external_id = excluded.external_id,
                    external_name = excluded.external_name,
                    notes = excluded.notes,
                    updated_at = datetime('now')
                """,
                [emp_id, resource_portal_id, name, note],
            )

    if not _table_exists(conn, "jira_issues"):
        return

    issue_rows = conn.execute(
        """
        SELECT assignee_id, assignee_name, COUNT(*) AS cnt
        FROM jira_issues
        WHERE assignee_id IS NOT NULL AND assignee_id != ''
          AND assignee_name IS NOT NULL AND assignee_name != ''
        GROUP BY assignee_id, assignee_name
        ORDER BY cnt DESC
        """
    ).fetchall()
    jira_by_name: dict[str, list[sqlite3.Row]] = {}
    for row in issue_rows:
        key = _normalize_name(row["assignee_name"])
        if key:
            jira_by_name.setdefault(key, []).append(row)

    for row in employee_rows:
        emp_id = row["id"]
        name = row["name"] or emp_id
        key = _normalize_name(name)
        matches = jira_by_name.get(key, [])
        if not matches:
            continue
        best = matches[0]
        conn.execute(
            """
            INSERT INTO employee_external_ids
                (employee_id, system_name, id_type, external_id, external_name, notes)
            VALUES (?, 'jira', 'assignee_account_id', ?, ?, 'auto-matched from jira_issues by normalized assignee name')
            ON CONFLICT(employee_id, system_name, id_type) DO UPDATE SET
                external_id=excluded.external_id,
                external_name=excluded.external_name,
                notes=excluded.notes,
                updated_at=datetime('now')
            """,
            [emp_id, best["assignee_id"], best["assignee_name"]],
        )


def _seed_use_cases(conn: sqlite3.Connection) -> None:
    if not _table_exists(conn, "use_cases"):
        return

    capability_overrides: dict[str, sqlite3.Row] = {}
    if _table_exists(conn, "agent_capabilities"):
        rows = conn.execute(
            "SELECT capability, status, complexity FROM agent_capabilities"
        ).fetchall()
        capability_overrides = {row["capability"]: row for row in rows}

    definitions = [
        {
            "id": "resource-allocation",
            "capability_key": "resource_allocation",
            "name": "Resource Allocation",
            "use_case_type": "business",
            "problem_statement": "Recommend the best-fit people for project demand without overloading staff.",
            "decision_type": "allocation",
            "source_systems_json": [
                "import-resource-portal",
                "import-skills-matrix",
                "import-hiref-report",
            ],
            "core_tables_json": [
                "employees",
                "employee_external_ids",
                "assignments",
                "monthly_allocations",
                "hiref",
                "decision_log",
            ],
            "outputs_json": ["pm allocate", "decision_log", "dashboard:/api/employees"],
            "priority": 1,
            "complexity": 2,
            "status": "active",
            "owner": "pm-agent",
            "notes": "Seeded by v1.7 use case framework.",
        },
        {
            "id": "hiref-renewal",
            "capability_key": "hiref_management",
            "name": "HIREF Renewal Management",
            "use_case_type": "business",
            "problem_statement": "Track contractor contract expiry, project compliance, and renewal readiness.",
            "decision_type": "risk",
            "source_systems_json": [
                "import-hiref-report",
                "import-resource-portal",
            ],
            "core_tables_json": [
                "employees",
                "hiref",
                "assignments",
                "staffing_placeholders",
            ],
            "outputs_json": ["pm hiref summary", "pm hiref review", "dashboard:/api/hiref", "weekly risks"],
            "priority": 1,
            "complexity": 3,
            "status": "active",
            "owner": "pm-agent",
            "notes": "Seeded by v1.7 use case framework.",
        },
        {
            "id": "weekly-project-status",
            "capability_key": "weekly_report",
            "name": "Weekly Project Status",
            "use_case_type": "business",
            "problem_statement": "Summarize weekly delivery status, actions, and management updates across projects.",
            "decision_type": "status",
            "source_systems_json": [
                "confluence-status-batch",
                "servicenow-change-requests",
            ],
            "core_tables_json": [
                "confluence_pages",
                "confluence_status_snapshots",
                "action_tracker",
                "change_requests",
                "action_items",
            ],
            "outputs_json": ["pm report", "Confluence status wall", "weekly summary"],
            "priority": 1,
            "complexity": 2,
            "status": "active",
            "owner": "pm-agent",
            "notes": "Seeded by v1.7 use case framework.",
        },
        {
            "id": "project-health-scoring",
            "capability_key": "health_scoring",
            "name": "Project Health Scoring",
            "use_case_type": "business",
            "problem_statement": "Score delivery health using JIRA sprint, burndown, quality, and scope indicators.",
            "decision_type": "risk",
            "source_systems_json": [
                "jira-release-*",
                "jira-health-*",
                "confluence-status-batch",
            ],
            "core_tables_json": [
                "jira_stream_versions",
                "jira_issues",
                "jira_sprints",
                "jira_health_snapshots",
                "confluence_status_snapshots",
            ],
            "outputs_json": ["pm health", "dashboard:/api/project-health"],
            "priority": 1,
            "complexity": 3,
            "status": "active",
            "owner": "pm-agent",
            "notes": "Seeded by v1.7 use case framework.",
        },
        {
            "id": "project-planning-draft",
            "capability_key": "",
            "name": "Project Planning Draft",
            "use_case_type": "business",
            "problem_statement": "Capture structured project planning drafts, assumptions, and risks for reuse and iteration.",
            "decision_type": "planning",
            "source_systems_json": [
                "import-resource-portal",
                "jira-health-*",
                "confluence-status-batch",
                "manual",
            ],
            "core_tables_json": [
                "projects",
                "project_profiles",
                "plan_versions",
                "project_snapshots",
            ],
            "outputs_json": ["pm planning add/list/show", "dashboard:/api/project-snapshots"],
            "priority": 2,
            "complexity": 2,
            "status": "active",
            "owner": "pm-agent",
            "notes": "Refreshed in v1.8 to persist PM-friendly project snapshots.",
        },
        {
            "id": "budget-estimation",
            "capability_key": "",
            "name": "Budget Estimation",
            "use_case_type": "business",
            "problem_statement": "Estimate staffing cost and budget implications using allocation and billing data.",
            "decision_type": "budget",
            "source_systems_json": [
                "import-resource-portal",
                "import-hiref-report",
                "manual",
            ],
            "core_tables_json": [
                "employees",
                "monthly_allocations",
                "plan_versions",
            ],
            "outputs_json": ["future budget estimation", "staffing cost view"],
            "priority": 2,
            "complexity": 2,
            "status": "active",
            "owner": "pm-agent",
            "notes": "Added in v1.7 to preserve billing_rate for future budget use cases.",
        },
        {
            "id": "memory-learning",
            "capability_key": "memory_learning",
            "name": "Memory Learning",
            "use_case_type": "platform",
            "problem_statement": "Persist long-lived PM rules and operating context across sessions.",
            "decision_type": "platform",
            "source_systems_json": ["manual"],
            "core_tables_json": ["memory_facts"],
            "outputs_json": ["cross-session context"],
            "priority": 3,
            "complexity": 1,
            "status": "active",
            "owner": "pm-agent",
            "notes": "Long-lived PM operating rules and context store.",
        },
        {
            "id": "project-focus-mode",
            "capability_key": "project_focus_mode",
            "name": "Project Focus Mode",
            "use_case_type": "platform",
            "problem_statement": "Highlight focus projects and their latest operating context for PM review.",
            "decision_type": "platform",
            "source_systems_json": ["manual", "confluence-status-batch"],
            "core_tables_json": ["project_profiles", "confluence_status_snapshots"],
            "outputs_json": ["dashboard focus views"],
            "priority": 3,
            "complexity": 2,
            "status": "active",
            "owner": "pm-agent",
            "notes": "Highlight focus projects and latest status context in the dashboard.",
        },
    ]

    for item in definitions:
        capability_key = item.pop("capability_key")
        capability_row = capability_overrides.get(capability_key) if capability_key else None
        status = capability_row["status"] if capability_row else item["status"]
        complexity = capability_row["complexity"] if capability_row else item["complexity"]
        conn.execute(
            """
            INSERT INTO use_cases
                (id, name, use_case_type, problem_statement, decision_type,
                 source_systems_json, core_tables_json, outputs_json,
                 priority, complexity, status, owner, notes)
            VALUES
                (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                use_case_type = excluded.use_case_type,
                problem_statement = excluded.problem_statement,
                decision_type = excluded.decision_type,
                source_systems_json = excluded.source_systems_json,
                core_tables_json = excluded.core_tables_json,
                outputs_json = excluded.outputs_json,
                priority = excluded.priority,
                complexity = excluded.complexity,
                status = excluded.status,
                owner = excluded.owner,
                notes = excluded.notes,
                updated_at = datetime('now')
            """,
            [
                item["id"],
                item["name"],
                item["use_case_type"],
                item["problem_statement"],
                item["decision_type"],
                json.dumps(item["source_systems_json"], ensure_ascii=False),
                json.dumps(item["core_tables_json"], ensure_ascii=False),
                json.dumps(item["outputs_json"], ensure_ascii=False),
                item["priority"],
                complexity,
                status,
                item["owner"],
                item["notes"],
            ],
        )


def _seed_data_sources(conn: sqlite3.Connection) -> None:
    if not _table_exists(conn, "data_sources"):
        return

    definitions = [
        {
            "id": "import-resource-portal",
            "source_type": "excel",
            "source_name": "Resource Portal Distribution Import",
            "ingestion_mode": "file",
            "refresh_sla_hours": 720,
            "active": 1,
            "config_json": {"script": "scripts/import_from_excel.py"},
            "notes": "Canonical staffing baseline import.",
        },
        {
            "id": "import-hiref-report",
            "source_type": "excel",
            "source_name": "HIREF Status Report Import",
            "ingestion_mode": "file",
            "refresh_sla_hours": 720,
            "active": 1,
            "config_json": {"script": "scripts/import_hiref.py"},
            "notes": "Contract and expiry enrichment import.",
        },
        {
            "id": "import-skills-matrix",
            "source_type": "json",
            "source_name": "Skills Matrix Import",
            "ingestion_mode": "file",
            "refresh_sla_hours": 720,
            "active": 1,
            "config_json": {"script": "scripts/import_skills.py"},
            "notes": "Role, level, and skill enrichment import.",
        },
        {
            "id": "servicenow-change-requests",
            "source_type": "servicenow",
            "source_name": "ServiceNow Change Requests",
            "ingestion_mode": "file",
            "refresh_sla_hours": 168,
            "active": 1,
            "config_json": {"script": "scripts/import_cr_csv.py"},
            "notes": "Change request status import from ServiceNow CSV exports.",
        },
        {
            "id": "confluence-status-batch",
            "source_type": "confluence",
            "source_name": "Confluence Status Sync (Batch)",
            "ingestion_mode": "api",
            "refresh_sla_hours": 168,
            "active": 1,
            "config_json": {"command": "pm confluence sync"},
            "notes": "Batch sync for project status pages and action tracker.",
        },
    ]

    if _table_exists(conn, "jira_board_configs"):
        board_rows = conn.execute(
            """
            SELECT id, name, project_key, version_name_pattern, board_url, pm_project_id, active
            FROM jira_board_configs
            """
        ).fetchall()
        for row in board_rows:
            config_json = {
                "board_id": row["id"],
                "project_key": row["project_key"],
                "version_name_pattern": row["version_name_pattern"] or "",
                "board_url": row["board_url"] or "",
                "pm_project_id": row["pm_project_id"] or "",
            }
            definitions.extend(
                [
                    {
                        "id": f"jira-release-{row['id']}",
                        "source_type": "jira",
                        "source_name": f"JIRA Release Sync — {row['name']}",
                        "ingestion_mode": "api",
                        "refresh_sla_hours": 24,
                        "active": row["active"],
                        "config_json": config_json,
                        "notes": "Per-board JIRA release/version sync.",
                    },
                    {
                        "id": f"jira-health-{row['id']}",
                        "source_type": "jira",
                        "source_name": f"JIRA Health Sync — {row['name']}",
                        "ingestion_mode": "api",
                        "refresh_sla_hours": 24,
                        "active": row["active"],
                        "config_json": config_json,
                        "notes": "Per-board JIRA sprint/health sync.",
                    },
                ]
            )

    for item in definitions:
        conn.execute(
            """
            INSERT INTO data_sources
                (id, source_type, source_name, ingestion_mode, refresh_sla_hours,
                 active, config_json, notes)
            VALUES
                (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                source_type = excluded.source_type,
                source_name = excluded.source_name,
                ingestion_mode = excluded.ingestion_mode,
                refresh_sla_hours = excluded.refresh_sla_hours,
                active = excluded.active,
                config_json = excluded.config_json,
                notes = excluded.notes,
                updated_at = datetime('now')
            """,
            [
                item["id"],
                item["source_type"],
                item["source_name"],
                item["ingestion_mode"],
                item["refresh_sla_hours"],
                item["active"],
                json.dumps(item["config_json"], ensure_ascii=False),
                item["notes"],
            ],
        )


def _legacy_version_board_ids(
    conn: sqlite3.Connection,
    project_key: str,
    version_name: str,
) -> list[str]:
    matched = [
        row[0]
        for row in conn.execute(
            """
            SELECT id
            FROM jira_board_configs
            WHERE project_key = ?
              AND COALESCE(version_name_pattern, '') != ''
              AND ? LIKE version_name_pattern
            ORDER BY id
            """,
            [project_key, version_name],
        ).fetchall()
    ]
    if matched:
        return matched

    fallback = [
        row[0]
        for row in conn.execute(
            "SELECT id FROM jira_board_configs WHERE project_key = ? ORDER BY id",
            [project_key],
        ).fetchall()
    ]
    return fallback if len(fallback) == 1 else []


def _migrate_legacy_jira_versions_v19(conn: sqlite3.Connection) -> tuple[int, int]:
    if not _table_exists(conn, "jira_versions"):
        return 0, 0

    rows = conn.execute("SELECT * FROM jira_versions").fetchall()
    if not rows:
        return 0, 0

    migrated_rows = 0
    unresolved_rows = 0
    for row in rows:
        board_ids = _legacy_version_board_ids(conn, row["project_key"], row["name"])
        if not board_ids:
            unresolved_rows += 1
            continue

        for board_id in board_ids:
            conn.execute(
                """
                INSERT INTO jira_stream_versions
                    (id, board_id, project_key, name, release_date, start_date,
                     status, released, total_issues, done_issues, inprogress_issues,
                     todo_issues, progress_pct, total_sp, done_sp, inprogress_sp,
                     todo_sp, sp_progress_pct, raw_data, synced_at)
                VALUES
                    (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0.0, 0.0, 0.0, 0.0, 0.0, ?, ?)
                ON CONFLICT(id, board_id) DO UPDATE SET
                    project_key = excluded.project_key,
                    name = excluded.name,
                    release_date = excluded.release_date,
                    start_date = excluded.start_date,
                    status = excluded.status,
                    released = excluded.released,
                    total_issues = excluded.total_issues,
                    done_issues = excluded.done_issues,
                    inprogress_issues = excluded.inprogress_issues,
                    todo_issues = excluded.todo_issues,
                    progress_pct = excluded.progress_pct,
                    raw_data = excluded.raw_data,
                    synced_at = excluded.synced_at
                """,
                [
                    row["id"],
                    board_id,
                    row["project_key"],
                    row["name"],
                    row["release_date"],
                    row["start_date"],
                    row["status"],
                    row["released"],
                    row["total_issues"],
                    row["done_issues"],
                    row["inprogress_issues"],
                    row["todo_issues"],
                    row["progress_pct"],
                    row["raw_data"],
                    row["synced_at"],
                ],
            )
            migrated_rows += 1

    return migrated_rows, unresolved_rows


def _migrate_action_tracker_v20(conn: sqlite3.Connection) -> None:
    """Move legacy tracker rows to the generic action-tracker table."""
    if not _table_exists(conn, "c2l_action_tracker"):
        return
    conn.execute(
        """
        INSERT OR IGNORE INTO action_tracker
            (id, page_id, item, action_required, assignee, due_date, status, remarks, synced_date, created_at, updated_at)
        SELECT id, page_id, item, action_required, assignee, due_date, status, remarks, synced_date, created_at, updated_at
        FROM c2l_action_tracker
        """
    )
    conn.execute("DROP TABLE c2l_action_tracker")


def _drop_legacy_tables_v19(conn: sqlite3.Connection) -> list[str]:
    migrated_release_rows, unresolved_release_rows = _migrate_legacy_jira_versions_v19(conn)
    warnings: list[str] = []
    if _table_exists(conn, "jira_versions"):
        if unresolved_release_rows == 0:
            conn.execute("DROP TABLE jira_versions")
        else:
            warnings.append(
                "Retained legacy jira_versions because some rows could not be mapped to jira_stream_versions yet."
            )
    if migrated_release_rows:
        warnings.append(
            f"Migrated {migrated_release_rows} legacy jira_versions row(s) into jira_stream_versions."
        )

    legacy_tables = [
        "memory_conversations",
        "memory_patterns",
        "memory_sessions",
        "agent_capabilities",
    ]
    for table_name in legacy_tables:
        if _table_exists(conn, table_name):
            conn.execute(f"DROP TABLE {table_name}")
    return warnings


PROJECT_HEALTH_PARAMETERS_V2 = {
    "config_version": "1.0",
    "default": {
        "source_precedence": [
            "jira_grade",
            "confluence_rag",
        ],
        "state_precedence": ["red", "amber"],
        "jira_grade_mapping": {
            "RED": "red",
            "YELLOW": "amber",
            "AMBER": "amber",
            "GREEN": "clear",
        },
        "confluence_rag_mapping": {
            "RED": "red",
            "AMBER": "amber",
            "YELLOW": "amber",
            "GREEN": "clear",
        },
    },
    "project_overrides": {},
}


def _migrate_project_health_rule_v2(conn: sqlite3.Connection) -> None:
    """Preserve v1 references while moving its fixed labels into v2 config."""
    row = conn.execute(
        """
        SELECT parameters_json
        FROM attention_rules
        WHERE rule_key = 'project_health_attention'
          AND rule_version = 'project-health-attention-v1'
          AND is_current = 1
        """
    ).fetchone()
    if not row:
        return
    parameters = json.loads(row["parameters_json"])
    if parameters != {"health_states": ["red", "amber"]}:
        return
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    conn.execute(
        """
        UPDATE attention_rules
        SET is_current = 0, updated_at = ?
        WHERE rule_key = 'project_health_attention'
          AND rule_version = 'project-health-attention-v1'
          AND is_current = 1
        """,
        [now],
    )
    conn.execute(
        """
        INSERT INTO attention_rules
            (rule_key, rule_version, is_current, enabled, parameters_json,
             created_at, updated_at)
        VALUES (
            'project_health_attention', 'project-health-attention-v2',
            1, 1, ?, ?, ?
        )
        """,
        [
            json.dumps(
                PROJECT_HEALTH_PARAMETERS_V2,
                sort_keys=True,
                separators=(",", ":"),
            ),
            now,
            now,
        ],
    )


def _seed_attention_rules(conn: sqlite3.Connection) -> None:
    """Register only the approved deterministic Phase 2 rule catalog."""
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rules = [
        (
            "project_health_attention",
            "project-health-attention-v2",
            1,
            PROJECT_HEALTH_PARAMETERS_V2,
        ),
        (
            "overdue_action_attention",
            "overdue-action-attention-v1",
            1,
            {"status": "open", "due_before": "today"},
        ),
        (
            "source_freshness_attention",
            "source-freshness-attention-v1",
            1,
            {"required_sources": "management_attention"},
        ),
        (
            "resource_overload_attention",
            "resource-overload-attention-v1",
            1,
            {"active_assignment_load_strictly_greater_than": 1.0},
        ),
        (
            "pending_decision_attention",
            "pending-decision-attention-disabled-v1",
            0,
            {"governance_definition": "not_approved"},
        ),
    ]
    conn.executemany(
        """
        INSERT OR IGNORE INTO attention_rules
            (rule_key, rule_version, is_current, enabled, parameters_json,
             created_at, updated_at)
        VALUES (?, ?, 1, ?, ?, ?, ?)
        """,
        [
            (
                rule_key,
                rule_version,
                enabled,
                json.dumps(parameters, sort_keys=True, separators=(",", ":")),
                now,
                now,
            )
            for rule_key, rule_version, enabled, parameters in rules
        ],
    )


def main(quiet: bool = False) -> None:
    db_path = Path(settings.database_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(DDL)
    conn.executescript(EXTRA_DDL)
    conn.executescript(ATTENTION_DDL)
    existing_columns = {
        row[1] for row in conn.execute("PRAGMA table_info(employees)").fetchall()
    }
    employee_migrations = [
        ("resource_type", "ALTER TABLE employees ADD COLUMN resource_type TEXT DEFAULT ''"),
        ("billing_rate", "ALTER TABLE employees ADD COLUMN billing_rate TEXT DEFAULT ''"),
        ("billing_end_date", "ALTER TABLE employees ADD COLUMN billing_end_date TEXT DEFAULT ''"),
        ("hiref_id", "ALTER TABLE employees ADD COLUMN hiref_id TEXT DEFAULT ''"),
        ("current_hiref", "ALTER TABLE employees ADD COLUMN current_hiref TEXT DEFAULT ''"),
        ("next_hiref", "ALTER TABLE employees ADD COLUMN next_hiref TEXT DEFAULT ''"),
        ("wd_id", "ALTER TABLE employees ADD COLUMN wd_id TEXT DEFAULT ''"),
    ]
    for column, sql in employee_migrations:
        if column not in existing_columns:
            conn.execute(sql)

    if not _column_exists(conn, "jira_board_configs", "issues_use_base_jql"):
        conn.execute(
            "ALTER TABLE jira_board_configs ADD COLUMN issues_use_base_jql INTEGER DEFAULT 0"
        )
    if not _column_exists(conn, "monthly_allocations", "plan_version_id"):
        conn.execute(
            "ALTER TABLE monthly_allocations ADD COLUMN plan_version_id TEXT DEFAULT ''"
        )

    conn.commit()
    try:
        _migrate_employee_identity_v16(conn)
        _ensure_default_plan_version(conn)
        _migrate_allocation_integrity_v24(conn)
        _migrate_staffing_token_hash_v24(conn)
        _backfill_employee_external_ids(conn)
        _migrate_project_snapshots_v18(conn)
        _migrate_action_tracker_v20(conn)
        _seed_use_cases(conn)
        _seed_data_sources(conn)
        _migrate_project_health_rule_v2(conn)
        _seed_attention_rules(conn)
        legacy_cleanup_warnings = _drop_legacy_tables_v19(conn)
    except Exception:
        conn.rollback()
        conn.close()
        raise

    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_employees_wd_id_unique
        ON employees(wd_id)
        WHERE COALESCE(wd_id, '') != ''
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_employees_current_hiref ON employees(current_hiref)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_employees_next_hiref ON employees(next_hiref)")
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_assignments_employee
        ON assignments(employee_id, status)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_assignments_project
        ON assignments(project_id, status)
        """
    )
    if _column_exists(conn, "monthly_allocations", "plan_version_id"):
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_monthly_allocations_employee_month
            ON monthly_allocations(employee_id, year, month)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_monthly_allocations_project_month
            ON monthly_allocations(project_id, year, month)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_monthly_allocations_version_month
            ON monthly_allocations(plan_version_id, year, month)
            """
        )
        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS
                idx_monthly_allocations_unique_period
            ON monthly_allocations(
                employee_id, project_id, year, month, plan_version_id
            )
            """
        )
    if _table_exists(conn, "placeholder_monthly_allocations"):
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS
                idx_placeholder_allocations_placeholder_month
            ON placeholder_monthly_allocations(placeholder_id, year, month)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_placeholder_allocations_project_month
            ON placeholder_monthly_allocations(project_id, year, month)
            """
        )
    if _table_exists(conn, "staffing_proposals"):
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_staffing_proposals_status_expiry
            ON staffing_proposals(status, expires_at)
            """
        )
    conn.commit()
    conn.close()

    if not quiet:
        for warning in legacy_cleanup_warnings:
            print(f"ℹ {warning}")
        print(f"✅ Database initialised at {db_path.resolve()}")


if __name__ == "__main__":
    main()
