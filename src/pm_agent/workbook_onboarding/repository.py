"""Persistence helpers for workbook onboarding profile and plan naming."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator
from uuid import uuid4

from pm_agent.config import settings
from pm_agent.data_onboarding import repository as onboarding_repository
from pm_agent.rules.identity import slugify_text

_VERSION_SUFFIX_RE = re.compile(r"^(?P<base>.+)-v(?P<version>[2-9]\d*)$")


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


def ensure_default_onboarding_profile(
    *, db_path: str | Path | None = None
) -> dict[str, Any]:
    profile = onboarding_repository.ensure_workbook_default_profile(db_path=db_path)
    return asdict(profile)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def resolve_plan_identity(
    requested_name: str,
    *,
    profile_key: str = "default",
    run_id: str | None = None,
    db_path: str | Path | None = None,
) -> dict[str, str]:
    final_name = requested_name.strip()
    if not final_name:
        raise ValueError("WORKBOOK_ONBOARDING_PLAN_VERSION_NAME_REQUIRED")
    if run_id is None:
        return _resolve_plan_identity_without_reservation(
            final_name,
            profile_key=profile_key,
            db_path=db_path,
        )
    with connection(db_path) as database:
        database.execute("BEGIN IMMEDIATE")
        reserved = database.execute(
            """
            SELECT version_name, plan_version_id
            FROM data_onboarding_plan_reservations
            WHERE run_id=? AND status='reserved'
            """,
            [run_id],
        ).fetchone()
        if reserved is not None:
            database.commit()
            return {
                "plan_version_id": str(reserved["plan_version_id"]),
                "version_name": str(reserved["version_name"]),
            }
        same_profile_reserved = database.execute(
            """
            SELECT version_name, plan_version_id
            FROM data_onboarding_plan_reservations
            WHERE profile_key=?
              AND requested_name=?
              AND status='reserved'
            ORDER BY created_at DESC
            LIMIT 1
            """,
            [profile_key, final_name],
        ).fetchone()
        if same_profile_reserved is not None:
            database.commit()
            return {
                "plan_version_id": str(same_profile_reserved["plan_version_id"]),
                "version_name": str(same_profile_reserved["version_name"]),
            }
        existing_names = [
            row["version_name"]
            for row in database.execute("SELECT version_name FROM plan_versions").fetchall()
        ]
        existing_ids = {
            row["plan_version_id"]
            for row in database.execute("SELECT plan_version_id FROM plan_versions").fetchall()
        }
        reservation_rows = database.execute(
            """
            SELECT version_name, plan_version_id
            FROM data_onboarding_plan_reservations
            WHERE status='reserved' AND run_id<>?
            """,
            [run_id],
        ).fetchall()
        existing_names.extend(str(row["version_name"]) for row in reservation_rows)
        existing_ids.update(str(row["plan_version_id"]) for row in reservation_rows)
        resolved = _resolved_plan_identity(final_name, existing_names, existing_ids)
        database.execute(
            """
            INSERT INTO data_onboarding_plan_reservations
                (reservation_id,run_id,source_type,profile_key,requested_name,
                 version_name,plan_version_id,status,created_at)
            VALUES (?,?,?,?,?,?,?,?,?)
            """,
            [
                f"data-onboarding-plan-reservation-{uuid4().hex}",
                run_id,
                "workbook",
                profile_key,
                final_name,
                resolved["version_name"],
                resolved["plan_version_id"],
                "reserved",
                _utc_now(),
            ],
        )
        database.commit()
    return resolved


def _resolve_plan_identity_without_reservation(
    final_name: str,
    *,
    profile_key: str,
    db_path: str | Path | None = None,
) -> dict[str, str]:
    with connection(db_path) as database:
        existing_names = [
            row["version_name"]
            for row in database.execute("SELECT version_name FROM plan_versions").fetchall()
        ]
        existing_ids = {
            row["plan_version_id"]
            for row in database.execute("SELECT plan_version_id FROM plan_versions").fetchall()
        }
        onboarding_runs_exists = database.execute(
            """
            SELECT 1
            FROM sqlite_master
            WHERE type='table' AND name='data_onboarding_runs'
            """
        ).fetchone()
        reservations_exist = database.execute(
            """
            SELECT 1
            FROM sqlite_master
            WHERE type='table' AND name='data_onboarding_plan_reservations'
            """
        ).fetchone()
        if reservations_exist:
            reservation_rows = database.execute(
                """
                SELECT version_name, plan_version_id
                FROM data_onboarding_plan_reservations
                WHERE profile_key<>?
                  AND status='reserved'
                """,
                [profile_key],
            ).fetchall()
            existing_names.extend(
                row["version_name"]
                for row in reservation_rows
                if isinstance(row["version_name"], str) and row["version_name"]
            )
            existing_ids.update(
                row["plan_version_id"]
                for row in reservation_rows
                if isinstance(row["plan_version_id"], str) and row["plan_version_id"]
            )
        if onboarding_runs_exists:
            pending_rows = database.execute(
                """
                SELECT
                    json_extract(source_preview_json, '$.plan_version.version_name') AS version_name,
                    json_extract(source_preview_json, '$.plan_version.plan_version_id') AS plan_version_id
                FROM data_onboarding_runs
                WHERE profile_key<>?
                  AND status IN ('previewed','running','failed','partially_completed')
                """,
                [profile_key],
            ).fetchall()
            existing_names.extend(
                row["version_name"]
                for row in pending_rows
                if isinstance(row["version_name"], str) and row["version_name"]
            )
            existing_ids.update(
                row["plan_version_id"]
                for row in pending_rows
                if isinstance(row["plan_version_id"], str) and row["plan_version_id"]
            )
    return _resolved_plan_identity(final_name, existing_names, existing_ids)


def _resolved_plan_identity(
    requested_name: str,
    existing_names: list[str],
    existing_ids: set[str],
) -> dict[str, str]:
    final_name = requested_name
    if final_name in existing_names:
        max_version = 1
        for name in existing_names:
            if name == final_name:
                continue
            match = _VERSION_SUFFIX_RE.fullmatch(name)
            if match and match.group("base") == final_name:
                max_version = max(max_version, int(match.group("version")))
        final_name = f"{final_name}-v{max_version + 1}"

    base_id = f"plan-workbook-{slugify_text(final_name)}"
    candidate = base_id or "plan-workbook"
    suffix = 2
    while candidate in existing_ids:
        candidate = f"{base_id}-{suffix}"
        suffix += 1
    return {"plan_version_id": candidate, "version_name": final_name}


def release_plan_identity(
    *, run_id: str, db_path: str | Path | None = None
) -> None:
    with connection(db_path) as database:
        database.execute(
            """
            UPDATE data_onboarding_plan_reservations
            SET status='released'
            WHERE run_id=? AND status='reserved'
            """,
            [run_id],
        )


def next_profile_revision(
    *, profile_key: str = "default", db_path: str | Path | None = None
) -> int:
    if profile_key == "default":
        ensure_default_onboarding_profile(db_path=db_path)
    return onboarding_repository.next_profile_revision(
        profile_key=profile_key,
        db_path=db_path,
    )


def advance_profile_revision(
    *, profile_key: str = "default", db_path: str | Path | None = None
) -> int:
    if profile_key == "default":
        ensure_default_onboarding_profile(db_path=db_path)
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
        revision = int(profile["current_revision"]) + 1
        database.execute(
            """
            UPDATE onboarding_profiles
            SET current_revision=?
            WHERE profile_key=?
            """,
            [revision, profile_key],
        )
        database.commit()
    return revision


def restore_profile_revision(
    *,
    profile_key: str = "default",
    claimed_revision: int,
    db_path: str | Path | None = None,
) -> None:
    if profile_key == "default":
        ensure_default_onboarding_profile(db_path=db_path)
    onboarding_repository.restore_profile_revision(
        profile_key=profile_key,
        claimed_revision=claimed_revision,
        db_path=db_path,
    )
