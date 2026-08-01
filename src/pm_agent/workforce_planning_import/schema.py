"""Additive schema owned by the workforce/planning clean-import capability."""

WORKFORCE_PLANNING_IMPORT_DDL = """
CREATE TABLE IF NOT EXISTS workforce_planning_import_sessions (
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

CREATE INDEX IF NOT EXISTS idx_workforce_planning_sessions_package
    ON workforce_planning_import_sessions(package_id, created_at);

CREATE TABLE IF NOT EXISTS workforce_planning_import_attempts (
    attempt_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES workforce_planning_import_sessions(session_id),
    status TEXT NOT NULL CHECK(status IN ('running','completed','failed')),
    started_at TEXT NOT NULL,
    finished_at TEXT NOT NULL DEFAULT '',
    failure_code TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_workforce_planning_attempts_session
    ON workforce_planning_import_attempts(session_id, started_at);

CREATE TABLE IF NOT EXISTS workforce_planning_import_runs (
    run_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES workforce_planning_import_sessions(session_id),
    attempt_id TEXT REFERENCES workforce_planning_import_attempts(attempt_id),
    step_key TEXT NOT NULL CHECK(step_key IN ('validate','publication','integrity','rollback_compatibility')),
    status TEXT NOT NULL CHECK(status IN ('completed','failed','rejected')),
    counts_json TEXT NOT NULL DEFAULT '{}' CHECK(json_valid(counts_json)),
    warning_codes_json TEXT NOT NULL DEFAULT '[]' CHECK(json_valid(warning_codes_json)),
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_workforce_planning_runs_session
    ON workforce_planning_import_runs(session_id, created_at);

CREATE TABLE IF NOT EXISTS workforce_planning_publications (
    publication_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL UNIQUE REFERENCES workforce_planning_import_sessions(session_id),
    package_id TEXT NOT NULL,
    package_fingerprint TEXT NOT NULL UNIQUE,
    schema_version TEXT NOT NULL,
    published_at TEXT NOT NULL,
    is_current INTEGER NOT NULL CHECK(is_current IN (0,1)),
    report_json TEXT NOT NULL CHECK(json_valid(report_json))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_workforce_planning_current_publication
    ON workforce_planning_publications(is_current) WHERE is_current=1;

CREATE TABLE IF NOT EXISTS workforce_member_period_coverage (
    publication_id TEXT NOT NULL REFERENCES workforce_planning_publications(publication_id),
    member_id TEXT NOT NULL REFERENCES employees(id),
    year INTEGER NOT NULL,
    month INTEGER NOT NULL CHECK(month BETWEEN 1 AND 12),
    employment_status TEXT NOT NULL CHECK(employment_status IN ('active','inactive')),
    PRIMARY KEY(publication_id, member_id, year, month)
);

CREATE TABLE IF NOT EXISTS monthly_project_allocation_coverage (
    publication_id TEXT NOT NULL REFERENCES workforce_planning_publications(publication_id),
    member_id TEXT NOT NULL REFERENCES employees(id),
    project_id TEXT NOT NULL REFERENCES projects(id),
    plan_version_id TEXT NOT NULL REFERENCES plan_versions(plan_version_id),
    year INTEGER NOT NULL,
    month INTEGER NOT NULL CHECK(month BETWEEN 1 AND 12),
    value_state TEXT NOT NULL CHECK(value_state='known'),
    PRIMARY KEY(publication_id, member_id, project_id, plan_version_id, year, month)
);
"""
