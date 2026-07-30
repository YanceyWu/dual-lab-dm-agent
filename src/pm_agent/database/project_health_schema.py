"""Dedicated Project Health schema composition.

The schema is additive. The catalog and re-import audit coexist with the
controlled configuration and assessment capability; no Attention is created.
"""

from __future__ import annotations

import sqlite3
PROJECT_HEALTH_DDL = """
CREATE TABLE IF NOT EXISTS project_health_factor_catalog (
    factor_id TEXT PRIMARY KEY,
    catalog_version TEXT NOT NULL,
    dimension TEXT NOT NULL CHECK(dimension IN ('schedule','delivery','scope','quality','resource','dependency','governance')),
    evidence_boundary TEXT NOT NULL,
    availability_policy TEXT NOT NULL CHECK(availability_policy IN ('unknown','not_available')),
    active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)),
    UNIQUE(catalog_version, factor_id)
);

CREATE TABLE IF NOT EXISTS project_health_default_conditions (
    condition_id TEXT PRIMARY KEY,
    factor_id TEXT NOT NULL REFERENCES project_health_factor_catalog(factor_id),
    condition_version TEXT NOT NULL,
    condition_json TEXT NOT NULL CHECK(json_valid(condition_json)),
    active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)),
    UNIQUE(factor_id, condition_version)
);

CREATE TABLE IF NOT EXISTS project_health_input_observations (
    observation_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id),
    input_kind TEXT NOT NULL CHECK(input_kind IN ('quality_gate','capacity_coverage','governance_gate')),
    value_json TEXT NOT NULL CHECK(json_valid(value_json)),
    observed_at TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    import_run_id TEXT NOT NULL,
    UNIQUE(project_id, input_kind, observed_at, schema_version)
);

CREATE TABLE IF NOT EXISTS project_health_reimport_sessions (
    session_id TEXT PRIMARY KEY,
    package_id TEXT NOT NULL,
    package_version TEXT NOT NULL,
    package_fingerprint TEXT NOT NULL UNIQUE,
    package_json TEXT NOT NULL DEFAULT '{}' CHECK(json_valid(package_json)),
    status TEXT NOT NULL CHECK(status IN ('previewed','running','completed','failed','rejected')),
    created_at TEXT NOT NULL,
    completed_at TEXT NOT NULL DEFAULT '',
    warning_codes_json TEXT NOT NULL DEFAULT '[]' CHECK(json_valid(warning_codes_json)),
    integrity_json TEXT NOT NULL DEFAULT '{}' CHECK(json_valid(integrity_json)),
    report_json TEXT NOT NULL DEFAULT '{}' CHECK(json_valid(report_json))
);

CREATE TABLE IF NOT EXISTS project_health_reimport_runs (
    import_run_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES project_health_reimport_sessions(session_id),
    step_key TEXT NOT NULL CHECK(step_key IN ('validate','canonical_derivation','health_coverage')),
    status TEXT NOT NULL CHECK(status IN ('completed','failed','skipped')),
    counts_json TEXT NOT NULL DEFAULT '{}' CHECK(json_valid(counts_json)),
    warnings_json TEXT NOT NULL DEFAULT '[]' CHECK(json_valid(warnings_json)),
    created_at TEXT NOT NULL,
    UNIQUE(session_id, step_key)
);

CREATE TABLE IF NOT EXISTS project_health_reimport_attempts (
    attempt_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES project_health_reimport_sessions(session_id),
    status TEXT NOT NULL CHECK(status IN ('running','completed','failed')),
    started_at TEXT NOT NULL,
    finished_at TEXT NOT NULL DEFAULT '',
    warning_codes_json TEXT NOT NULL DEFAULT '[]' CHECK(json_valid(warning_codes_json))
);

CREATE TABLE IF NOT EXISTS project_health_configuration_operations (
    operation_id TEXT PRIMARY KEY,
    status TEXT NOT NULL CHECK(status IN ('reserved')),
    project_id TEXT REFERENCES projects(id),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS project_health_assessment_runs (
    assessment_run_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id),
    catalog_version TEXT NOT NULL,
    state TEXT NOT NULL CHECK(state IN ('red','amber','green','unknown','stale','missing','conflicting','not_available','not_applicable')),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS project_health_dimension_results (
    assessment_run_id TEXT NOT NULL REFERENCES project_health_assessment_runs(assessment_run_id),
    dimension TEXT NOT NULL,
    state TEXT NOT NULL,
    PRIMARY KEY(assessment_run_id, dimension)
);

CREATE TABLE IF NOT EXISTS project_health_factor_results (
    assessment_run_id TEXT NOT NULL REFERENCES project_health_assessment_runs(assessment_run_id),
    factor_id TEXT NOT NULL REFERENCES project_health_factor_catalog(factor_id),
    state TEXT NOT NULL,
    evidence_json TEXT NOT NULL DEFAULT '{}' CHECK(json_valid(evidence_json)),
    PRIMARY KEY(assessment_run_id, factor_id)
);

CREATE TABLE IF NOT EXISTS project_health_assessment_details (
    assessment_run_id TEXT PRIMARY KEY REFERENCES project_health_assessment_runs(assessment_run_id),
    configuration_version_id TEXT NOT NULL,
    guard_outcomes_json TEXT NOT NULL DEFAULT '[]' CHECK(json_valid(guard_outcomes_json)),
    legacy_comparison_json TEXT NOT NULL DEFAULT '{}' CHECK(json_valid(legacy_comparison_json))
);

CREATE TABLE IF NOT EXISTS project_health_configuration_versions (
    configuration_version_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL DEFAULT '',
    scope TEXT NOT NULL CHECK(scope IN ('default','project')),
    parameters_json TEXT NOT NULL CHECK(json_valid(parameters_json)),
    is_current INTEGER NOT NULL CHECK(is_current IN (0,1)),
    created_at TEXT NOT NULL,
    UNIQUE(scope, project_id, configuration_version_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_project_health_configuration_current
    ON project_health_configuration_versions(scope, project_id) WHERE is_current=1;

CREATE TABLE IF NOT EXISTS project_health_configuration_changes (
    operation_id TEXT PRIMARY KEY,
    scope TEXT NOT NULL CHECK(scope IN ('default','project')),
    project_id TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL CHECK(status IN ('proposed','claimed','confirmed','expired','rejected')),
    token_hash TEXT NOT NULL UNIQUE,
    fingerprint TEXT NOT NULL,
    proposed_json TEXT NOT NULL CHECK(json_valid(proposed_json)),
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    result_json TEXT NOT NULL DEFAULT '{}' CHECK(json_valid(result_json))
);

CREATE INDEX IF NOT EXISTS idx_project_health_reimport_sessions_status
    ON project_health_reimport_sessions(status, created_at);
CREATE INDEX IF NOT EXISTS idx_project_health_reimport_attempts_session
    ON project_health_reimport_attempts(session_id, started_at);
CREATE INDEX IF NOT EXISTS idx_project_health_input_observations_project
    ON project_health_input_observations(project_id, input_kind, observed_at);
"""


def ensure_project_health_reimport_columns(connection: sqlite3.Connection) -> None:
    """Keep pre-review local databases readable without relying on them in production."""
    columns = {row[1] for row in connection.execute("PRAGMA table_info(project_health_reimport_sessions)")}
    migrations = {
        "package_json": "ALTER TABLE project_health_reimport_sessions ADD COLUMN package_json TEXT NOT NULL DEFAULT '{}' CHECK(json_valid(package_json))",
        "integrity_json": "ALTER TABLE project_health_reimport_sessions ADD COLUMN integrity_json TEXT NOT NULL DEFAULT '{}' CHECK(json_valid(integrity_json))",
    }
    for column, statement in migrations.items():
        if column not in columns:
            connection.execute(statement)
