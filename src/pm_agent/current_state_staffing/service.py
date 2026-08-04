"""Preview/confirm service for canonical current-state staffing publication."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from pm_agent.current_state_staffing import repository

PACKAGE_SCHEMA_VERSION = "current-state-staffing-v1"
_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_TOP_LEVEL_FIELDS = {
    "dataset_marker",
    "package_id",
    "schema_version",
    "generated_at",
    "source_id",
    "publication_scope",
    "manifest",
    "members",
    "projects",
    "assignments",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _exact_fields(value: object, fields: set[str], error_code: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError(error_code)
    return value


def _allowed_fields(
    value: object,
    *,
    required: set[str],
    optional: set[str],
    error_code: str,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(error_code)
    keys = set(value)
    if not required.issubset(keys) or not keys.issubset(required | optional):
        raise ValueError(error_code)
    return value


def _bounded_string(
    value: object,
    *,
    limit: int = 128,
    error_code: str = "CURRENT_STATE_STAFFING_STRING_INVALID",
) -> str:
    if not isinstance(value, str):
        raise ValueError(error_code)
    normalized = value.strip()
    if not normalized or len(normalized) > limit:
        raise ValueError(error_code)
    return normalized


def _optional_bounded_string(
    value: object,
    *,
    limit: int = 128,
    error_code: str = "CURRENT_STATE_STAFFING_STRING_INVALID",
) -> str | None:
    if value is None:
        return None
    return _bounded_string(value, limit=limit, error_code=error_code)


def _identifier_string(value: object, *, error_code: str) -> str:
    normalized = _bounded_string(value, error_code=error_code)
    if not _IDENTIFIER_RE.fullmatch(normalized):
        raise ValueError(error_code)
    return normalized


def _enum_string(value: object, allowed: set[str], error_code: str) -> str:
    if not isinstance(value, str) or value not in allowed:
        raise ValueError(error_code)
    return value


def _iso_timestamp(value: object) -> str:
    normalized = _bounded_string(value, limit=40)
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError("CURRENT_STATE_STAFFING_TIMESTAMP_INVALID") from exc
    if parsed.tzinfo is None:
        raise ValueError("CURRENT_STATE_STAFFING_TIMESTAMP_INVALID")
    return parsed.isoformat(timespec="seconds")


def _iso_date(value: object, *, error_code: str = "CURRENT_STATE_STAFFING_DATE_INVALID") -> str:
    normalized = _bounded_string(value, limit=10, error_code=error_code)
    try:
        parsed = date.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(error_code) from exc
    if parsed.isoformat() != normalized:
        raise ValueError(error_code)
    return normalized


def _year_month(value: object, *, error_code: str) -> tuple[int, int]:
    if (
        not isinstance(value, dict)
        or not isinstance(value.get("effective_year"), int)
        or isinstance(value.get("effective_year"), bool)
        or not isinstance(value.get("effective_month"), int)
        or isinstance(value.get("effective_month"), bool)
    ):
        raise ValueError(error_code)
    year = int(value["effective_year"])
    month = int(value["effective_month"])
    if year < 2000 or year > 2100 or month < 1 or month > 12:
        raise ValueError(error_code)
    return year, month


def _unique(items: list[Any], key, error_code: str) -> None:
    keys = [key(item) for item in items]
    if len(keys) != len(set(keys)):
        raise ValueError(error_code)


def _normalize_scope(value: object) -> dict[str, Any]:
    item = _exact_fields(
        value,
        {"scope_key", "as_of_date", "effective_year", "effective_month"},
        "CURRENT_STATE_STAFFING_SCOPE_FIELDS_INVALID",
    )
    year, month = _year_month(item, error_code="CURRENT_STATE_STAFFING_SCOPE_PERIOD_INVALID")
    return {
        "scope_key": _identifier_string(
            item["scope_key"], error_code="CURRENT_STATE_STAFFING_SCOPE_KEY_INVALID"
        ),
        "as_of_date": _iso_date(item["as_of_date"]),
        "effective_year": year,
        "effective_month": month,
    }


def _normalize_member(value: object) -> dict[str, Any]:
    item = _allowed_fields(
        value,
        required={"member_id", "display_name", "status", "role", "level"},
        optional={"resource_type", "current_hiref_id", "hiref_end_date"},
        error_code="CURRENT_STATE_STAFFING_MEMBER_FIELDS_INVALID",
    )
    member = {
        "member_id": _identifier_string(
            item["member_id"], error_code="CURRENT_STATE_STAFFING_MEMBER_ID_INVALID"
        ),
        "display_name": _bounded_string(
            item["display_name"],
            limit=120,
            error_code="CURRENT_STATE_STAFFING_MEMBER_NAME_INVALID",
        ),
        "status": _enum_string(
            item["status"],
            {"active", "inactive"},
            "CURRENT_STATE_STAFFING_MEMBER_STATUS_INVALID",
        ),
        "role": _bounded_string(
            item["role"],
            limit=120,
            error_code="CURRENT_STATE_STAFFING_MEMBER_ROLE_INVALID",
        ),
        "level": _bounded_string(
            item["level"],
            limit=40,
            error_code="CURRENT_STATE_STAFFING_MEMBER_LEVEL_INVALID",
        ),
        "resource_type": _enum_string(
            item.get("resource_type", ""),
            {"", "LTFTE", "STFTE"},
            "CURRENT_STATE_STAFFING_MEMBER_RESOURCE_TYPE_INVALID",
        ),
        "current_hiref_id": _optional_bounded_string(
            item.get("current_hiref_id"),
            limit=80,
            error_code="CURRENT_STATE_STAFFING_MEMBER_HIREF_ID_INVALID",
        ),
        "hiref_end_date": (
            _iso_date(
                item["hiref_end_date"],
                error_code="CURRENT_STATE_STAFFING_MEMBER_HIREF_END_DATE_INVALID",
            )
            if item.get("hiref_end_date") is not None
            else None
        ),
    }
    if bool(member["current_hiref_id"]) != bool(member["hiref_end_date"]):
        raise ValueError("CURRENT_STATE_STAFFING_MEMBER_HIREF_FIELDS_INCOMPLETE")
    return member


def _normalize_project(value: object) -> dict[str, Any]:
    item = _exact_fields(
        value,
        {"project_id", "display_name", "status", "priority"},
        "CURRENT_STATE_STAFFING_PROJECT_FIELDS_INVALID",
    )
    priority = item["priority"]
    if not isinstance(priority, int) or isinstance(priority, bool) or not 1 <= priority <= 5:
        raise ValueError("CURRENT_STATE_STAFFING_PROJECT_PRIORITY_INVALID")
    return {
        "project_id": _identifier_string(
            item["project_id"], error_code="CURRENT_STATE_STAFFING_PROJECT_ID_INVALID"
        ),
        "display_name": _bounded_string(
            item["display_name"],
            limit=120,
            error_code="CURRENT_STATE_STAFFING_PROJECT_NAME_INVALID",
        ),
        "status": _enum_string(
            item["status"],
            {"planning", "active", "done"},
            "CURRENT_STATE_STAFFING_PROJECT_STATUS_INVALID",
        ),
        "priority": priority,
    }


def _normalize_assignment(value: object) -> dict[str, Any]:
    item = _exact_fields(
        value,
        {"member_id", "project_id", "allocation"},
        "CURRENT_STATE_STAFFING_ASSIGNMENT_FIELDS_INVALID",
    )
    allocation = item["allocation"]
    if (
        not isinstance(allocation, (int, float))
        or isinstance(allocation, bool)
        or not 0.0 < float(allocation) <= 1.0
    ):
        raise ValueError("CURRENT_STATE_STAFFING_ASSIGNMENT_RANGE_INVALID")
    return {
        "member_id": _identifier_string(
            item["member_id"], error_code="CURRENT_STATE_STAFFING_ASSIGNMENT_MEMBER_INVALID"
        ),
        "project_id": _identifier_string(
            item["project_id"], error_code="CURRENT_STATE_STAFFING_ASSIGNMENT_PROJECT_INVALID"
        ),
        "allocation": float(allocation),
    }


def _assignment_key(item: dict[str, Any]) -> tuple[str, str]:
    return (item["member_id"], item["project_id"])


def validate_package(payload: object) -> dict[str, Any]:
    package = _exact_fields(
        payload,
        _TOP_LEVEL_FIELDS,
        "CURRENT_STATE_STAFFING_PACKAGE_FIELDS_INVALID",
    )
    if package["schema_version"] != PACKAGE_SCHEMA_VERSION:
        raise ValueError("CURRENT_STATE_STAFFING_PACKAGE_VERSION_INVALID")
    normalized: dict[str, Any] = {
        "dataset_marker": _bounded_string(
            package["dataset_marker"],
            error_code="CURRENT_STATE_STAFFING_DATASET_MARKER_INVALID",
        ),
        "package_id": _identifier_string(
            package["package_id"],
            error_code="CURRENT_STATE_STAFFING_PACKAGE_ID_INVALID",
        ),
        "schema_version": PACKAGE_SCHEMA_VERSION,
        "generated_at": _iso_timestamp(package["generated_at"]),
        "source_id": _identifier_string(
            package["source_id"],
            error_code="CURRENT_STATE_STAFFING_SOURCE_ID_INVALID",
        ),
        "publication_scope": _normalize_scope(package["publication_scope"]),
    }
    for field in ("members", "projects", "assignments"):
        if not isinstance(package[field], list):
            raise ValueError("CURRENT_STATE_STAFFING_PACKAGE_COLLECTION_INVALID")
    normalized["members"] = [_normalize_member(item) for item in package["members"]]
    normalized["projects"] = [_normalize_project(item) for item in package["projects"]]
    normalized["assignments"] = [_normalize_assignment(item) for item in package["assignments"]]
    if not normalized["members"] or not normalized["projects"]:
        raise ValueError("CURRENT_STATE_STAFFING_PACKAGE_EMPTY_REQUIRED_SCOPE")
    _unique(
        normalized["members"],
        lambda item: item["member_id"],
        "CURRENT_STATE_STAFFING_MEMBER_DUPLICATE",
    )
    _unique(
        normalized["projects"],
        lambda item: item["project_id"],
        "CURRENT_STATE_STAFFING_PROJECT_DUPLICATE",
    )
    _unique(
        normalized["assignments"],
        _assignment_key,
        "CURRENT_STATE_STAFFING_ASSIGNMENT_DUPLICATE",
    )

    manifest = _exact_fields(
        package["manifest"],
        {"member_ids", "project_ids", "assignment_keys"},
        "CURRENT_STATE_STAFFING_MANIFEST_FIELDS_INVALID",
    )
    for field in ("member_ids", "project_ids", "assignment_keys"):
        if not isinstance(manifest[field], list):
            raise ValueError("CURRENT_STATE_STAFFING_MANIFEST_COLLECTION_INVALID")
    normalized_manifest = {
        "member_ids": [
            _identifier_string(item, error_code="CURRENT_STATE_STAFFING_MEMBER_ID_INVALID")
            for item in manifest["member_ids"]
        ],
        "project_ids": [
            _identifier_string(item, error_code="CURRENT_STATE_STAFFING_PROJECT_ID_INVALID")
            for item in manifest["project_ids"]
        ],
        "assignment_keys": [
            _normalize_assignment_key(item) for item in manifest["assignment_keys"]
        ],
    }
    for field in ("member_ids", "project_ids"):
        if len(normalized_manifest[field]) != len(set(normalized_manifest[field])):
            raise ValueError("CURRENT_STATE_STAFFING_MANIFEST_DUPLICATE")
    _unique(
        normalized_manifest["assignment_keys"],
        _assignment_key,
        "CURRENT_STATE_STAFFING_ASSIGNMENT_MANIFEST_DUPLICATE",
    )

    member_ids = {item["member_id"] for item in normalized["members"]}
    project_ids = {item["project_id"] for item in normalized["projects"]}
    assignment_keys = {_assignment_key(item) for item in normalized["assignments"]}
    if member_ids != set(normalized_manifest["member_ids"]):
        raise ValueError("CURRENT_STATE_STAFFING_MEMBER_MANIFEST_INCOMPLETE")
    if project_ids != set(normalized_manifest["project_ids"]):
        raise ValueError("CURRENT_STATE_STAFFING_PROJECT_MANIFEST_INCOMPLETE")
    if assignment_keys != {_assignment_key(item) for item in normalized_manifest["assignment_keys"]}:
        raise ValueError("CURRENT_STATE_STAFFING_ASSIGNMENT_MANIFEST_INCOMPLETE")
    for assignment in normalized["assignments"]:
        if assignment["member_id"] not in member_ids:
            raise ValueError("CURRENT_STATE_STAFFING_ASSIGNMENT_MEMBER_NOT_FOUND")
        if assignment["project_id"] not in project_ids:
            raise ValueError("CURRENT_STATE_STAFFING_ASSIGNMENT_PROJECT_NOT_FOUND")

    normalized["members"].sort(key=lambda item: item["member_id"])
    normalized["projects"].sort(key=lambda item: item["project_id"])
    normalized["assignments"].sort(key=_assignment_key)
    normalized_manifest["member_ids"].sort()
    normalized_manifest["project_ids"].sort()
    normalized_manifest["assignment_keys"].sort(key=_assignment_key)
    normalized["manifest"] = normalized_manifest
    return normalized


def _normalize_assignment_key(value: object) -> dict[str, Any]:
    item = _exact_fields(
        value,
        {"member_id", "project_id"},
        "CURRENT_STATE_STAFFING_ASSIGNMENT_KEY_FIELDS_INVALID",
    )
    return {
        "member_id": _identifier_string(
            item["member_id"],
            error_code="CURRENT_STATE_STAFFING_ASSIGNMENT_MEMBER_INVALID",
        ),
        "project_id": _identifier_string(
            item["project_id"],
            error_code="CURRENT_STATE_STAFFING_ASSIGNMENT_PROJECT_INVALID",
        ),
    }


def _preview_counts(package: dict[str, Any]) -> dict[str, int]:
    assigned_members = {assignment["member_id"] for assignment in package["assignments"]}
    active_members = sum(member["status"] == "active" for member in package["members"])
    return {
        "members": len(package["members"]),
        "active_members": active_members,
        "inactive_members": len(package["members"]) - active_members,
        "projects": len(package["projects"]),
        "assignments": len(package["assignments"]),
        "assigned_members": len(assigned_members),
        "unassigned_members": len(package["members"]) - len(assigned_members),
    }


def preview_import(payload: object, *, db_path: str | Path | None = None) -> dict[str, Any]:
    package = validate_package(payload)
    fingerprint = hashlib.sha256(_json(package).encode("utf-8")).hexdigest()
    counts = _preview_counts(package)
    existing = repository.session_by_fingerprint(fingerprint, db_path=db_path)
    if existing:
        if existing["status"] == "completed":
            return {
                "status": "already_completed",
                "session_id": existing["session_id"],
                "idempotent": True,
                "report": json.loads(existing["report_json"]),
            }
        return {
            "status": "in_progress" if existing["status"] == "running" else "retryable",
            "session_id": existing["session_id"],
            "idempotent": False,
            "counts": counts,
            "publication_scope": package["publication_scope"],
        }

    package_conflict = repository.latest_session_for_package(package["package_id"], db_path=db_path)
    session_id = f"current-state-staffing-session-{uuid4().hex}"
    now = _now()
    if package_conflict and package_conflict["package_fingerprint"] != fingerprint:
        repository.create_session(
            session_id=session_id,
            package_id=package["package_id"],
            schema_version=package["schema_version"],
            package_fingerprint=fingerprint,
            package=package,
            status="rejected",
            created_at=now,
            failure_code="CURRENT_STATE_STAFFING_PACKAGE_REPLAY_CONFLICT",
            db_path=db_path,
        )
        repository.record_run(
            session_id=session_id,
            attempt_id=None,
            step_key="validate",
            status="rejected",
            counts=counts,
            warning_codes=["CURRENT_STATE_STAFFING_PACKAGE_REPLAY_CONFLICT"],
            created_at=now,
            db_path=db_path,
        )
        return {
            "status": "rejected",
            "session_id": session_id,
            "idempotent": False,
            "failure_code": "CURRENT_STATE_STAFFING_PACKAGE_REPLAY_CONFLICT",
            "publication_scope": package["publication_scope"],
        }

    repository.create_session(
        session_id=session_id,
        package_id=package["package_id"],
        schema_version=package["schema_version"],
        package_fingerprint=fingerprint,
        package=package,
        status="previewed",
        created_at=now,
        db_path=db_path,
    )
    repository.record_run(
        session_id=session_id,
        attempt_id=None,
        step_key="validate",
        status="completed",
        counts=counts,
        warning_codes=[],
        created_at=now,
        db_path=db_path,
    )
    return {
        "status": "previewed",
        "session_id": session_id,
        "idempotent": False,
        "package_fingerprint": fingerprint,
        "counts": counts,
        "publication_scope": package["publication_scope"],
        "coverage": {
            "member_roster_state": "complete",
            "assignment_manifest_state": "complete",
        },
        "confirmation_required": True,
    }


def _publication_report(
    package: dict[str, Any],
    *,
    publication_id: str,
    package_fingerprint: str,
    published_at: str,
) -> dict[str, Any]:
    return {
        "publication_id": publication_id,
        "package_id": package["package_id"],
        "package_fingerprint": package_fingerprint,
        "scope_key": package["publication_scope"]["scope_key"],
        "as_of_date": package["publication_scope"]["as_of_date"],
        "effective_year": package["publication_scope"]["effective_year"],
        "effective_month": package["publication_scope"]["effective_month"],
        "published_at": published_at,
        "coverage": {
            "member_roster_state": "complete",
            "assignment_manifest_state": "complete",
            "missing_record_count": 0,
        },
        "counts": _preview_counts(package),
    }


def _failure_code(exc: Exception) -> str:
    if isinstance(exc, ValueError) and str(exc).startswith("CURRENT_STATE_STAFFING_"):
        return str(exc)
    if isinstance(exc, RuntimeError) and str(exc).startswith("CURRENT_STATE_STAFFING_"):
        return str(exc)
    return "CURRENT_STATE_STAFFING_PUBLICATION_FAILED"


def confirm_import(
    session_id: str,
    *,
    replace_current: bool = True,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    session = repository.load_session(session_id, db_path=db_path)
    if not session:
        raise ValueError("CURRENT_STATE_STAFFING_SESSION_NOT_FOUND")
    if session["status"] == "completed":
        return {
            "status": "completed",
            "session_id": session_id,
            "idempotent": True,
            "report": json.loads(session["report_json"]),
        }
    if session["status"] == "rejected":
        raise ValueError("CURRENT_STATE_STAFFING_SESSION_NOT_CONFIRMABLE")
    attempt_id = repository.start_attempt(session_id, started_at=_now(), db_path=db_path)
    package = json.loads(session["package_json"])
    counts = _preview_counts(package)
    published_at = _now()
    publication_id = f"current-state-staffing-publication-{uuid4().hex}"
    report = _publication_report(
        package,
        publication_id=publication_id,
        package_fingerprint=str(session["package_fingerprint"]),
        published_at=published_at,
    )
    try:
        final_report = repository.publish(
            session_id=session_id,
            attempt_id=attempt_id,
            package_fingerprint=str(session["package_fingerprint"]),
            package=package,
            published_at=published_at,
            replace_current=replace_current,
            report=report,
            counts=counts,
            db_path=db_path,
        )
    except Exception as exc:
        repository.fail_attempt(
            session_id=session_id,
            attempt_id=attempt_id,
            failure_code=_failure_code(exc),
            finished_at=_now(),
            db_path=db_path,
        )
        raise
    return {
        "status": "completed",
        "session_id": session_id,
        "idempotent": False,
        "report": final_report,
    }
