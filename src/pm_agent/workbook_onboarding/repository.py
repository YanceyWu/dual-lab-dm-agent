"""Persistence helpers for workbook onboarding profile and plan naming."""

from __future__ import annotations

import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from pm_agent.config import settings
from pm_agent.rules.identity import slugify_text

_DEFAULT_PROFILE = {
    "profile_id": "onboarding-profile-default",
    "profile_key": "default",
    "member_key_type": "workday_id",
    "project_key_type": "resource_portal_project_id",
    "baseline_source": "workbook",
    "adjustment_source": "copilot",
    "conflict_policy": "copilot_wins_workbook_blocked",
    "current_revision": 0,
    "status": "active",
}
_VERSION_SUFFIX_RE = re.compile(r"^(?P<base>.+)-v(?P<version>[2-9]\d*)$")


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


def ensure_default_onboarding_profile(
    *, db_path: str | Path | None = None
) -> dict[str, Any]:
    now = _utc_now()
    with connection(db_path) as database:
        database.execute("BEGIN IMMEDIATE")
        row = database.execute(
            "SELECT * FROM onboarding_profiles WHERE profile_key='default'"
        ).fetchone()
        if row is None:
            database.execute(
                """
                INSERT INTO onboarding_profiles
                    (profile_id,profile_key,member_key_type,project_key_type,baseline_source,
                     adjustment_source,conflict_policy,current_revision,status,created_at,updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
                """,
                [
                    _DEFAULT_PROFILE["profile_id"],
                    _DEFAULT_PROFILE["profile_key"],
                    _DEFAULT_PROFILE["member_key_type"],
                    _DEFAULT_PROFILE["project_key_type"],
                    _DEFAULT_PROFILE["baseline_source"],
                    _DEFAULT_PROFILE["adjustment_source"],
                    _DEFAULT_PROFILE["conflict_policy"],
                    _DEFAULT_PROFILE["current_revision"],
                    _DEFAULT_PROFILE["status"],
                    now,
                    now,
                ],
            )
            row = database.execute(
                "SELECT * FROM onboarding_profiles WHERE profile_key='default'"
            ).fetchone()
        database.commit()
    return dict(row)


def resolve_plan_identity(
    requested_name: str,
    *,
    db_path: str | Path | None = None,
) -> dict[str, str]:
    final_name = requested_name.strip()
    if not final_name:
        raise ValueError("WORKBOOK_ONBOARDING_PLAN_VERSION_NAME_REQUIRED")
    with connection(db_path) as database:
        existing_names = [
            row["version_name"]
            for row in database.execute("SELECT version_name FROM plan_versions").fetchall()
        ]
        existing_ids = {
            row["plan_version_id"]
            for row in database.execute("SELECT plan_version_id FROM plan_versions").fetchall()
        }
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


def next_profile_revision(*, db_path: str | Path | None = None) -> int:
    profile = ensure_default_onboarding_profile(db_path=db_path)
    return int(profile["current_revision"]) + 1


def advance_profile_revision(*, db_path: str | Path | None = None) -> int:
    now = _utc_now()
    with connection(db_path) as database:
        database.execute("BEGIN IMMEDIATE")
        profile = database.execute(
            "SELECT current_revision FROM onboarding_profiles WHERE profile_key='default'"
        ).fetchone()
        if profile is None:
            database.commit()
            ensure_default_onboarding_profile(db_path=db_path)
            return advance_profile_revision(db_path=db_path)
        revision = int(profile["current_revision"]) + 1
        database.execute(
            """
            UPDATE onboarding_profiles
            SET current_revision=?, updated_at=?
            WHERE profile_key='default'
            """,
            [revision, now],
        )
        database.commit()
    return revision
