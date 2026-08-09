"""Immutable public reader for the current canonical capacity fact."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from pm_agent.config import settings
from pm_agent.resource_intelligence.service import (
    COMMITMENT_KINDS,
    _fingerprint,
    validate_package,
)
from pm_agent.workforce_planning_import.read_model import project_allocation_snapshot


def source_capacity_export_snapshot(
    *, plan_version_id: str, capacity_context: dict[str, Any],
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    """Return Capacity facts from the authoritative Workbook source generation.

    Capacity publications, observations, freshness and derivations are runtime
    products.  The import session's package is the retained source contract and
    is sufficient to recreate those products after a workbook re-import.
    """
    row_count = capacity_context.get("row_count")
    package_id = capacity_context.get("package_id")
    if type(row_count) is not int or row_count < 0:
        raise ValueError("WORKBOOK_EXPORT_CAPACITY_SOURCE_INVALID")
    if row_count == 0:
        if package_id is not None:
            raise ValueError("WORKBOOK_EXPORT_CAPACITY_SOURCE_INVALID")
        return {"facts": [], "source": None}
    if not isinstance(package_id, str) or not package_id:
        raise ValueError("WORKBOOK_EXPORT_CAPACITY_SOURCE_MISSING")
    database = sqlite3.connect(Path(db_path or settings.database_path))
    database.row_factory = sqlite3.Row
    try:
        session = database.execute(
            """SELECT session_id,package_id,package_fingerprint,package_json
               FROM resource_capacity_import_sessions
               WHERE status='completed' AND package_id=?
               ORDER BY completed_at DESC,created_at DESC LIMIT 1""",
            [package_id],
        ).fetchone()
    finally:
        database.close()

    if session is None:
        raise ValueError("WORKBOOK_EXPORT_CAPACITY_SOURCE_MISSING")
    try:
        stored_package = json.loads(str(session["package_json"]))
        stored_observations = stored_package.get("observations")
        if not isinstance(stored_observations, list):
            raise ValueError
        package = validate_package({
            **stored_package,
            "observations": [
                {key: value for key, value in observation.items() if key != "fingerprint"}
                for observation in stored_observations
            ],
        })
    except (AttributeError, TypeError, ValueError, json.JSONDecodeError):
        raise ValueError("WORKBOOK_EXPORT_CAPACITY_SOURCE_INVALID") from None
    if (
        str(package.get("package_id") or "") != package_id
        or str(session["package_id"]) != package_id
        or str(package.get("plan_version_id") or "") != plan_version_id
        or _fingerprint(package) != str(session["package_fingerprint"])
    ):
        raise ValueError("WORKBOOK_EXPORT_CAPACITY_SOURCE_INVALID")
    try:
        observations = package["observations"]
        by_period: dict[tuple[str, int, int], dict[str, float]] = {}
        for observation in observations:
            identity = (
                str(observation["member_id"]), int(observation["year"]),
                int(observation["month"]),
            )
            kind = str(observation["commitment_kind"])
            if kind not in COMMITMENT_KINDS or observation.get("value_state") != "known":
                raise ValueError
            fraction = float(observation["fraction"])
            if not 0.0 <= fraction <= 1.0 or kind in by_period.setdefault(identity, {}):
                raise ValueError
            by_period[identity][kind] = fraction
        if any(set(values) != set(COMMITMENT_KINDS) for values in by_period.values()):
            raise ValueError
        if len(by_period) != row_count:
            raise ValueError
    except (KeyError, TypeError, ValueError):
        raise ValueError("WORKBOOK_EXPORT_CAPACITY_SOURCE_INVALID") from None
    facts = [
        {
            "member_id": member_id, "year": year, "month": month,
            "leave_fraction": values["leave"], "bau_fraction": values["bau"],
            "non_project_fraction": values["non_project"],
        }
        for (member_id, year, month), values in sorted(by_period.items())
    ]
    return {
        "facts": facts,
        "source": {
            "session_id": str(session["session_id"]),
            "package_id": str(session["package_id"]),
            "package_fingerprint": str(session["package_fingerprint"]),
        },
    }


def list_effective_capacity(
    year: int,
    month: int,
    plan_version_id: str,
    *,
    member_ids: list[str] | None = None,
    states: list[str] | None = None,
    db_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    """Return current persisted derivations without recalculating capacity."""
    database = sqlite3.connect(Path(db_path or settings.database_path))
    database.row_factory = sqlite3.Row
    try:
        clauses = [
            "p.is_current=1",
            "d.year=?",
            "d.month=?",
            "d.plan_version_id=?",
        ]
        parameters: list[Any] = [year, month, plan_version_id]
        if member_ids:
            clauses.append(f"d.member_id IN ({','.join('?' for _ in member_ids)})")
            parameters.extend(member_ids)
        if states:
            clauses.append(f"d.state IN ({','.join('?' for _ in states)})")
            parameters.extend(states)
        rows = database.execute(
            f"""SELECT d.*,p.package_id,p.package_fingerprint,p.published_at
                FROM resource_capacity_derivations d
                JOIN resource_capacity_publications p
                  ON p.publication_id=d.publication_id
                WHERE {' AND '.join(clauses)}
                ORDER BY d.member_id""",
            parameters,
        ).fetchall()
        results = []
        for row in rows:
            item = dict(row)
            item["evidence"] = json.loads(item.pop("evidence_json"))
            results.append(item)
        return results
    finally:
        database.close()


def get_effective_capacity(
    member_id: str, year: int, month: int, plan_version_id: str, *,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    """Return one member/month fact; absence is explicit unknown, never zero."""
    database = sqlite3.connect(Path(db_path or settings.database_path))
    database.row_factory = sqlite3.Row
    try:
        row = database.execute(
            """SELECT d.*,p.package_id,p.package_fingerprint,p.published_at
               FROM resource_capacity_derivations d
               JOIN resource_capacity_publications p ON p.publication_id=d.publication_id
               WHERE p.is_current=1 AND d.member_id=? AND d.year=? AND d.month=?
                 AND d.plan_version_id=?""",
            [member_id, year, month, plan_version_id],
        ).fetchone()
        if not row:
            return {
                "member_id": member_id, "year": year, "month": month,
                "plan_version_id": plan_version_id, "state": "unknown",
                "state_reason": "current_capacity_publication_or_period_not_found",
                "effective_capacity": None, "available_capacity": None,
                "overload_amount": None, "overload_state": None, "evidence": {},
            }
        result = dict(row)
        result["evidence"] = json.loads(result.pop("evidence_json"))
        return result
    finally:
        database.close()


def get_effective_capacity_in_transaction(
    database: sqlite3.Connection,
    member_id: str,
    year: int,
    month: int,
    plan_version_id: str,
) -> dict[str, Any] | None:
    """Load the current derivation using a caller-owned write transaction."""
    prior_factory = database.row_factory
    database.row_factory = sqlite3.Row
    try:
        row = database.execute(
            """SELECT d.*,p.package_id,p.package_fingerprint,p.published_at
               FROM resource_capacity_derivations d
               JOIN resource_capacity_publications p ON p.publication_id=d.publication_id
               WHERE p.is_current=1 AND d.member_id=? AND d.year=? AND d.month=?
                 AND d.plan_version_id=?""",
            [member_id, year, month, plan_version_id],
        ).fetchone()
        if not row:
            return None
        result = dict(row)
        result["evidence"] = json.loads(result.pop("evidence_json"))
        return result
    finally:
        database.row_factory = prior_factory


def get_project_capacity_coverage(
    project_id: str,
    year: int,
    month: int,
    plan_version_id: str,
    *,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    """Aggregate one authoritative project/month capacity-coverage fact."""
    allocation = project_allocation_snapshot(
        project_id, year, month, plan_version_id, db_path=db_path
    )
    base = {
        "fact_key": "capacity_coverage",
        "project_id": project_id,
        "year": year,
        "month": month,
        "plan_version_id": plan_version_id,
        "state": allocation["state"],
        "state_reason": allocation["state_reason"],
        "value": None,
        "evidence": {"allocation": allocation},
    }
    if allocation["state"] != "known":
        return base
    assignments = allocation["assignments"]
    if not assignments:
        return {
            **base,
            "state": "known",
            "state_reason": "authoritative_empty_assignment_set",
            "value": {
                "assignment_state": "empty",
                "assigned_member_count": 0,
                "overload_state": None,
            },
        }
    member_ids = [item["member_id"] for item in assignments]
    capacity_rows = list_effective_capacity(
        year,
        month,
        plan_version_id,
        member_ids=member_ids,
        db_path=db_path,
    )
    by_member = {row["member_id"]: row for row in capacity_rows}
    missing = sorted(set(member_ids) - set(by_member))
    if missing:
        return {
            **base,
            "state": "unknown",
            "state_reason": "assigned_member_capacity_missing",
            "evidence": {**base["evidence"], "missing_member_ids": missing},
        }
    if any(
        row["workforce_publication_id"] != allocation["publication_id"]
        for row in capacity_rows
    ):
        return {
            **base,
            "state": "unknown",
            "state_reason": "capacity_allocation_publication_mismatch",
            "evidence": {**base["evidence"], "capacity_derivations": capacity_rows},
        }
    states = {row["state"] for row in capacity_rows}
    state = (
        "conflicting" if "conflicting" in states
        else "unknown" if "unknown" in states
        else "stale" if "stale" in states
        else "known"
    )
    evidence = {**base["evidence"], "capacity_derivations": capacity_rows}
    if state != "known":
        return {
            **base,
            "state": state,
            "state_reason": f"assigned_member_capacity_{state}",
            "evidence": evidence,
        }
    overload_states = [row["overload_state"] for row in capacity_rows]
    if any(item not in {"clear", "amber", "red"} for item in overload_states):
        return {
            **base,
            "state": "unknown",
            "state_reason": "assigned_member_overload_state_invalid",
            "evidence": evidence,
        }
    overload_state = (
        "red" if "red" in overload_states
        else "amber" if "amber" in overload_states
        else "clear"
    )
    return {
        **base,
        "state": "known",
        "state_reason": "assigned_member_capacity_complete",
        "value": {
            "assignment_state": "assigned",
            "assigned_member_count": len(assignments),
            "overload_state": overload_state,
            "overloaded_member_count": sum(
                row["overload_state"] in {"amber", "red"} for row in capacity_rows
            ),
        },
        "evidence": evidence,
    }
