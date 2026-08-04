"""Persistence helpers for structured data onboarding."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator
from uuid import uuid4

from pm_agent.config import settings
from pm_agent.data_onboarding.models import (
    DomainLinkRecord,
    SourceProfileRecord,
    SourceProfileUpsert,
)
from pm_agent.data_onboarding.workbook_contract import (
    WORKBOOK_ADJUSTMENT_SOURCE,
    WORKBOOK_BASELINE_SOURCE,
    WORKBOOK_CONFLICT_POLICY,
    WORKBOOK_DEFAULT_DISPLAY_NAME,
    WORKBOOK_DEFAULT_PROFILE_ID,
    WORKBOOK_DEFAULT_PROFILE_KEY,
    WORKBOOK_DEFAULT_SOURCE_OPTIONS,
    WORKBOOK_MAPPING_PRESET_ID,
    WORKBOOK_MEMBER_KEY_TYPE,
    WORKBOOK_PLAN_NAMING_POLICY,
    WORKBOOK_PROJECT_KEY_TYPE,
    WORKBOOK_SOURCE_TYPE,
)
from pm_agent.workbook_onboarding.presets import default_source_options


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def connection(db_path: str | Path | None = None) -> Iterator[sqlite3.Connection]:
    database = sqlite3.connect(Path(db_path or settings.database_path), isolation_level=None)
    database.row_factory = sqlite3.Row
    database.execute("PRAGMA foreign_keys = ON")
    database.execute("PRAGMA busy_timeout = 10000")
    try:
        yield database
    finally:
        database.close()


def _profile_from_row(row: sqlite3.Row) -> SourceProfileRecord:
    return SourceProfileRecord(
        profile_id=str(row["profile_id"]),
        profile_key=str(row["profile_key"]),
        display_name=str(row["display_name"]),
        source_type=str(row["source_type"]),
        source_locator=str(row["source_locator"]),
        mapping_preset_id=str(row["mapping_preset_id"]),
        member_key_type=str(row["member_key_type"]),
        project_key_type=str(row["project_key_type"]),
        baseline_source=str(row["baseline_source"]),
        adjustment_source=str(row["adjustment_source"]),
        conflict_policy=str(row["conflict_policy"]),
        plan_naming_policy=str(row["plan_naming_policy"]),
        source_options=json.loads(row["source_options_json"]),
        current_revision=int(row["current_revision"]),
        status=str(row["status"]),
        last_successful_run_id=str(row["last_successful_run_id"]),
        last_successful_run_at=str(row["last_successful_run_at"]),
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )


def load_profile(
    profile_key: str, *, db_path: str | Path | None = None
) -> SourceProfileRecord | None:
    with connection(db_path) as database:
        row = database.execute(
            "SELECT * FROM onboarding_profiles WHERE profile_key=?",
            [profile_key],
        ).fetchone()
    return _profile_from_row(row) if row else None


def list_profiles(
    *, status: str | None = None, db_path: str | Path | None = None
) -> list[SourceProfileRecord]:
    query = "SELECT * FROM onboarding_profiles"
    params: list[Any] = []
    if status is not None:
        query += " WHERE status=?"
        params.append(status)
    query += " ORDER BY profile_key"
    with connection(db_path) as database:
        rows = database.execute(query, params).fetchall()
    return [_profile_from_row(row) for row in rows]


def save_profile(
    profile: SourceProfileUpsert, *, db_path: str | Path | None = None
) -> SourceProfileRecord:
    now = _utc_now()
    with connection(db_path) as database:
        database.execute("BEGIN IMMEDIATE")
        existing = database.execute(
            "SELECT * FROM onboarding_profiles WHERE profile_key=?",
            [profile.profile_key],
        ).fetchone()
        if existing is None:
            database.execute(
                """
                INSERT INTO onboarding_profiles
                    (profile_id,profile_key,display_name,source_type,source_locator,
                     mapping_preset_id,member_key_type,project_key_type,baseline_source,
                     adjustment_source,conflict_policy,plan_naming_policy,source_options_json,
                     current_revision,status,last_successful_run_id,last_successful_run_at,
                     created_at,updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,0,?,'','',?,?)
                """,
                [
                    profile.profile_id,
                    profile.profile_key,
                    profile.display_name,
                    profile.source_type,
                    profile.source_locator,
                    profile.mapping_preset_id,
                    profile.member_key_type,
                    profile.project_key_type,
                    profile.baseline_source,
                    profile.adjustment_source,
                    profile.conflict_policy,
                    profile.plan_naming_policy,
                    _json(profile.source_options),
                    profile.status,
                    now,
                    now,
                ],
            )
        else:
            database.execute(
                """
                UPDATE onboarding_profiles
                SET display_name=?,
                    source_type=?,
                    source_locator=?,
                    mapping_preset_id=?,
                    member_key_type=?,
                    project_key_type=?,
                    baseline_source=?,
                    adjustment_source=?,
                    conflict_policy=?,
                    plan_naming_policy=?,
                    source_options_json=?,
                    status=?,
                    updated_at=?
                WHERE profile_key=?
                """,
                [
                    profile.display_name,
                    profile.source_type,
                    profile.source_locator,
                    profile.mapping_preset_id,
                    profile.member_key_type,
                    profile.project_key_type,
                    profile.baseline_source,
                    profile.adjustment_source,
                    profile.conflict_policy,
                    profile.plan_naming_policy,
                    _json(profile.source_options),
                    profile.status,
                    now,
                    profile.profile_key,
                ],
            )
        row = database.execute(
            "SELECT * FROM onboarding_profiles WHERE profile_key=?",
            [profile.profile_key],
        ).fetchone()
        database.commit()
    if row is None:
        raise RuntimeError("DATA_ONBOARDING_PROFILE_SAVE_FAILED")
    return _profile_from_row(row)


def ensure_workbook_default_profile(
    *, db_path: str | Path | None = None
) -> SourceProfileRecord:
    existing = load_profile(WORKBOOK_DEFAULT_PROFILE_KEY, db_path=db_path)
    mapping_preset_id = (
        existing.mapping_preset_id
        if existing and existing.mapping_preset_id
        else WORKBOOK_MAPPING_PRESET_ID
    )
    try:
        source_options = default_source_options(mapping_preset_id)
    except ValueError as exc:
        if str(exc) != "WORKBOOK_MAPPING_PRESET_UNKNOWN":
            raise
        source_options = (
            existing.source_options
            if existing and existing.source_options
            else dict(WORKBOOK_DEFAULT_SOURCE_OPTIONS)
        )
    profile = SourceProfileUpsert(
        profile_id=existing.profile_id if existing else WORKBOOK_DEFAULT_PROFILE_ID,
        profile_key=WORKBOOK_DEFAULT_PROFILE_KEY,
        display_name=existing.display_name if existing and existing.display_name else WORKBOOK_DEFAULT_DISPLAY_NAME,
        source_type=existing.source_type if existing and existing.source_type else WORKBOOK_SOURCE_TYPE,
        source_locator=existing.source_locator if existing else "",
        mapping_preset_id=mapping_preset_id,
        member_key_type=existing.member_key_type if existing and existing.member_key_type else WORKBOOK_MEMBER_KEY_TYPE,
        project_key_type=existing.project_key_type if existing and existing.project_key_type else WORKBOOK_PROJECT_KEY_TYPE,
        baseline_source=existing.baseline_source if existing and existing.baseline_source else WORKBOOK_BASELINE_SOURCE,
        adjustment_source=existing.adjustment_source if existing and existing.adjustment_source else WORKBOOK_ADJUSTMENT_SOURCE,
        conflict_policy=existing.conflict_policy if existing and existing.conflict_policy else WORKBOOK_CONFLICT_POLICY,
        plan_naming_policy=existing.plan_naming_policy if existing and existing.plan_naming_policy else WORKBOOK_PLAN_NAMING_POLICY,
        source_options=source_options,
        status="active",
    )
    return save_profile(profile, db_path=db_path)


def next_profile_revision(
    *, profile_key: str, db_path: str | Path | None = None
) -> int:
    profile = load_profile(profile_key, db_path=db_path)
    if profile is None:
        raise ValueError("DATA_ONBOARDING_PROFILE_NOT_FOUND")
    return profile.current_revision + 1


def claim_profile_revision(
    *,
    profile_key: str,
    expected_revision: int,
    db_path: str | Path | None = None,
) -> int:
    if expected_revision < 1:
        raise ValueError("DATA_ONBOARDING_PROFILE_REVISION_INVALID")
    with connection(db_path) as database:
        database.execute("BEGIN IMMEDIATE")
        profile = database.execute(
            "SELECT current_revision,status FROM onboarding_profiles WHERE profile_key=?",
            [profile_key],
        ).fetchone()
        if profile is None:
            database.commit()
            raise ValueError("DATA_ONBOARDING_PROFILE_NOT_FOUND")
        if str(profile["status"]) != "active":
            database.commit()
            raise ValueError("DATA_ONBOARDING_PROFILE_INACTIVE")
        current_revision = int(profile["current_revision"])
        if current_revision != expected_revision - 1:
            database.commit()
            raise ValueError("DATA_ONBOARDING_PROFILE_REVISION_CONFLICT")
        database.execute(
            """
            UPDATE onboarding_profiles
            SET current_revision=?, updated_at=?
            WHERE profile_key=?
            """,
            [expected_revision, _utc_now(), profile_key],
        )
        database.commit()
    return expected_revision


def record_profile_success(
    *,
    profile_key: str,
    run_id: str,
    completed_at: str,
    db_path: str | Path | None = None,
) -> None:
    with connection(db_path) as database:
        database.execute(
            """
            UPDATE onboarding_profiles
            SET last_successful_run_id=?, last_successful_run_at=?, updated_at=?
            WHERE profile_key=?
            """,
            [run_id, completed_at, completed_at, profile_key],
        )


def restore_profile_revision(
    *,
    profile_key: str,
    claimed_revision: int,
    db_path: str | Path | None = None,
) -> None:
    if claimed_revision < 1:
        return
    with connection(db_path) as database:
        database.execute("BEGIN IMMEDIATE")
        profile = database.execute(
            "SELECT current_revision FROM onboarding_profiles WHERE profile_key=?",
            [profile_key],
        ).fetchone()
        if profile is None:
            database.commit()
            return
        if int(profile["current_revision"]) == claimed_revision:
            database.execute(
                """
                UPDATE onboarding_profiles
                SET current_revision=?, updated_at=?
                WHERE profile_key=?
                """,
                [claimed_revision - 1, _utc_now(), profile_key],
            )
        database.commit()


def find_run_by_fingerprint(
    profile_id: str,
    preview_fingerprint: str,
    *,
    db_path: str | Path | None = None,
) -> dict[str, Any] | None:
    with connection(db_path) as database:
        row = database.execute(
            """
            SELECT * FROM data_onboarding_runs
            WHERE profile_id=? AND preview_fingerprint=?
            ORDER BY rowid DESC
            LIMIT 1
            """,
            [profile_id, preview_fingerprint],
        ).fetchone()
    return dict(row) if row else None


def create_run(
    *,
    run_id: str,
    profile: SourceProfileRecord,
    profile_snapshot: dict[str, Any],
    source_identity: dict[str, Any],
    preview_fingerprint: str,
    source_preview: dict[str, Any],
    preview_payload: dict[str, Any],
    status: str,
    created_at: str,
    failure_code: str = "",
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    with connection(db_path) as database:
        database.execute("BEGIN IMMEDIATE")
        database.execute(
            """
            INSERT INTO data_onboarding_runs
                (run_id,profile_id,profile_key,source_type,source_locator,
                 profile_snapshot_json,source_identity_json,preview_fingerprint,
                 source_preview_json,preview_json,confirm_json,status,
                 created_at,completed_at,failure_code)
            VALUES (?,?,?,?,?,?,?,?,?,?,? ,?,?,?,?)
            """,
            [
                run_id,
                profile.profile_id,
                profile.profile_key,
                profile.source_type,
                profile.source_locator,
                _json(profile_snapshot),
                _json(source_identity),
                preview_fingerprint,
                _json(source_preview),
                _json(preview_payload),
                "{}",
                status,
                created_at,
                created_at if status == "rejected" else "",
                failure_code,
            ],
        )
        row = database.execute(
            "SELECT * FROM data_onboarding_runs WHERE run_id=?",
            [run_id],
        ).fetchone()
        database.commit()
    if row is None:
        raise RuntimeError("DATA_ONBOARDING_RUN_CREATE_FAILED")
    return dict(row)


def load_run(
    run_id: str, *, db_path: str | Path | None = None
) -> dict[str, Any] | None:
    with connection(db_path) as database:
        row = database.execute(
            "SELECT * FROM data_onboarding_runs WHERE run_id=?",
            [run_id],
        ).fetchone()
    return dict(row) if row else None


def start_run_attempt(
    run_id: str, *, started_at: str, db_path: str | Path | None = None
) -> str:
    attempt_id = f"data-onboarding-attempt-{uuid4().hex}"
    with connection(db_path) as database:
        database.execute("BEGIN IMMEDIATE")
        claimed = database.execute(
            """
            UPDATE data_onboarding_runs
            SET status='running', failure_code='', completed_at=''
            WHERE run_id=? AND status IN ('previewed','failed','partially_completed')
            """,
            [run_id],
        )
        if claimed.rowcount != 1:
            database.commit()
            raise ValueError("DATA_ONBOARDING_RUN_NOT_CONFIRMABLE")
        database.execute(
            """
            INSERT INTO data_onboarding_run_attempts
                (attempt_id,run_id,status,started_at)
            VALUES (?,?,'running',?)
            """,
            [attempt_id, run_id, started_at],
        )
        database.commit()
    return attempt_id


def finish_run(
    *,
    run_id: str,
    attempt_id: str,
    run_status: str,
    confirm_payload: dict[str, Any],
    failure_code: str,
    finished_at: str,
    links: list[DomainLinkRecord],
    profile_key: str | None = None,
    db_path: str | Path | None = None,
) -> None:
    with connection(db_path) as database:
        database.execute("BEGIN IMMEDIATE")
        database.execute(
            """
            UPDATE data_onboarding_run_attempts
            SET status='completed', finished_at=?, failure_code=?
            WHERE attempt_id=?
            """,
            [finished_at, failure_code, attempt_id],
        )
        for link in links:
            database.execute(
                """
                INSERT INTO data_onboarding_publication_links
                    (link_id,run_id,capability_key,status,domain_session_id,
                     domain_publication_id,domain_plan_version_id,details_json,created_at)
                VALUES (?,?,?,?,?,?,?,?,?)
                ON CONFLICT(run_id, capability_key) DO UPDATE SET
                    status=excluded.status,
                    domain_session_id=excluded.domain_session_id,
                    domain_publication_id=excluded.domain_publication_id,
                    domain_plan_version_id=excluded.domain_plan_version_id,
                    details_json=excluded.details_json
                """,
                [
                    f"data-onboarding-link-{uuid4().hex}",
                    run_id,
                    link.capability_key,
                    link.status,
                    link.domain_session_id,
                    link.domain_publication_id,
                    link.domain_plan_version_id,
                    _json(link.details),
                    finished_at,
                ],
            )
        database.execute(
            """
            UPDATE data_onboarding_runs
            SET status=?, completed_at=?, failure_code=?, confirm_json=?
            WHERE run_id=?
            """,
            [run_status, finished_at, failure_code, _json(confirm_payload), run_id],
        )
        if run_status == "completed" and profile_key:
            database.execute(
                """
                UPDATE onboarding_profiles
                SET last_successful_run_id=?, last_successful_run_at=?, updated_at=?
                WHERE profile_key=?
                """,
                [run_id, finished_at, finished_at, profile_key],
            )
        database.commit()


def recover_running_run(
    *,
    run_id: str,
    failure_code: str,
    finished_at: str,
    db_path: str | Path | None = None,
) -> None:
    with connection(db_path) as database:
        database.execute("BEGIN IMMEDIATE")
        database.execute(
            """
            UPDATE data_onboarding_run_attempts
            SET status='failed', finished_at=?, failure_code=?
            WHERE run_id=? AND status='running'
            """,
            [finished_at, failure_code, run_id],
        )
        database.execute(
            """
            UPDATE data_onboarding_runs
            SET status='failed', completed_at=?, failure_code=?
            WHERE run_id=? AND status='running'
            """,
            [finished_at, failure_code, run_id],
        )
        database.commit()


def has_running_attempt(
    run_id: str, *, db_path: str | Path | None = None
) -> bool:
    with connection(db_path) as database:
        row = database.execute(
            """
            SELECT 1
            FROM data_onboarding_run_attempts
            WHERE run_id=? AND status='running'
            LIMIT 1
            """,
            [run_id],
        ).fetchone()
    return row is not None


def fail_attempt(
    *,
    run_id: str,
    attempt_id: str,
    failure_code: str,
    finished_at: str,
    db_path: str | Path | None = None,
) -> None:
    with connection(db_path) as database:
        database.execute("BEGIN IMMEDIATE")
        database.execute(
            """
            UPDATE data_onboarding_run_attempts
            SET status='failed', finished_at=?, failure_code=?
            WHERE attempt_id=?
            """,
            [finished_at, failure_code, attempt_id],
        )
        database.execute(
            """
            UPDATE data_onboarding_runs
            SET status='failed', completed_at=?, failure_code=?
            WHERE run_id=?
            """,
            [finished_at, failure_code, run_id],
        )
        database.commit()


def load_links(
    run_id: str, *, db_path: str | Path | None = None
) -> list[dict[str, Any]]:
    with connection(db_path) as database:
        rows = database.execute(
            """
            SELECT * FROM data_onboarding_publication_links
            WHERE run_id=?
            ORDER BY capability_key
            """,
            [run_id],
        ).fetchall()
    return [dict(row) for row in rows]
