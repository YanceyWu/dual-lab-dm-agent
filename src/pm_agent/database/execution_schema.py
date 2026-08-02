"""Dedicated Phase 3 canonical schema composition.

This module owns the canonical execution storage family extracted from
``database/bootstrap.py`` so bootstrap can remain a composition boundary.
"""

from __future__ import annotations

PHASE3_CANONICAL_DDL = """
CREATE TABLE IF NOT EXISTS execution_work_items (
    work_item_id            TEXT PRIMARY KEY,
    project_id              TEXT NOT NULL REFERENCES projects(id),
    board_id                TEXT NOT NULL,
    source_id               TEXT NOT NULL,
    source_ref              TEXT NOT NULL,
    status_ref              TEXT NOT NULL DEFAULT '',
    status_category         TEXT NOT NULL DEFAULT '',
    sprint_source_ref       TEXT NOT NULL DEFAULT '',
    story_points            REAL,
    value_state             TEXT NOT NULL DEFAULT 'unknown'
                            CHECK(value_state IN ('known','unknown','unavailable','conflicting')),
    freshness_state         TEXT NOT NULL DEFAULT 'never_observed'
                            CHECK(freshness_state IN ('fresh','stale','partial','failed','never_observed')),
    latest_evidence_run_id  TEXT NOT NULL DEFAULT '',
    observed_at             TEXT NOT NULL,
    UNIQUE(source_id, board_id, source_ref)
);

CREATE TABLE IF NOT EXISTS execution_source_identities (
    identity_id             TEXT PRIMARY KEY,
    subject_kind            TEXT NOT NULL CHECK(subject_kind IN ('work_item')),
    subject_id              TEXT NOT NULL,
    source_id               TEXT NOT NULL,
    board_id                TEXT NOT NULL,
    source_ref              TEXT NOT NULL,
    first_observed_at       TEXT NOT NULL,
    last_observed_at        TEXT NOT NULL,
    active                  INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0, 1)),
    UNIQUE(subject_kind, source_id, board_id, source_ref)
);

CREATE INDEX IF NOT EXISTS idx_execution_source_identities_subject
    ON execution_source_identities(subject_kind, subject_id, active);

CREATE TABLE IF NOT EXISTS execution_work_item_observations (
    observation_id          TEXT PRIMARY KEY,
    work_item_id            TEXT NOT NULL REFERENCES execution_work_items(work_item_id),
    field_key               TEXT NOT NULL,
    from_value              TEXT NOT NULL DEFAULT '',
    to_value                TEXT NOT NULL DEFAULT '',
    source_event_ref        TEXT NOT NULL DEFAULT '',
    source_updated_at       TEXT NOT NULL,
    observed_at             TEXT NOT NULL,
    source_run_id           TEXT NOT NULL DEFAULT '',
    UNIQUE(work_item_id, field_key, source_event_ref, source_updated_at, to_value)
);

CREATE INDEX IF NOT EXISTS idx_execution_work_item_observations_item_time
    ON execution_work_item_observations(work_item_id, source_updated_at);

CREATE TABLE IF NOT EXISTS execution_sprints (
    sprint_id               TEXT PRIMARY KEY,
    project_id              TEXT NOT NULL REFERENCES projects(id),
    board_id                TEXT NOT NULL,
    source_ref              TEXT NOT NULL,
    lifecycle_state         TEXT NOT NULL DEFAULT 'unknown',
    start_date              TEXT NOT NULL DEFAULT '',
    end_date                TEXT NOT NULL DEFAULT '',
    commitment_boundary_at  TEXT NOT NULL DEFAULT '',
    commitment_boundary_basis TEXT NOT NULL DEFAULT '',
    observed_at             TEXT NOT NULL,
    UNIQUE(board_id, source_ref)
);

CREATE TABLE IF NOT EXISTS execution_release_commitments (
    release_id              TEXT PRIMARY KEY,
    project_id              TEXT NOT NULL REFERENCES projects(id),
    board_id                TEXT NOT NULL,
    source_ref              TEXT NOT NULL,
    lifecycle_state         TEXT NOT NULL DEFAULT 'unknown',
    planned_date            TEXT NOT NULL DEFAULT '',
    source_target_date      TEXT NOT NULL DEFAULT '',
    forecast_date           TEXT NOT NULL DEFAULT '',
    actual_date             TEXT NOT NULL DEFAULT '',
    first_observed_target_date TEXT NOT NULL DEFAULT '',
    target_authority        TEXT NOT NULL DEFAULT 'unknown',
    observed_at             TEXT NOT NULL,
    UNIQUE(board_id, source_ref)
);

CREATE TABLE IF NOT EXISTS execution_release_observations (
    observation_id          TEXT PRIMARY KEY,
    release_id              TEXT NOT NULL REFERENCES execution_release_commitments(release_id),
    source_target_date      TEXT NOT NULL DEFAULT '',
    actual_date             TEXT NOT NULL DEFAULT '',
    lifecycle_state         TEXT NOT NULL,
    target_authority        TEXT NOT NULL,
    observed_at             TEXT NOT NULL,
    source_input_id         TEXT NOT NULL DEFAULT '',
    UNIQUE(release_id, source_target_date, actual_date, lifecycle_state, observed_at)
);

CREATE TABLE IF NOT EXISTS execution_scope_memberships (
    membership_id           TEXT PRIMARY KEY,
    work_item_id            TEXT NOT NULL REFERENCES execution_work_items(work_item_id),
    scope_kind              TEXT NOT NULL CHECK(scope_kind IN ('sprint','release')),
    scope_id                TEXT NOT NULL,
    valid_from              TEXT NOT NULL,
    valid_to                TEXT NOT NULL DEFAULT '',
    boundary_basis          TEXT NOT NULL DEFAULT '',
    evidence_run_id         TEXT NOT NULL DEFAULT '',
    state                   TEXT NOT NULL DEFAULT 'open' CHECK(state IN ('open','closed')),
    UNIQUE(work_item_id, scope_kind, scope_id, valid_from)
);

CREATE INDEX IF NOT EXISTS idx_execution_scope_memberships_current
    ON execution_scope_memberships(scope_kind, scope_id, state);

CREATE TABLE IF NOT EXISTS execution_milestones (
    milestone_id            TEXT PRIMARY KEY,
    project_id              TEXT NOT NULL REFERENCES projects(id),
    milestone_type          TEXT NOT NULL,
    criticality             TEXT NOT NULL,
    lifecycle_state         TEXT NOT NULL,
    planned_date            TEXT NOT NULL DEFAULT '',
    source_target_date      TEXT NOT NULL DEFAULT '',
    forecast_date           TEXT NOT NULL DEFAULT '',
    actual_date             TEXT NOT NULL DEFAULT '',
    first_observed_target_date TEXT NOT NULL DEFAULT '',
    authority               TEXT NOT NULL,
    completeness_state      TEXT NOT NULL,
    observed_at             TEXT NOT NULL,
    schema_version          TEXT NOT NULL,
    latest_operation_id     TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS execution_milestone_observations (
    observation_id          TEXT PRIMARY KEY,
    milestone_id            TEXT NOT NULL REFERENCES execution_milestones(milestone_id),
    planned_date            TEXT NOT NULL DEFAULT '',
    source_target_date      TEXT NOT NULL DEFAULT '',
    forecast_date           TEXT NOT NULL DEFAULT '',
    actual_date             TEXT NOT NULL DEFAULT '',
    lifecycle_state         TEXT NOT NULL,
    authority               TEXT NOT NULL,
    completeness_state      TEXT NOT NULL,
    observed_at             TEXT NOT NULL,
    operation_id            TEXT NOT NULL DEFAULT '',
    UNIQUE(milestone_id, observed_at, lifecycle_state, planned_date, source_target_date,
           forecast_date, actual_date, authority)
);

CREATE TABLE IF NOT EXISTS execution_milestone_release_links (
    milestone_id            TEXT NOT NULL REFERENCES execution_milestones(milestone_id),
    release_id              TEXT NOT NULL REFERENCES execution_release_commitments(release_id),
    operation_id            TEXT NOT NULL DEFAULT '',
    PRIMARY KEY(milestone_id, release_id)
);

CREATE TABLE IF NOT EXISTS execution_dependencies (
    dependency_id           TEXT PRIMARY KEY,
    project_id              TEXT NOT NULL REFERENCES projects(id),
    source_link_ref         TEXT NOT NULL,
    predecessor_work_item_id TEXT NOT NULL REFERENCES execution_work_items(work_item_id),
    successor_work_item_id  TEXT NOT NULL REFERENCES execution_work_items(work_item_id),
    dependency_type         TEXT NOT NULL,
    state                   TEXT NOT NULL,
    observed_at             TEXT NOT NULL,
    evidence_run_id         TEXT NOT NULL DEFAULT '',
    UNIQUE(project_id, source_link_ref)
);

CREATE TABLE IF NOT EXISTS execution_dependency_observations (
    observation_id          TEXT PRIMARY KEY,
    dependency_id           TEXT NOT NULL REFERENCES execution_dependencies(dependency_id),
    state                   TEXT NOT NULL,
    observed_at             TEXT NOT NULL,
    evidence_run_id         TEXT NOT NULL DEFAULT '',
    UNIQUE(dependency_id, state, observed_at, evidence_run_id)
);

CREATE TABLE IF NOT EXISTS execution_derivation_runs (
    derivation_run_id       TEXT PRIMARY KEY,
    project_id              TEXT NOT NULL REFERENCES projects(id),
    board_id                TEXT NOT NULL,
    rule_version            TEXT NOT NULL,
    input_fingerprint       TEXT NOT NULL UNIQUE,
    completeness_state      TEXT NOT NULL,
    freshness_state         TEXT NOT NULL,
    warning_codes_json      TEXT NOT NULL DEFAULT '[]' CHECK(json_valid(warning_codes_json)),
    fact_count              INTEGER NOT NULL DEFAULT 0,
    started_at              TEXT NOT NULL,
    finished_at             TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS execution_derivation_inputs (
    derivation_run_id       TEXT NOT NULL REFERENCES execution_derivation_runs(derivation_run_id)
                            ON DELETE CASCADE,
    input_kind              TEXT NOT NULL CHECK(input_kind IN ('source_evidence_run','legacy_sync','milestone_operation')),
    input_id                TEXT NOT NULL,
    PRIMARY KEY(derivation_run_id, input_kind, input_id)
);

CREATE TABLE IF NOT EXISTS execution_facts (
    fact_id                 TEXT PRIMARY KEY,
    derivation_run_id       TEXT NOT NULL REFERENCES execution_derivation_runs(derivation_run_id),
    project_id              TEXT NOT NULL REFERENCES projects(id),
    subject_kind            TEXT NOT NULL,
    subject_id              TEXT NOT NULL,
    fact_key                TEXT NOT NULL,
    value_json              TEXT NOT NULL CHECK(json_valid(value_json)),
    value_state             TEXT NOT NULL CHECK(value_state IN ('known','unknown','unavailable','conflicting')),
    freshness_state         TEXT NOT NULL CHECK(freshness_state IN ('fresh','stale','partial','failed','never_observed')),
    evidence_json           TEXT NOT NULL DEFAULT '{}' CHECK(json_valid(evidence_json)),
    UNIQUE(derivation_run_id, subject_kind, subject_id, fact_key)
);

CREATE INDEX IF NOT EXISTS idx_execution_facts_project_subject
    ON execution_facts(project_id, subject_kind, subject_id, fact_key);

CREATE TABLE IF NOT EXISTS milestone_import_operations (
    operation_id            TEXT PRIMARY KEY,
    status                  TEXT NOT NULL CHECK(status IN ('proposed','claimed','confirmed','expired','rejected')),
    token_hash              TEXT NOT NULL UNIQUE,
    request_json            TEXT NOT NULL CHECK(json_valid(request_json)),
    proposed_json           TEXT NOT NULL CHECK(json_valid(proposed_json)),
    fingerprint             TEXT NOT NULL,
    created_at              TEXT NOT NULL,
    expires_at              TEXT NOT NULL,
    confirmed_at            TEXT NOT NULL DEFAULT '',
    result_json             TEXT NOT NULL DEFAULT '{}' CHECK(json_valid(result_json)),
    failure_code            TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_milestone_import_operations_status_expiry
    ON milestone_import_operations(status, expires_at);
"""
