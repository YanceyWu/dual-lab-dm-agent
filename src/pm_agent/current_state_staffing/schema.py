"""Additive schema for canonical current-state staffing publication."""

CURRENT_STATE_STAFFING_DDL = """
CREATE TABLE IF NOT EXISTS current_state_staffing_import_sessions (
    session_id TEXT PRIMARY KEY,
    package_id TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    package_fingerprint TEXT NOT NULL UNIQUE,
    package_json TEXT NOT NULL CHECK(json_valid(package_json)),
    status TEXT NOT NULL CHECK(status IN ('previewed','running','completed','failed','rejected')),
    created_at TEXT NOT NULL,
    completed_at TEXT NOT NULL DEFAULT '',
    failure_code TEXT NOT NULL DEFAULT '',
    report_json TEXT NOT NULL DEFAULT '{}' CHECK(json_valid(report_json))
);

CREATE INDEX IF NOT EXISTS idx_current_state_staffing_sessions_package
    ON current_state_staffing_import_sessions(package_id, created_at);

CREATE TABLE IF NOT EXISTS current_state_staffing_import_attempts (
    attempt_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES current_state_staffing_import_sessions(session_id),
    status TEXT NOT NULL CHECK(status IN ('running','completed','failed')),
    started_at TEXT NOT NULL,
    finished_at TEXT NOT NULL DEFAULT '',
    failure_code TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_current_state_staffing_attempts_session
    ON current_state_staffing_import_attempts(session_id, started_at);

CREATE TABLE IF NOT EXISTS current_state_staffing_import_runs (
    run_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES current_state_staffing_import_sessions(session_id),
    attempt_id TEXT REFERENCES current_state_staffing_import_attempts(attempt_id),
    step_key TEXT NOT NULL CHECK(step_key IN ('validate','publication')),
    status TEXT NOT NULL CHECK(status IN ('completed','failed','rejected')),
    counts_json TEXT NOT NULL DEFAULT '{}' CHECK(json_valid(counts_json)),
    warning_codes_json TEXT NOT NULL DEFAULT '[]' CHECK(json_valid(warning_codes_json)),
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_current_state_staffing_runs_session
    ON current_state_staffing_import_runs(session_id, created_at);

CREATE TABLE IF NOT EXISTS current_state_staffing_publications (
    publication_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL UNIQUE REFERENCES current_state_staffing_import_sessions(session_id),
    package_id TEXT NOT NULL,
    package_fingerprint TEXT NOT NULL UNIQUE,
    schema_version TEXT NOT NULL,
    scope_key TEXT NOT NULL,
    as_of_date TEXT NOT NULL,
    effective_year INTEGER NOT NULL,
    effective_month INTEGER NOT NULL CHECK(effective_month BETWEEN 1 AND 12),
    published_at TEXT NOT NULL,
    is_current INTEGER NOT NULL CHECK(is_current IN (0,1)),
    report_json TEXT NOT NULL CHECK(json_valid(report_json))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_current_state_staffing_current_publication
    ON current_state_staffing_publications(scope_key, is_current)
    WHERE is_current=1;

CREATE TABLE IF NOT EXISTS current_state_staffing_members (
    publication_id TEXT NOT NULL REFERENCES current_state_staffing_publications(publication_id),
    member_id TEXT NOT NULL,
    display_name TEXT NOT NULL,
    employment_status TEXT NOT NULL CHECK(employment_status IN ('active','inactive')),
    role TEXT NOT NULL,
    level TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    current_hiref_id TEXT NOT NULL,
    hiref_end_date TEXT NOT NULL,
    PRIMARY KEY(publication_id, member_id)
);

CREATE TABLE IF NOT EXISTS current_state_staffing_projects (
    publication_id TEXT NOT NULL REFERENCES current_state_staffing_publications(publication_id),
    project_id TEXT NOT NULL,
    display_name TEXT NOT NULL,
    project_status TEXT NOT NULL CHECK(project_status IN ('planning','active','done')),
    priority INTEGER NOT NULL CHECK(priority BETWEEN 1 AND 5),
    PRIMARY KEY(publication_id, project_id)
);

CREATE TABLE IF NOT EXISTS current_state_staffing_assignments (
    publication_id TEXT NOT NULL REFERENCES current_state_staffing_publications(publication_id),
    member_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    allocation REAL NOT NULL CHECK(allocation > 0.0 AND allocation <= 1.0),
    PRIMARY KEY(publication_id, member_id, project_id),
    FOREIGN KEY(publication_id, member_id)
        REFERENCES current_state_staffing_members(publication_id, member_id),
    FOREIGN KEY(publication_id, project_id)
        REFERENCES current_state_staffing_projects(publication_id, project_id)
);

CREATE INDEX IF NOT EXISTS idx_current_state_staffing_assignments_project
    ON current_state_staffing_assignments(publication_id, project_id, member_id);

CREATE TABLE IF NOT EXISTS current_state_staffing_member_loads (
    publication_id TEXT NOT NULL REFERENCES current_state_staffing_publications(publication_id),
    member_id TEXT NOT NULL,
    current_load REAL NOT NULL CHECK(current_load >= 0.0),
    active_project_count INTEGER NOT NULL CHECK(active_project_count >= 0),
    assignment_state TEXT NOT NULL CHECK(assignment_state IN ('assigned','unassigned')),
    PRIMARY KEY(publication_id, member_id),
    FOREIGN KEY(publication_id, member_id)
        REFERENCES current_state_staffing_members(publication_id, member_id)
);
"""

CURRENT_STATE_STAFFING_REQUIRED_TABLES = {
    "current_state_staffing_import_sessions",
    "current_state_staffing_import_attempts",
    "current_state_staffing_import_runs",
    "current_state_staffing_publications",
    "current_state_staffing_members",
    "current_state_staffing_projects",
    "current_state_staffing_assignments",
    "current_state_staffing_member_loads",
}
