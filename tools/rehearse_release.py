#!/usr/bin/env python3
"""Rehearse wheel install, isolated DB upgrade, and DB rollback."""

from __future__ import annotations

import hashlib
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

from validate_release import REPO_ROOT, build_package, package_version

SAMPLE_DB = REPO_ROOT / "src/sample-data/demo/sample_pm.db"
CORE_TABLES = (
    "employees",
    "projects",
    "assignments",
    "monthly_allocations",
    "decision_log",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def counts(path: Path) -> dict[str, int]:
    with sqlite3.connect(path) as connection:
        return {
            table: connection.execute(
                f"SELECT COUNT(*) FROM {table}"
            ).fetchone()[0]
            for table in CORE_TABLES
        }


def verify_upgraded_database(path: Path, expected_counts: dict[str, int]) -> None:
    with sqlite3.connect(path) as connection:
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        foreign_keys = connection.execute("PRAGMA foreign_key_check").fetchall()
        names = {
            row[0]
            for row in connection.execute(
                """
                SELECT name FROM sqlite_master
                WHERE name IN (
                    'v_member_load',
                    'v_project_team',
                    'staffing_proposals',
                    'dashboard_operations'
                )
                """
            )
        }
        connection.execute("SELECT COUNT(*) FROM v_member_load").fetchone()
        connection.execute("SELECT COUNT(*) FROM v_project_team").fetchone()
        token_columns = {
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(staffing_proposals)"
            )
            if row[1].startswith("confirmation_token")
        }

    if integrity != "ok":
        raise RuntimeError("DATABASE_INTEGRITY_FAILED")
    if foreign_keys:
        raise RuntimeError("DATABASE_FOREIGN_KEY_CHECK_FAILED")
    if names != {
        "v_member_load",
        "v_project_team",
        "staffing_proposals",
        "dashboard_operations",
    }:
        raise RuntimeError("DATABASE_OBJECT_SET_INVALID")
    if token_columns != {"confirmation_token_hash"}:
        raise RuntimeError("CONFIRMATION_TOKEN_SCHEMA_INVALID")
    if counts(path) != expected_counts:
        raise RuntimeError("DATABASE_CORE_COUNTS_CHANGED")


def rehearse() -> None:
    with tempfile.TemporaryDirectory(prefix="dm-release-rehearsal-") as temp_dir:
        workspace = Path(temp_dir)
        artifact_dir = workspace / "dist"
        artifact_dir.mkdir()
        wheel, _sdist = build_package(artifact_dir)

        install_dir = workspace / "installed"
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--no-deps",
                "--target",
                str(install_dir),
                str(wheel),
            ],
            check=True,
            cwd=workspace,
        )
        installed_env = os.environ.copy()
        installed_env["PYTHONPATH"] = str(install_dir)
        installed_version = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "from importlib.metadata import version;"
                    "print(version('ai-pm-agent'))"
                ),
            ],
            check=True,
            cwd=workspace,
            env=installed_env,
            capture_output=True,
            text=True,
        ).stdout.strip()
        if installed_version != package_version():
            raise RuntimeError("INSTALLED_VERSION_MISMATCH")

        backup_db = workspace / "before-upgrade.db"
        upgrade_db = workspace / "upgrade-copy.db"
        rollback_db = workspace / "rollback-copy.db"
        shutil.copy2(SAMPLE_DB, backup_db)
        shutil.copy2(backup_db, upgrade_db)
        original_hash = sha256(backup_db)
        before_counts = counts(backup_db)

        upgrade_env = installed_env.copy()
        upgrade_env["DATABASE_PATH"] = str(upgrade_db)
        subprocess.run(
            [
                sys.executable,
                "-c",
                "from pm_agent.database.bootstrap import main; main()",
            ],
            check=True,
            cwd=workspace,
            env=upgrade_env,
        )
        verify_upgraded_database(upgrade_db, before_counts)

        shutil.copy2(backup_db, rollback_db)
        if sha256(rollback_db) != original_hash:
            raise RuntimeError("DATABASE_ROLLBACK_HASH_MISMATCH")
        if sha256(SAMPLE_DB) != original_hash:
            raise RuntimeError("SOURCE_SAMPLE_DATABASE_CHANGED")

    print(
        "Release rehearsal PASSED: wheel install, isolated DB upgrade, "
        f"and rollback for ai-pm-agent {package_version()}"
    )


if __name__ == "__main__":
    try:
        rehearse()
    except (RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"Release rehearsal FAILED: {type(exc).__name__}", file=sys.stderr)
        raise SystemExit(1) from exc
