"""Additive schema owned by the Copilot interaction-memory capability."""

INTERACTION_MEMORY_DDL = """
CREATE TABLE IF NOT EXISTS interaction_memory_scopes (
    scope_id TEXT PRIMARY KEY,
    scope_source TEXT NOT NULL CHECK(scope_source IN ('project_id','repo_root_fingerprint')),
    scope_key TEXT NOT NULL,
    scope_display_name TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1 CHECK(enabled IN (0,1)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(scope_source, scope_key)
);

CREATE INDEX IF NOT EXISTS idx_interaction_memory_scopes_enabled
    ON interaction_memory_scopes(enabled, updated_at);

CREATE TABLE IF NOT EXISTS interaction_memory_entries (
    entry_id TEXT PRIMARY KEY,
    scope_id TEXT NOT NULL REFERENCES interaction_memory_scopes(scope_id)
        ON DELETE CASCADE,
    memory_kind TEXT NOT NULL CHECK(memory_kind IN ('preference','context','follow_up','strategy')),
    category TEXT NOT NULL,
    title TEXT NOT NULL DEFAULT '',
    summary TEXT NOT NULL DEFAULT '',
    state TEXT NOT NULL CHECK(state IN (
        'active','disabled','cleared','expired',
        'open','snoozed','done',
        'suppressed','retired'
    )),
    confidence REAL NOT NULL DEFAULT 1.0 CHECK(confidence BETWEEN 0.0 AND 1.0),
    weight REAL NOT NULL DEFAULT 1.0,
    metadata_json TEXT NOT NULL DEFAULT '{}' CHECK(json_valid(metadata_json)),
    interaction_event_ref_json TEXT NOT NULL DEFAULT '{}' CHECK(json_valid(interaction_event_ref_json)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(scope_id, memory_kind, category, title)
);

CREATE INDEX IF NOT EXISTS idx_interaction_memory_entries_scope_kind_state
    ON interaction_memory_entries(scope_id, memory_kind, state, updated_at);

CREATE INDEX IF NOT EXISTS idx_interaction_memory_entries_scope_weight
    ON interaction_memory_entries(scope_id, weight DESC, confidence DESC, updated_at DESC);

CREATE TABLE IF NOT EXISTS interaction_memory_audit (
    audit_id TEXT PRIMARY KEY,
    scope_id TEXT NOT NULL,
    entry_id TEXT NOT NULL DEFAULT '',
    operation_type TEXT NOT NULL,
    interaction_event_ref_json TEXT NOT NULL CHECK(json_valid(interaction_event_ref_json)),
    prior_state_json TEXT NOT NULL DEFAULT '{}' CHECK(json_valid(prior_state_json)),
    new_state_json TEXT NOT NULL DEFAULT '{}' CHECK(json_valid(new_state_json)),
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_interaction_memory_audit_scope_created
    ON interaction_memory_audit(scope_id, created_at DESC);
"""
