"""Publish canonical dashboard demo artifacts from synthetic sample data.

This module belongs to the supported synthetic demo build path. It builds
canonical current-state staffing and contract-coverage packages from the
already-seeded demo tables, then publishes them through the owning capability
preview/confirm contracts.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from pm_agent.contract_coverage import service as contract_coverage_service
from pm_agent.current_state_staffing import service as current_state_staffing_service

DEMO_DATASET_MARKER = "SYNTHETIC_DATASET_V1"
DEMO_AS_OF_DATE = "2026-08-15"
DEMO_CURRENT_STATE_PACKAGE_ID = "package-synthetic-demo-current-state-r1"
DEMO_CURRENT_STATE_SCOPE_KEY = "synthetic-demo-current-state-staffing"
DEMO_CURRENT_STATE_SOURCE_ID = "source-synthetic-demo-current-state-staffing"
DEMO_CONTRACT_COVERAGE_PACKAGE_ID = "package-synthetic-demo-contract-coverage-r1"
DEMO_CONTRACT_COVERAGE_SCOPE_KEY = "synthetic-demo-contract-coverage"
DEMO_CONTRACT_COVERAGE_SOURCE_ID = "source-synthetic-demo-contract-coverage"


def _connect(db_path: str | Path) -> sqlite3.Connection:
    connection = sqlite3.connect(Path(db_path))
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _normalize_contract_fields(row: sqlite3.Row) -> tuple[str | None, str | None]:
    current_hiref_id = str(row["current_hiref"] or "") or None
    hiref_end_date = str(row["current_hiref_end_date"] or "") or None
    if not current_hiref_id or not hiref_end_date:
        return None, None
    return current_hiref_id, hiref_end_date


def _effective_period(connection: sqlite3.Connection, *, as_of_date: str) -> tuple[int, int]:
    periods = connection.execute(
        """
        SELECT DISTINCT year, month
        FROM monthly_allocations
        ORDER BY year, month
        """
    ).fetchall()
    if not periods:
        raise RuntimeError("SYNTHETIC_DEMO_CURRENT_STATE_PERIOD_NOT_FOUND")
    as_of_month = as_of_date[:7]
    for row in periods:
        year = int(row["year"])
        month = int(row["month"])
        if as_of_month == f"{year:04d}-{month:02d}":
            return year, month
    first = periods[0]
    return int(first["year"]), int(first["month"])


def build_current_state_staffing_package(
    db_path: str | Path,
    *,
    package_id: str = DEMO_CURRENT_STATE_PACKAGE_ID,
    dataset_marker: str = DEMO_DATASET_MARKER,
    source_id: str = DEMO_CURRENT_STATE_SOURCE_ID,
    scope_key: str = DEMO_CURRENT_STATE_SCOPE_KEY,
    as_of_date: str = DEMO_AS_OF_DATE,
    effective_year: int | None = None,
    effective_month: int | None = None,
) -> dict[str, Any]:
    with _connect(db_path) as connection:
        if effective_year is None or effective_month is None:
            effective_year, effective_month = _effective_period(
                connection,
                as_of_date=as_of_date,
            )
        members = []
        for row in connection.execute(
            """
            SELECT e.id,e.name,e.status,e.role,e.level,e.resource_type,e.current_hiref,
                   COALESCE(h.end_date, e.billing_end_date) AS current_hiref_end_date
            FROM employees e
            LEFT JOIN hiref h ON h.id = e.current_hiref
            WHERE e.status = 'active'
            ORDER BY e.id
            """
        ).fetchall():
            current_hiref_id, hiref_end_date = _normalize_contract_fields(row)
            members.append(
                {
                    "member_id": str(row["id"]),
                    "display_name": str(row["name"]),
                    "status": "active" if str(row["status"]) == "active" else "inactive",
                    "role": str(row["role"] or "unspecified"),
                    "level": str(row["level"] or "unknown"),
                    "resource_type": str(row["resource_type"] or ""),
                    "current_hiref_id": current_hiref_id,
                    "hiref_end_date": hiref_end_date,
                }
            )
        projects = [
            {
                "project_id": str(row["id"]),
                "display_name": str(row["name"]),
                "status": str(row["status"]),
                "priority": int(row["priority"] or 3),
            }
            for row in connection.execute(
                """
                SELECT id, name, status, priority
                FROM projects
                WHERE status IN ('planning', 'active', 'done')
                ORDER BY id
                """
            ).fetchall()
        ]
        assignments = [
            {
                "member_id": str(row["employee_id"]),
                "project_id": str(row["project_id"]),
                "allocation": float(row["allocation"]),
            }
            for row in connection.execute(
                """
                SELECT employee_id, project_id, allocation
                FROM assignments
                WHERE status = 'active'
                ORDER BY employee_id, project_id
                """
            ).fetchall()
        ]
    return {
        "dataset_marker": dataset_marker,
        "package_id": package_id,
        "schema_version": current_state_staffing_service.PACKAGE_SCHEMA_VERSION,
        "generated_at": f"{as_of_date}T00:00:00+00:00",
        "source_id": source_id,
        "publication_scope": {
            "scope_key": scope_key,
            "as_of_date": as_of_date,
            "effective_year": effective_year,
            "effective_month": effective_month,
        },
        "manifest": {
            "member_ids": [member["member_id"] for member in members],
            "project_ids": [project["project_id"] for project in projects],
            "assignment_keys": [
                {
                    "member_id": assignment["member_id"],
                    "project_id": assignment["project_id"],
                }
                for assignment in assignments
            ],
        },
        "members": members,
        "projects": projects,
        "assignments": assignments,
    }


def build_contract_coverage_package(
    db_path: str | Path,
    *,
    package_id: str = DEMO_CONTRACT_COVERAGE_PACKAGE_ID,
    dataset_marker: str = DEMO_DATASET_MARKER,
    source_id: str = DEMO_CONTRACT_COVERAGE_SOURCE_ID,
    scope_key: str = DEMO_CONTRACT_COVERAGE_SCOPE_KEY,
    as_of_date: str = DEMO_AS_OF_DATE,
) -> dict[str, Any]:
    with _connect(db_path) as connection:
        members = []
        for row in connection.execute(
            """
            SELECT e.id,e.name,e.status,e.resource_type,e.current_hiref,
                   COALESCE(h.end_date, e.billing_end_date) AS current_hiref_end_date
            FROM employees e
            LEFT JOIN hiref h ON h.id = e.current_hiref
            WHERE e.status = 'active'
            ORDER BY e.id
            """
        ).fetchall():
            current_hiref_id, hiref_end_date = _normalize_contract_fields(row)
            members.append(
                {
                    "member_id": str(row["id"]),
                    "display_name": str(row["name"]),
                    "status": "active" if str(row["status"]) == "active" else "inactive",
                    "resource_type": str(row["resource_type"] or ""),
                    "current_hiref_id": current_hiref_id,
                    "hiref_end_date": hiref_end_date,
                }
            )
    member_ids = [member["member_id"] for member in members]
    stfte_member_ids = sorted(
        member["member_id"] for member in members if member["resource_type"] == "STFTE"
    )
    ltfte_member_ids = sorted(
        member["member_id"] for member in members if member["resource_type"] == "LTFTE"
    )
    contract_member_ids = sorted(
        member["member_id"]
        for member in members
        if member["current_hiref_id"] and member["hiref_end_date"]
    )
    unknown_resource_type_member_ids = sorted(
        member["member_id"] for member in members if member["resource_type"] == ""
    )
    return {
        "dataset_marker": dataset_marker,
        "package_id": package_id,
        "schema_version": contract_coverage_service.PACKAGE_SCHEMA_VERSION,
        "generated_at": f"{as_of_date}T00:00:00+00:00",
        "source_id": source_id,
        "publication_scope": {
            "scope_key": scope_key,
            "as_of_date": as_of_date,
        },
        "manifest": {
            "member_ids": member_ids,
            "stfte_member_ids": stfte_member_ids,
            "ltfte_member_ids": ltfte_member_ids,
            "contract_member_ids": contract_member_ids,
            "unknown_resource_type_member_ids": unknown_resource_type_member_ids,
        },
        "members": members,
    }


def _confirm_previewed_import(
    *,
    label: str,
    preview: dict[str, Any],
    confirm_import,
    db_path: str | Path,
) -> dict[str, Any]:
    if preview["status"] == "in_progress":
        raise RuntimeError(f"{label} preview failed: {preview['status']}")
    if preview["status"] not in {"previewed", "already_completed", "retryable"}:
        raise RuntimeError(f"{label} preview failed: {preview['status']}")
    return confirm_import(preview["session_id"], db_path=db_path)


def publish_current_state_staffing_from_legacy_snapshot(
    db_path: str | Path,
    *,
    package_id: str = DEMO_CURRENT_STATE_PACKAGE_ID,
    dataset_marker: str = DEMO_DATASET_MARKER,
    source_id: str = DEMO_CURRENT_STATE_SOURCE_ID,
    scope_key: str = DEMO_CURRENT_STATE_SCOPE_KEY,
    as_of_date: str = DEMO_AS_OF_DATE,
    effective_year: int | None = None,
    effective_month: int | None = None,
) -> dict[str, Any]:
    package = build_current_state_staffing_package(
        db_path,
        package_id=package_id,
        dataset_marker=dataset_marker,
        source_id=source_id,
        scope_key=scope_key,
        as_of_date=as_of_date,
        effective_year=effective_year,
        effective_month=effective_month,
    )
    preview = current_state_staffing_service.preview_import(package, db_path=db_path)
    return _confirm_previewed_import(
        label="current-state staffing",
        preview=preview,
        confirm_import=current_state_staffing_service.confirm_import,
        db_path=db_path,
    )


def publish_contract_coverage_from_legacy_snapshot(
    db_path: str | Path,
    *,
    package_id: str = DEMO_CONTRACT_COVERAGE_PACKAGE_ID,
    dataset_marker: str = DEMO_DATASET_MARKER,
    source_id: str = DEMO_CONTRACT_COVERAGE_SOURCE_ID,
    scope_key: str = DEMO_CONTRACT_COVERAGE_SCOPE_KEY,
    as_of_date: str = DEMO_AS_OF_DATE,
) -> dict[str, Any]:
    package = build_contract_coverage_package(
        db_path,
        package_id=package_id,
        dataset_marker=dataset_marker,
        source_id=source_id,
        scope_key=scope_key,
        as_of_date=as_of_date,
    )
    preview = contract_coverage_service.preview_import(package, db_path=db_path)
    return _confirm_previewed_import(
        label="contract coverage",
        preview=preview,
        confirm_import=contract_coverage_service.confirm_import,
        db_path=db_path,
    )


def publish_demo_dashboard_publications(db_path: str | Path) -> dict[str, dict[str, Any]]:
    return {
        "current_state_staffing": publish_current_state_staffing_from_legacy_snapshot(
            db_path
        ),
        "contract_coverage": publish_contract_coverage_from_legacy_snapshot(db_path),
    }
