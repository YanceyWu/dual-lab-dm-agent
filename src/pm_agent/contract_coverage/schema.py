"""Additive schema for canonical contract-coverage publication."""

CONTRACT_COVERAGE_DDL = """
CREATE TABLE IF NOT EXISTS contract_coverage_import_sessions (
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

CREATE INDEX IF NOT EXISTS idx_contract_coverage_sessions_package
    ON contract_coverage_import_sessions(package_id, created_at);

CREATE TABLE IF NOT EXISTS contract_coverage_import_attempts (
    attempt_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES contract_coverage_import_sessions(session_id),
    status TEXT NOT NULL CHECK(status IN ('running','completed','failed')),
    started_at TEXT NOT NULL,
    finished_at TEXT NOT NULL DEFAULT '',
    failure_code TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_contract_coverage_attempts_session
    ON contract_coverage_import_attempts(session_id, started_at);

CREATE TABLE IF NOT EXISTS contract_coverage_import_runs (
    run_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES contract_coverage_import_sessions(session_id),
    attempt_id TEXT REFERENCES contract_coverage_import_attempts(attempt_id),
    step_key TEXT NOT NULL CHECK(step_key IN ('validate','publication')),
    status TEXT NOT NULL CHECK(status IN ('completed','failed','rejected')),
    counts_json TEXT NOT NULL DEFAULT '{}' CHECK(json_valid(counts_json)),
    warning_codes_json TEXT NOT NULL DEFAULT '[]' CHECK(json_valid(warning_codes_json)),
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_contract_coverage_runs_session
    ON contract_coverage_import_runs(session_id, created_at);

CREATE TABLE IF NOT EXISTS contract_coverage_publications (
    publication_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL UNIQUE REFERENCES contract_coverage_import_sessions(session_id),
    package_id TEXT NOT NULL,
    package_fingerprint TEXT NOT NULL UNIQUE,
    schema_version TEXT NOT NULL,
    scope_key TEXT NOT NULL,
    as_of_date TEXT NOT NULL,
    published_at TEXT NOT NULL,
    is_current INTEGER NOT NULL CHECK(is_current IN (0,1)),
    report_json TEXT NOT NULL CHECK(json_valid(report_json))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_contract_coverage_current_publication
    ON contract_coverage_publications(scope_key, is_current)
    WHERE is_current=1;

CREATE TABLE IF NOT EXISTS contract_coverage_members (
    publication_id TEXT NOT NULL REFERENCES contract_coverage_publications(publication_id),
    member_id TEXT NOT NULL,
    display_name TEXT NOT NULL,
    employment_status TEXT NOT NULL CHECK(employment_status IN ('active','inactive')),
    resource_type TEXT NOT NULL,
    current_hiref_id TEXT NOT NULL,
    hiref_end_date TEXT NOT NULL,
    PRIMARY KEY(publication_id, member_id)
);
"""

CONTRACT_COVERAGE_REQUIRED_TABLES = {
    "contract_coverage_import_sessions",
    "contract_coverage_import_attempts",
    "contract_coverage_import_runs",
    "contract_coverage_publications",
    "contract_coverage_members",
}
