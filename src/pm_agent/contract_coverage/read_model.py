"""Public read-contract skeleton for canonical contract coverage."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pm_agent.config import settings
from pm_agent.contract_coverage.schema import CONTRACT_COVERAGE_REQUIRED_TABLES

CONTRACT_COVERAGE_PUBLICATION_SOURCE_ID = "contract-coverage-publication"
DEFAULT_PUBLICATION_REFRESH_SLA_HOURS = 720.0


def _connect(db_path: str | Path | None = None) -> sqlite3.Connection:
    database = sqlite3.connect(Path(db_path or settings.database_path))
    database.row_factory = sqlite3.Row
    database.execute("PRAGMA foreign_keys = ON")
    return database


def _use_database(
    *,
    db_path: str | Path | None = None,
    database: sqlite3.Connection | None = None,
) -> tuple[sqlite3.Connection, bool]:
    if database is not None:
        return database, False
    return _connect(db_path), True


def _schema_available(database: sqlite3.Connection) -> bool:
    rows = database.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table'
          AND name IN ({})
        """.format(",".join("?" for _ in CONTRACT_COVERAGE_REQUIRED_TABLES)),
        sorted(CONTRACT_COVERAGE_REQUIRED_TABLES),
    ).fetchall()
    return {str(row["name"]) for row in rows} == CONTRACT_COVERAGE_REQUIRED_TABLES


def _parse_json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    try:
        parsed = json.loads(str(value))
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _load_current_publication(database: sqlite3.Connection) -> dict[str, Any] | None:
    publication = database.execute(
        """
        SELECT publication_id,package_id,package_fingerprint,scope_key,
               as_of_date,published_at,report_json
        FROM contract_coverage_publications
        WHERE is_current=1
        ORDER BY published_at DESC
        LIMIT 1
        """
    ).fetchone()
    if publication is None:
        return None
    return {
        "publication_id": str(publication["publication_id"]),
        "package_id": str(publication["package_id"]),
        "package_fingerprint": str(publication["package_fingerprint"]),
        "scope_key": str(publication["scope_key"]),
        "as_of_date": str(publication["as_of_date"]),
        "published_at": str(publication["published_at"]),
        "report": _parse_json_object(publication["report_json"]),
    }


def _publication_refresh_sla_hours() -> float:
    return DEFAULT_PUBLICATION_REFRESH_SLA_HOURS


def _parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _coverage_state(report: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
    coverage = report.get("coverage")
    if not isinstance(coverage, dict):
        return (
            "partial",
            "contract_coverage_publication_coverage_missing",
            {},
        )
    state_values = [
        str(value)
        for key, value in coverage.items()
        if key.endswith("_state") and value is not None
    ]
    try:
        missing_record_count = int(coverage.get("missing_record_count") or 0)
    except (TypeError, ValueError):
        missing_record_count = 1
    if missing_record_count > 0 or any(value != "complete" for value in state_values):
        return (
            "partial",
            "contract_coverage_publication_coverage_incomplete",
            dict(coverage),
        )
    return (
        "complete",
        "contract_coverage_publication_coverage_complete",
        dict(coverage),
    )


def _freshness_warning(state: str) -> str:
    return {
        "fresh": "",
        "stale": "Contract-coverage publication is stale.",
        "partial": "Contract-coverage publication coverage is partial.",
        "unknown": "Contract-coverage publication is missing.",
        "unavailable": "Contract-coverage publication schema is unavailable.",
    }.get(state, "Contract-coverage publication freshness is unknown.")


def _member_contract_fact_state(row: sqlite3.Row) -> str:
    resource_type = str(row["resource_type"])
    has_contract = bool(str(row["current_hiref_id"])) and bool(str(row["hiref_end_date"]))
    if resource_type == "LTFTE":
        return "not_required"
    if resource_type == "STFTE":
        return "covered" if has_contract else "missing"
    return "covered" if has_contract else "unknown"


def current_publication_state(
    *,
    db_path: str | Path | None = None,
    database: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    database, should_close = _use_database(db_path=db_path, database=database)
    try:
        if not _schema_available(database):
            return {
                "state": "unavailable",
                "state_reason": "contract_coverage_schema_missing",
                "publication": None,
            }
        publication = _load_current_publication(database)
        if publication is None:
            return {
                "state": "unknown",
                "state_reason": "contract_coverage_publication_not_found",
                "publication": None,
            }
        return {
            "state": "known",
            "state_reason": "contract_coverage_current_publication_available",
            "publication": publication,
        }
    finally:
        if should_close:
            database.close()


def current_publication_freshness(
    *,
    db_path: str | Path | None = None,
    database: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    database, should_close = _use_database(db_path=db_path, database=database)
    try:
        publication_state = current_publication_state(database=database)
        base = {
            "source_id": CONTRACT_COVERAGE_PUBLICATION_SOURCE_ID,
            "state": publication_state["state"],
            "state_reason": publication_state["state_reason"],
            "observed_at": None,
            "last_success_at": None,
            "refresh_sla_hours": None,
            "publication_id": None,
            "package_id": None,
            "package_fingerprint": None,
            "scope_key": None,
            "as_of_date": None,
            "coverage_state": None,
            "coverage": None,
            "warning": _freshness_warning(publication_state["state"]),
        }
        publication = publication_state.get("publication")
        if not isinstance(publication, dict):
            return base
        refresh_sla_hours = _publication_refresh_sla_hours()
        coverage_state, coverage_reason, coverage = _coverage_state(
            publication.get("report", {})
        )
        published_at = publication.get("published_at")
        freshness_state = "fresh"
        freshness_reason = "contract_coverage_publication_fresh"
        if coverage_state != "complete":
            freshness_state = "partial"
            freshness_reason = coverage_reason
        else:
            observed_at = _parse_datetime(published_at)
            if observed_at is None:
                freshness_state = "partial"
                freshness_reason = "contract_coverage_publication_timestamp_invalid"
            else:
                age_hours = (datetime.now(timezone.utc) - observed_at).total_seconds() / 3600
                if age_hours > refresh_sla_hours:
                    freshness_state = "stale"
                    freshness_reason = "contract_coverage_publication_stale"
        return {
            **base,
            "state": freshness_state,
            "state_reason": freshness_reason,
            "observed_at": published_at,
            "last_success_at": published_at,
            "refresh_sla_hours": refresh_sla_hours,
            "publication_id": publication["publication_id"],
            "package_id": publication["package_id"],
            "package_fingerprint": publication["package_fingerprint"],
            "scope_key": publication["scope_key"],
            "as_of_date": publication["as_of_date"],
            "coverage_state": coverage_state,
            "coverage": coverage,
            "warning": _freshness_warning(freshness_state),
        }
    finally:
        if should_close:
            database.close()


def contract_coverage_snapshot(
    *,
    db_path: str | Path | None = None,
    database: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    publication_state = current_publication_state(db_path=db_path, database=database)
    publication_freshness = current_publication_freshness(
        db_path=db_path,
        database=database,
    )
    base = {
        "state": publication_state["state"],
        "state_reason": publication_state["state_reason"],
        "publication": publication_state["publication"],
        "freshness": publication_freshness,
        "freshness_state": publication_freshness["state"],
        "freshness_reason": publication_freshness["state_reason"],
        "coverage": publication_freshness["coverage"],
        "summary": None,
        "members": [],
    }
    if publication_state["state"] != "known":
        return base
    publication = publication_state["publication"]
    assert isinstance(publication, dict)
    database, should_close = _use_database(db_path=db_path, database=database)
    try:
        member_rows = database.execute(
            """
            SELECT member_id,display_name,employment_status,resource_type,
                   current_hiref_id,hiref_end_date
            FROM contract_coverage_members
            WHERE publication_id=?
            ORDER BY member_id
            """,
            [publication["publication_id"]],
        ).fetchall()
    finally:
        if should_close:
            database.close()
    members = [
        {
            "member_id": str(row["member_id"]),
            "display_name": str(row["display_name"]),
            "employment_status": str(row["employment_status"]),
            "resource_type": str(row["resource_type"]) or None,
            "current_hiref_id": str(row["current_hiref_id"]) or None,
            "hiref_end_date": str(row["hiref_end_date"]) or None,
            "contract_fact_state": _member_contract_fact_state(row),
        }
        for row in member_rows
    ]
    report = publication.get("report", {})
    summary = report.get("counts") if isinstance(report, dict) else None
    return {**base, "summary": summary, "members": members}


def member_contract_snapshot(
    member_id: str, *, db_path: str | Path | None = None
) -> dict[str, Any]:
    snapshot = contract_coverage_snapshot(db_path=db_path)
    base = {
        "member_id": member_id,
        "state": snapshot["state"],
        "state_reason": snapshot["state_reason"],
        "publication": snapshot["publication"],
        "freshness": snapshot["freshness"],
        "freshness_state": snapshot["freshness_state"],
        "freshness_reason": snapshot["freshness_reason"],
        "member": None,
    }
    if snapshot["state"] != "known":
        return base
    member = next(
        (item for item in snapshot["members"] if item["member_id"] == member_id),
        None,
    )
    if member is None:
        return {
            **base,
            "state": "unknown",
            "state_reason": "member_not_in_contract_coverage_publication",
        }
    return {
        **base,
        "state": "known",
        "state_reason": "member_contract_available_from_contract_coverage_publication",
        "member": dict(member),
    }
