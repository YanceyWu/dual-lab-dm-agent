"""Dedicated additive schema for structured data onboarding."""

from __future__ import annotations

import json
import sqlite3

from pm_agent.data_onboarding.workbook_contract import (
    WORKBOOK_DEFAULT_DISPLAY_NAME,
    WORKBOOK_MAPPING_PRESET_ID,
    WORKBOOK_PLAN_NAMING_POLICY,
    WORKBOOK_SOURCE_TYPE,
    WORKBOOK_DEFAULT_SOURCE_OPTIONS,
)

DATA_ONBOARDING_DDL = """
CREATE TABLE IF NOT EXISTS onboarding_profiles (
    profile_id TEXT PRIMARY KEY,
    profile_key TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL DEFAULT '',
    source_type TEXT NOT NULL DEFAULT '',
    source_locator TEXT NOT NULL DEFAULT '',
    mapping_preset_id TEXT NOT NULL DEFAULT '',
    member_key_type TEXT NOT NULL,
    project_key_type TEXT NOT NULL,
    baseline_source TEXT NOT NULL,
    adjustment_source TEXT NOT NULL,
    conflict_policy TEXT NOT NULL,
    plan_naming_policy TEXT NOT NULL DEFAULT '',
    source_options_json TEXT NOT NULL DEFAULT '{}' CHECK(json_valid(source_options_json)),
    current_revision INTEGER NOT NULL DEFAULT 0 CHECK(current_revision >= 0),
    status TEXT NOT NULL CHECK(status IN ('active','inactive')),
    last_successful_run_id TEXT NOT NULL DEFAULT '',
    last_successful_run_at TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS data_onboarding_runs (
    run_id TEXT PRIMARY KEY,
    profile_id TEXT NOT NULL REFERENCES onboarding_profiles(profile_id),
    profile_key TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_locator TEXT NOT NULL,
    profile_snapshot_json TEXT NOT NULL CHECK(json_valid(profile_snapshot_json)),
    source_identity_json TEXT NOT NULL CHECK(json_valid(source_identity_json)),
    preview_fingerprint TEXT NOT NULL,
    source_preview_json TEXT NOT NULL CHECK(json_valid(source_preview_json)),
    preview_json TEXT NOT NULL CHECK(json_valid(preview_json)),
    confirm_json TEXT NOT NULL DEFAULT '{}' CHECK(json_valid(confirm_json)),
    status TEXT NOT NULL CHECK(status IN ('previewed','running','completed','partially_completed','failed','rejected')),
    created_at TEXT NOT NULL,
    completed_at TEXT NOT NULL DEFAULT '',
    failure_code TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_data_onboarding_runs_profile_fingerprint
    ON data_onboarding_runs(profile_id, preview_fingerprint);

CREATE INDEX IF NOT EXISTS idx_data_onboarding_runs_profile_status
    ON data_onboarding_runs(profile_key, status, created_at);

CREATE TABLE IF NOT EXISTS data_onboarding_run_attempts (
    attempt_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES data_onboarding_runs(run_id),
    status TEXT NOT NULL CHECK(status IN ('running','completed','failed')),
    started_at TEXT NOT NULL,
    finished_at TEXT NOT NULL DEFAULT '',
    failure_code TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_data_onboarding_attempts_run
    ON data_onboarding_run_attempts(run_id, started_at);

CREATE TABLE IF NOT EXISTS data_onboarding_publication_links (
    link_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES data_onboarding_runs(run_id),
    capability_key TEXT NOT NULL,
    status TEXT NOT NULL,
    domain_session_id TEXT NOT NULL DEFAULT '',
    domain_publication_id TEXT NOT NULL DEFAULT '',
    domain_plan_version_id TEXT NOT NULL DEFAULT '',
    details_json TEXT NOT NULL DEFAULT '{}' CHECK(json_valid(details_json)),
    created_at TEXT NOT NULL,
    UNIQUE(run_id, capability_key)
);

CREATE INDEX IF NOT EXISTS idx_data_onboarding_links_run
    ON data_onboarding_publication_links(run_id, capability_key);

CREATE TABLE IF NOT EXISTS data_onboarding_plan_reservations (
    reservation_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL UNIQUE,
    source_type TEXT NOT NULL,
    profile_key TEXT NOT NULL,
    requested_name TEXT NOT NULL,
    version_name TEXT NOT NULL,
    plan_version_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('reserved','released')),
    created_at TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_data_onboarding_reserved_version_name
    ON data_onboarding_plan_reservations(version_name)
    WHERE status='reserved';

CREATE UNIQUE INDEX IF NOT EXISTS idx_data_onboarding_reserved_plan_id
    ON data_onboarding_plan_reservations(plan_version_id)
    WHERE status='reserved';

CREATE INDEX IF NOT EXISTS idx_data_onboarding_reservations_profile
    ON data_onboarding_plan_reservations(profile_key, requested_name, status, created_at);
"""


def ensure_onboarding_profile_columns(connection: sqlite3.Connection) -> None:
    """Keep earlier local databases readable while Batch A is additive."""

    columns = {
        row[1] for row in connection.execute("PRAGMA table_info(onboarding_profiles)").fetchall()
    }
    migrations = {
        "display_name": "ALTER TABLE onboarding_profiles ADD COLUMN display_name TEXT NOT NULL DEFAULT ''",
        "source_type": "ALTER TABLE onboarding_profiles ADD COLUMN source_type TEXT NOT NULL DEFAULT ''",
        "source_locator": "ALTER TABLE onboarding_profiles ADD COLUMN source_locator TEXT NOT NULL DEFAULT ''",
        "mapping_preset_id": "ALTER TABLE onboarding_profiles ADD COLUMN mapping_preset_id TEXT NOT NULL DEFAULT ''",
        "plan_naming_policy": "ALTER TABLE onboarding_profiles ADD COLUMN plan_naming_policy TEXT NOT NULL DEFAULT ''",
        "source_options_json": "ALTER TABLE onboarding_profiles ADD COLUMN source_options_json TEXT NOT NULL DEFAULT '{}' CHECK(json_valid(source_options_json))",
        "last_successful_run_id": "ALTER TABLE onboarding_profiles ADD COLUMN last_successful_run_id TEXT NOT NULL DEFAULT ''",
        "last_successful_run_at": "ALTER TABLE onboarding_profiles ADD COLUMN last_successful_run_at TEXT NOT NULL DEFAULT ''",
    }
    for column, statement in migrations.items():
        if column not in columns:
            connection.execute(statement)
    connection.execute(
        """
        UPDATE onboarding_profiles
        SET display_name = CASE WHEN display_name='' THEN ? ELSE display_name END,
            source_type = CASE WHEN source_type='' THEN ? ELSE source_type END,
            mapping_preset_id = CASE WHEN mapping_preset_id='' THEN ? ELSE mapping_preset_id END,
            plan_naming_policy = CASE WHEN plan_naming_policy='' THEN ? ELSE plan_naming_policy END,
            source_options_json = CASE
                WHEN source_options_json='{}' THEN ?
                ELSE source_options_json
            END
        WHERE profile_key='default'
          AND baseline_source='workbook'
          AND adjustment_source='copilot'
          AND conflict_policy='copilot_wins_workbook_blocked'
        """,
        [
            WORKBOOK_DEFAULT_DISPLAY_NAME,
            WORKBOOK_SOURCE_TYPE,
            WORKBOOK_MAPPING_PRESET_ID,
            WORKBOOK_PLAN_NAMING_POLICY,
            json.dumps(WORKBOOK_DEFAULT_SOURCE_OPTIONS, sort_keys=True),
        ],
    )
    connection.execute("DROP INDEX IF EXISTS idx_data_onboarding_runs_profile_fingerprint")
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_data_onboarding_runs_profile_fingerprint
            ON data_onboarding_runs(profile_id, preview_fingerprint)
        """
    )
    reservation_table_exists = connection.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type='table' AND name='data_onboarding_plan_reservations'
        """
    ).fetchone()
    if reservation_table_exists:
        reservation_columns = {
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(data_onboarding_plan_reservations)"
            ).fetchall()
        }
        if "run_id" not in reservation_columns:
            connection.execute(
                """
                ALTER TABLE data_onboarding_plan_reservations
                ADD COLUMN run_id TEXT NOT NULL DEFAULT ''
                """
            )
        connection.execute(
            """
            UPDATE data_onboarding_plan_reservations
            SET run_id = reservation_id
            WHERE run_id = ''
            """
        )
        connection.execute("DROP INDEX IF EXISTS idx_data_onboarding_reserved_run")
        connection.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_data_onboarding_reserved_run
                ON data_onboarding_plan_reservations(run_id)
            """
        )
