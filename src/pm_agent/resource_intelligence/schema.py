"""Additive schema owned by the Resource Intelligence capacity core."""

RESOURCE_INTELLIGENCE_DDL = """
CREATE TABLE IF NOT EXISTS resource_capacity_import_sessions (
    session_id TEXT PRIMARY KEY,
    package_id TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    package_fingerprint TEXT NOT NULL UNIQUE,
    package_json TEXT NOT NULL CHECK(json_valid(package_json)),
    status TEXT NOT NULL CHECK(status IN ('previewed','running','completed','failed','rejected')),
    created_at TEXT NOT NULL,
    completed_at TEXT NOT NULL DEFAULT '',
    failure_code TEXT NOT NULL DEFAULT '',
    report_json TEXT NOT NULL DEFAULT '{}' CHECK(json_valid(report_json))
);

CREATE INDEX IF NOT EXISTS idx_resource_capacity_sessions_package
    ON resource_capacity_import_sessions(package_id, created_at);

CREATE INDEX IF NOT EXISTS idx_resource_capacity_sessions_idempotency
    ON resource_capacity_import_sessions(idempotency_key);

CREATE TABLE IF NOT EXISTS resource_capacity_import_attempts (
    attempt_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES resource_capacity_import_sessions(session_id),
    status TEXT NOT NULL CHECK(status IN ('running','completed','failed')),
    started_at TEXT NOT NULL,
    finished_at TEXT NOT NULL DEFAULT '',
    failure_code TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS resource_capacity_import_runs (
    run_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES resource_capacity_import_sessions(session_id),
    attempt_id TEXT REFERENCES resource_capacity_import_attempts(attempt_id),
    step_key TEXT NOT NULL CHECK(step_key IN
        ('validate','publication','derivation','integrity','rollback_compatibility')),
    status TEXT NOT NULL CHECK(status IN ('completed','failed','rejected')),
    counts_json TEXT NOT NULL DEFAULT '{}' CHECK(json_valid(counts_json)),
    warning_codes_json TEXT NOT NULL DEFAULT '[]' CHECK(json_valid(warning_codes_json)),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS resource_capacity_publications (
    publication_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL UNIQUE REFERENCES resource_capacity_import_sessions(session_id),
    package_id TEXT NOT NULL,
    package_fingerprint TEXT NOT NULL UNIQUE,
    schema_version TEXT NOT NULL,
    workforce_publication_id TEXT NOT NULL,
    plan_version_id TEXT NOT NULL REFERENCES plan_versions(plan_version_id),
    assessment_time TEXT NOT NULL,
    published_at TEXT NOT NULL,
    is_current INTEGER NOT NULL CHECK(is_current IN (0,1)),
    report_json TEXT NOT NULL CHECK(json_valid(report_json))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_resource_capacity_current_publication
    ON resource_capacity_publications(is_current) WHERE is_current=1;

CREATE TABLE IF NOT EXISTS resource_capacity_manifest_coverage (
    publication_id TEXT NOT NULL REFERENCES resource_capacity_publications(publication_id),
    member_id TEXT NOT NULL REFERENCES employees(id),
    year INTEGER NOT NULL,
    month INTEGER NOT NULL CHECK(month BETWEEN 1 AND 12),
    commitment_kind TEXT NOT NULL CHECK(commitment_kind IN ('leave','bau','non_project')),
    authoritative_source_id TEXT NOT NULL,
    PRIMARY KEY(publication_id,member_id,year,month,commitment_kind)
);

CREATE TABLE IF NOT EXISTS resource_capacity_observations (
    observation_id TEXT PRIMARY KEY,
    publication_id TEXT NOT NULL REFERENCES resource_capacity_publications(publication_id),
    member_id TEXT NOT NULL REFERENCES employees(id),
    year INTEGER NOT NULL,
    month INTEGER NOT NULL CHECK(month BETWEEN 1 AND 12),
    commitment_kind TEXT NOT NULL CHECK(commitment_kind IN ('leave','bau','non_project')),
    fraction REAL NOT NULL CHECK(fraction BETWEEN 0.0 AND 1.0),
    value_state TEXT NOT NULL CHECK(value_state='known'),
    authoritative_source_id TEXT NOT NULL,
    source_reference TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    rule_version TEXT NOT NULL,
    source_observation_version INTEGER NOT NULL CHECK(source_observation_version >= 1),
    observation_fingerprint TEXT NOT NULL,
    UNIQUE(publication_id,member_id,year,month,commitment_kind)
);

CREATE TABLE IF NOT EXISTS resource_capacity_derivations (
    derivation_id TEXT PRIMARY KEY,
    publication_id TEXT NOT NULL REFERENCES resource_capacity_publications(publication_id),
    workforce_publication_id TEXT NOT NULL,
    plan_version_id TEXT NOT NULL REFERENCES plan_versions(plan_version_id),
    member_id TEXT NOT NULL REFERENCES employees(id),
    year INTEGER NOT NULL,
    month INTEGER NOT NULL CHECK(month BETWEEN 1 AND 12),
    state TEXT NOT NULL CHECK(state IN ('known','stale','unknown','conflicting')),
    state_reason TEXT NOT NULL,
    base_capacity REAL,
    leave_fraction REAL,
    bau_fraction REAL,
    non_project_fraction REAL,
    non_project_deduction REAL,
    effective_capacity_raw REAL,
    effective_capacity REAL,
    planned_project_allocation REAL,
    available_capacity_raw REAL,
    available_capacity REAL,
    total_commitment REAL,
    overload_amount REAL,
    overload_state TEXT CHECK(overload_state IS NULL OR overload_state IN ('clear','amber','red')),
    assessment_time TEXT NOT NULL,
    derivation_rule_version TEXT NOT NULL,
    freshness_rule_version TEXT NOT NULL,
    base_rule_version TEXT NOT NULL,
    overload_rule_version TEXT NOT NULL,
    evidence_json TEXT NOT NULL CHECK(json_valid(evidence_json)),
    UNIQUE(publication_id,member_id,year,month,plan_version_id)
);

CREATE INDEX IF NOT EXISTS idx_resource_capacity_derivation_lookup
    ON resource_capacity_derivations(member_id,year,month,plan_version_id);
"""
