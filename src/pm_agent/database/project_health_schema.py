"""Dedicated Phase 4 Project Health schema composition.

The schema is additive.  Batch A owns catalogue and re-import audit only; it
does not create health assessments, configuration mutations, or Attention.
"""
PHASE4_HEALTH_DDL = """
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
    status TEXT NOT NULL CHECK(status IN ('previewed','running','completed','failed','rejected')),
    created_at TEXT NOT NULL,
    completed_at TEXT NOT NULL DEFAULT '',
    warning_codes_json TEXT NOT NULL DEFAULT '[]' CHECK(json_valid(warning_codes_json)),
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

CREATE INDEX IF NOT EXISTS idx_project_health_reimport_sessions_status
    ON project_health_reimport_sessions(status, created_at);
CREATE INDEX IF NOT EXISTS idx_project_health_input_observations_project
    ON project_health_input_observations(project_id, input_kind, observed_at);
"""
