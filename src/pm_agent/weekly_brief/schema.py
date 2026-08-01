"""Additive storage owned only by the Weekly Brief v2 snapshot core."""

WEEKLY_BRIEF_SNAPSHOT_DDL = """
CREATE TABLE IF NOT EXISTS weekly_brief_snapshot_operations (
    operation_id TEXT PRIMARY KEY,
    snapshot_id TEXT UNIQUE,
    execution_id TEXT NOT NULL,
    contract_version TEXT NOT NULL,
    comparison_rule_version TEXT NOT NULL,
    generated_at TEXT NOT NULL,
    week_key TEXT NOT NULL,
    scope_json TEXT NOT NULL CHECK(json_valid(scope_json)),
    scope_fingerprint TEXT NOT NULL,
    input_fingerprint TEXT NOT NULL,
    baseline_snapshot_id TEXT NOT NULL DEFAULT '',
    baseline_fingerprint TEXT NOT NULL DEFAULT '',
    statement_fingerprint TEXT NOT NULL,
    evidence_state_fingerprint TEXT NOT NULL,
    result_fingerprint TEXT NOT NULL,
    candidate_json TEXT NOT NULL CHECK(json_valid(candidate_json)),
    statement_manifest_json TEXT NOT NULL CHECK(json_valid(statement_manifest_json)),
    evidence_summary_json TEXT NOT NULL CHECK(json_valid(evidence_summary_json)),
    section_coverage_json TEXT NOT NULL CHECK(json_valid(section_coverage_json)),
    limitation_codes_json TEXT NOT NULL CHECK(json_valid(limitation_codes_json)),
    structural_status TEXT NOT NULL CHECK(structural_status IN ('complete','failed')),
    actor_id TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    confirmation_token_hash TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('proposed','claimed','confirmed','expired','failed')),
    created_at TEXT NOT NULL,
    claimed_at TEXT NOT NULL DEFAULT '',
    confirmed_at TEXT NOT NULL DEFAULT '',
    failure_code TEXT NOT NULL DEFAULT '',
    UNIQUE(actor_id, idempotency_key)
);

CREATE INDEX IF NOT EXISTS idx_weekly_brief_snapshot_confirmed
    ON weekly_brief_snapshot_operations(status, scope_fingerprint, confirmed_at);
CREATE INDEX IF NOT EXISTS idx_weekly_brief_snapshot_execution
    ON weekly_brief_snapshot_operations(execution_id);
"""
