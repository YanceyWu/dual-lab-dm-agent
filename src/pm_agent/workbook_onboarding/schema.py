"""Schema owned by the workbook onboarding capability."""

WORKBOOK_ONBOARDING_DDL = """
CREATE TABLE IF NOT EXISTS onboarding_profiles (
    profile_id TEXT PRIMARY KEY,
    profile_key TEXT NOT NULL UNIQUE,
    member_key_type TEXT NOT NULL,
    project_key_type TEXT NOT NULL,
    baseline_source TEXT NOT NULL,
    adjustment_source TEXT NOT NULL,
    conflict_policy TEXT NOT NULL,
    current_revision INTEGER NOT NULL DEFAULT 0 CHECK(current_revision >= 0),
    status TEXT NOT NULL CHECK(status IN ('active','inactive')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""
