"""Versioned, previewable, atomic workforce/planning clean-import contract."""

from __future__ import annotations

import hashlib
import json
import re
from calendar import monthrange
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from pm_agent.workforce_planning_import import repository

PACKAGE_SCHEMA_VERSION = "workforce-planning-import-v1"
_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_TOP_LEVEL_FIELDS = {
    "dataset_marker",
    "package_id",
    "schema_version",
    "generated_at",
    "source_id",
    "manifest",
    "members",
    "projects",
    "plan_versions",
    "monthly_allocations",
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
    error_code: str = "WORKFORCE_PLANNING_STRING_INVALID",
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
    error_code: str = "WORKFORCE_PLANNING_STRING_INVALID",
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


def _iso_date(value: object) -> str:
    normalized = _bounded_string(value, limit=10)
    try:
        parsed = date.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError("WORKFORCE_PLANNING_DATE_INVALID") from exc
    if parsed.isoformat() != normalized:
        raise ValueError("WORKFORCE_PLANNING_DATE_INVALID")
    return normalized


def _optional_iso_date(value: object) -> str | None:
    if value is None:
        return None
    return _iso_date(value)


def _iso_timestamp(value: object) -> str:
    normalized = _bounded_string(value, limit=40)
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError("WORKFORCE_PLANNING_TIMESTAMP_INVALID") from exc
    if parsed.tzinfo is None:
        raise ValueError("WORKFORCE_PLANNING_TIMESTAMP_INVALID")
    return parsed.isoformat(timespec="seconds")


def _year_month(value: object, error_code: str) -> tuple[int, int]:
    if (
        not isinstance(value, dict)
        or not isinstance(value.get("year"), int)
        or isinstance(value.get("year"), bool)
        or not isinstance(value.get("month"), int)
        or isinstance(value.get("month"), bool)
    ):
        raise ValueError(error_code)
    year = value["year"]
    month = value["month"]
    if year < 2000 or year > 2100 or month < 1 or month > 12:
        raise ValueError(error_code)
    return year, month


def _unique(items: list[Any], key, error_code: str) -> None:
    keys = [key(item) for item in items]
    if len(keys) != len(set(keys)):
        raise ValueError(error_code)


def _normalize_member(value: object) -> dict[str, Any]:
    item = _allowed_fields(
        value,
        required={
            "member_id",
            "display_name",
            "role",
            "level",
            "status",
            "effective_start",
            "effective_end",
        },
        optional={"resource_type", "current_hiref_id", "hiref_end_date"},
        error_code="WORKFORCE_MEMBER_FIELDS_INVALID",
    )
    member_id = _identifier_string(item["member_id"], error_code="WORKFORCE_MEMBER_ID_INVALID")
    display_name = _bounded_string(
        item["display_name"],
        limit=120,
        error_code="WORKFORCE_MEMBER_NAME_INVALID",
    )
    status = _enum_string(
        item["status"], {"active", "inactive"}, "WORKFORCE_MEMBER_STATUS_INVALID"
    )
    effective_start = _iso_date(item["effective_start"])
    effective_end = _optional_iso_date(item["effective_end"])
    if effective_end and effective_end < effective_start:
        raise ValueError("WORKFORCE_MEMBER_EFFECTIVE_RANGE_INVALID")
    role = _bounded_string(
        item["role"],
        limit=120,
        error_code="WORKFORCE_MEMBER_ROLE_INVALID",
    )
    level = _bounded_string(
        item["level"],
        limit=40,
        error_code="WORKFORCE_MEMBER_LEVEL_INVALID",
    )
    resource_type = _enum_string(
        item.get("resource_type", ""),
        {"", "LTFTE", "STFTE"},
        "WORKFORCE_MEMBER_RESOURCE_TYPE_INVALID",
    )
    current_hiref_id = _optional_bounded_string(
        item.get("current_hiref_id"),
        limit=80,
        error_code="WORKFORCE_MEMBER_HIREF_ID_INVALID",
    )
    hiref_end_date = _optional_iso_date(item.get("hiref_end_date"))
    if resource_type == "STFTE" and (not current_hiref_id or not hiref_end_date):
        raise ValueError("WORKFORCE_MEMBER_STFTE_HIREF_REQUIRED")
    if bool(current_hiref_id) != bool(hiref_end_date):
        raise ValueError("WORKFORCE_MEMBER_HIREF_FIELDS_INCOMPLETE")
    return {
        "member_id": member_id,
        "display_name": display_name,
        "role": role,
        "level": level,
        "status": status,
        "effective_start": effective_start,
        "effective_end": effective_end,
        "resource_type": resource_type,
        "current_hiref_id": current_hiref_id,
        "hiref_end_date": hiref_end_date,
    }


def _normalize_project(value: object) -> dict[str, Any]:
    item = _exact_fields(
        value,
        {"project_id", "display_name", "status", "priority", "start_date", "target_end"},
        "WORKFORCE_PROJECT_FIELDS_INVALID",
    )
    project_id = _identifier_string(item["project_id"], error_code="WORKFORCE_PROJECT_ID_INVALID")
    display_name = _bounded_string(
        item["display_name"],
        limit=120,
        error_code="WORKFORCE_PROJECT_NAME_INVALID",
    )
    status = _enum_string(
        item["status"],
        {"planning", "active", "at_risk", "done"},
        "WORKFORCE_PROJECT_STATUS_INVALID",
    )
    if not isinstance(item["priority"], int) or isinstance(item["priority"], bool) or not 1 <= item[
        "priority"
    ] <= 5:
        raise ValueError("WORKFORCE_PROJECT_PRIORITY_INVALID")
    start_date = _optional_iso_date(item["start_date"])
    target_end = _optional_iso_date(item["target_end"])
    if start_date and target_end and target_end < start_date:
        raise ValueError("WORKFORCE_PROJECT_DATE_RANGE_INVALID")
    return {
        "project_id": project_id,
        "display_name": display_name,
        "status": status,
        "priority": item["priority"],
        "start_date": start_date,
        "target_end": target_end,
    }


def _normalize_plan(value: object) -> dict[str, Any]:
    item = _exact_fields(
        value,
        {"plan_version_id", "version_name", "scenario_type", "as_of_date", "status"},
        "WORKFORCE_PLAN_FIELDS_INVALID",
    )
    plan_id = _identifier_string(item["plan_version_id"], error_code="WORKFORCE_PLAN_ID_INVALID")
    version_name = _bounded_string(
        item["version_name"],
        limit=120,
        error_code="WORKFORCE_PLAN_VERSION_NAME_INVALID",
    )
    scenario_type = _enum_string(
        item["scenario_type"],
        {"baseline", "forecast", "approved", "what_if"},
        "WORKFORCE_PLAN_SCENARIO_INVALID",
    )
    status = _enum_string(
        item["status"], {"active", "draft", "archived"}, "WORKFORCE_PLAN_STATUS_INVALID"
    )
    return {
        "plan_version_id": plan_id,
        "version_name": version_name,
        "scenario_type": scenario_type,
        "as_of_date": _optional_iso_date(item["as_of_date"]),
        "status": status,
    }


def _normalize_workforce_period(value: object) -> dict[str, Any]:
    item = _exact_fields(
        value,
        {"member_id", "year", "month"},
        "WORKFORCE_PERIOD_FIELDS_INVALID",
    )
    year, month = _year_month(item, "WORKFORCE_PERIOD_INVALID")
    return {
        "member_id": _identifier_string(item["member_id"], error_code="WORKFORCE_PERIOD_MEMBER_INVALID"),
        "year": year,
        "month": month,
    }


def _normalize_allocation_identity(value: object, *, with_value: bool) -> dict[str, Any]:
    fields = {"member_id", "project_id", "plan_version_id", "year", "month"}
    if with_value:
        fields.add("allocation")
    item = _exact_fields(value, fields, "WORKFORCE_ALLOCATION_FIELDS_INVALID")
    year, month = _year_month(item, "WORKFORCE_ALLOCATION_MONTH_INVALID")
    result = {
        "member_id": _identifier_string(
            item["member_id"], error_code="WORKFORCE_ALLOCATION_MEMBER_INVALID"
        ),
        "project_id": _identifier_string(
            item["project_id"], error_code="WORKFORCE_ALLOCATION_PROJECT_INVALID"
        ),
        "plan_version_id": _identifier_string(
            item["plan_version_id"], error_code="WORKFORCE_ALLOCATION_PLAN_INVALID"
        ),
        "year": year,
        "month": month,
    }
    if with_value:
        allocation = item["allocation"]
        if (
            not isinstance(allocation, (int, float))
            or isinstance(allocation, bool)
            or not 0.0 <= float(allocation) <= 1.0
        ):
            raise ValueError("WORKFORCE_ALLOCATION_RANGE_INVALID")
        result["allocation"] = float(allocation)
    return result


def _allocation_key(item: dict[str, Any]) -> tuple[Any, ...]:
    return (
        item["member_id"],
        item["project_id"],
        item["plan_version_id"],
        item["year"],
        item["month"],
    )


def validate_package(payload: object) -> dict[str, Any]:
    package = _exact_fields(payload, _TOP_LEVEL_FIELDS, "WORKFORCE_PLANNING_PACKAGE_FIELDS_INVALID")
    if package["schema_version"] != PACKAGE_SCHEMA_VERSION:
        raise ValueError("WORKFORCE_PLANNING_PACKAGE_VERSION_INVALID")
    normalized: dict[str, Any] = {
        "dataset_marker": _bounded_string(
            package["dataset_marker"],
            error_code="WORKFORCE_PLANNING_DATASET_MARKER_INVALID",
        ),
        "package_id": _identifier_string(
            package["package_id"], error_code="WORKFORCE_PLANNING_PACKAGE_ID_INVALID"
        ),
        "schema_version": PACKAGE_SCHEMA_VERSION,
        "generated_at": _iso_timestamp(package["generated_at"]),
        "source_id": _identifier_string(
            package["source_id"], error_code="WORKFORCE_PLANNING_SOURCE_ID_INVALID"
        ),
    }
    for field in ("members", "projects", "plan_versions", "monthly_allocations"):
        if not isinstance(package[field], list):
            raise ValueError("WORKFORCE_PLANNING_PACKAGE_COLLECTION_INVALID")
    normalized["members"] = [_normalize_member(item) for item in package["members"]]
    normalized["projects"] = [_normalize_project(item) for item in package["projects"]]
    normalized["plan_versions"] = [_normalize_plan(item) for item in package["plan_versions"]]
    normalized["monthly_allocations"] = [
        _normalize_allocation_identity(item, with_value=True)
        for item in package["monthly_allocations"]
    ]
    if not normalized["members"] or not normalized["projects"] or not normalized["plan_versions"]:
        raise ValueError("WORKFORCE_PLANNING_PACKAGE_EMPTY_REQUIRED_SCOPE")
    _unique(normalized["members"], lambda item: item["member_id"], "WORKFORCE_MEMBER_DUPLICATE")
    _unique(normalized["projects"], lambda item: item["project_id"], "WORKFORCE_PROJECT_DUPLICATE")
    _unique(
        normalized["plan_versions"],
        lambda item: item["plan_version_id"],
        "WORKFORCE_PLAN_DUPLICATE",
    )
    _unique(normalized["monthly_allocations"], _allocation_key, "WORKFORCE_ALLOCATION_DUPLICATE")

    manifest = _exact_fields(
        package["manifest"],
        {"member_ids", "project_ids", "plan_version_ids", "workforce_periods", "allocation_keys"},
        "WORKFORCE_PLANNING_MANIFEST_FIELDS_INVALID",
    )
    for field in ("member_ids", "project_ids", "plan_version_ids", "workforce_periods", "allocation_keys"):
        if not isinstance(manifest[field], list):
            raise ValueError("WORKFORCE_PLANNING_MANIFEST_COLLECTION_INVALID")
    normalized_manifest = {
        "member_ids": [
            _identifier_string(item, error_code="WORKFORCE_MEMBER_ID_INVALID")
            for item in manifest["member_ids"]
        ],
        "project_ids": [
            _identifier_string(item, error_code="WORKFORCE_PROJECT_ID_INVALID")
            for item in manifest["project_ids"]
        ],
        "plan_version_ids": [
            _identifier_string(item, error_code="WORKFORCE_PLAN_ID_INVALID")
            for item in manifest["plan_version_ids"]
        ],
        "workforce_periods": [
            _normalize_workforce_period(item) for item in manifest["workforce_periods"]
        ],
        "allocation_keys": [
            _normalize_allocation_identity(item, with_value=False)
            for item in manifest["allocation_keys"]
        ],
    }
    for field in ("member_ids", "project_ids", "plan_version_ids"):
        if len(normalized_manifest[field]) != len(set(normalized_manifest[field])):
            raise ValueError("WORKFORCE_PLANNING_MANIFEST_DUPLICATE")
    _unique(
        normalized_manifest["workforce_periods"],
        lambda item: (item["member_id"], item["year"], item["month"]),
        "WORKFORCE_PERIOD_DUPLICATE",
    )
    _unique(
        normalized_manifest["allocation_keys"],
        _allocation_key,
        "WORKFORCE_ALLOCATION_MANIFEST_DUPLICATE",
    )

    member_ids = {item["member_id"] for item in normalized["members"]}
    project_ids = {item["project_id"] for item in normalized["projects"]}
    plan_ids = {item["plan_version_id"] for item in normalized["plan_versions"]}
    if member_ids != set(normalized_manifest["member_ids"]):
        raise ValueError("WORKFORCE_MEMBER_MANIFEST_INCOMPLETE")
    if project_ids != set(normalized_manifest["project_ids"]):
        raise ValueError("WORKFORCE_PROJECT_MANIFEST_INCOMPLETE")
    if plan_ids != set(normalized_manifest["plan_version_ids"]):
        raise ValueError("WORKFORCE_PLAN_MANIFEST_INCOMPLETE")
    if {_allocation_key(item) for item in normalized["monthly_allocations"]} != {
        _allocation_key(item) for item in normalized_manifest["allocation_keys"]
    }:
        raise ValueError("WORKFORCE_ALLOCATION_MANIFEST_INCOMPLETE")

    members = {item["member_id"]: item for item in normalized["members"]}
    for period in normalized_manifest["workforce_periods"]:
        member = members.get(period["member_id"])
        if not member:
            raise ValueError("WORKFORCE_PERIOD_MEMBER_NOT_FOUND")
        first_day = date(period["year"], period["month"], 1).isoformat()
        last_day = date(
            period["year"], period["month"], monthrange(period["year"], period["month"])[1]
        ).isoformat()
        if member["effective_start"] > first_day or (
            member["effective_end"] is not None and member["effective_end"] < last_day
        ):
            raise ValueError("WORKFORCE_PERIOD_OUTSIDE_EFFECTIVE_RANGE")
    covered_member_periods = {
        (item["member_id"], item["year"], item["month"])
        for item in normalized_manifest["workforce_periods"]
    }
    expected_allocation_keys = {
        (member_id, project_id, plan_id, year, month)
        for member_id, year, month in covered_member_periods
        for project_id in project_ids
        for plan_id in plan_ids
    }
    if {_allocation_key(item) for item in normalized_manifest["allocation_keys"]} != expected_allocation_keys:
        raise ValueError("WORKFORCE_ALLOCATION_COVERAGE_INCOMPLETE")
    for allocation in normalized["monthly_allocations"]:
        if allocation["member_id"] not in member_ids:
            raise ValueError("WORKFORCE_ALLOCATION_MEMBER_NOT_FOUND")
        if allocation["project_id"] not in project_ids:
            raise ValueError("WORKFORCE_ALLOCATION_PROJECT_NOT_FOUND")
        if allocation["plan_version_id"] not in plan_ids:
            raise ValueError("WORKFORCE_ALLOCATION_PLAN_NOT_FOUND")
        if (allocation["member_id"], allocation["year"], allocation["month"]) not in covered_member_periods:
            raise ValueError("WORKFORCE_ALLOCATION_PERIOD_NOT_COVERED")

    normalized["manifest"] = normalized_manifest
    normalized["members"].sort(key=lambda item: item["member_id"])
    normalized["projects"].sort(key=lambda item: item["project_id"])
    normalized["plan_versions"].sort(key=lambda item: item["plan_version_id"])
    normalized["monthly_allocations"].sort(key=_allocation_key)
    normalized_manifest["member_ids"].sort()
    normalized_manifest["project_ids"].sort()
    normalized_manifest["plan_version_ids"].sort()
    normalized_manifest["workforce_periods"].sort(
        key=lambda item: (item["member_id"], item["year"], item["month"])
    )
    normalized_manifest["allocation_keys"].sort(key=_allocation_key)
    return normalized


def _preview_counts(package: dict[str, Any]) -> dict[str, int]:
    return {
        "members": len(package["members"]),
        "projects": len(package["projects"]),
        "plan_versions": len(package["plan_versions"]),
        "monthly_allocations": len(package["monthly_allocations"]),
        "workforce_periods": len(package["manifest"]["workforce_periods"]),
        "allocation_keys": len(package["manifest"]["allocation_keys"]),
        "explicit_zero_allocations": sum(
            item["allocation"] == 0 for item in package["monthly_allocations"]
        ),
    }


def preview_import(payload: object, *, db_path: str | Path | None = None) -> dict[str, Any]:
    package = validate_package(payload)
    fingerprint = hashlib.sha256(_json(package).encode("utf-8")).hexdigest()
    existing = repository.session_by_fingerprint(fingerprint, db_path=db_path)
    if existing:
        if existing["status"] == "completed":
            return {
                "status": "already_completed",
                "session_id": existing["session_id"],
                "idempotent": True,
                "report": json.loads(existing["report_json"]),
            }
        if existing["status"] == "running":
            return {
                "status": "in_progress",
                "session_id": existing["session_id"],
                "idempotent": False,
            }
        return {
            "status": "retryable",
            "session_id": existing["session_id"],
            "idempotent": False,
            "counts": _preview_counts(package),
        }

    completed = repository.completed_session_for_package(package["package_id"], db_path=db_path)
    session_id = f"workforce-planning-session-{uuid4().hex}"
    now = _now()
    if completed:
        repository.create_session(
            session_id=session_id,
            package_id=package["package_id"],
            schema_version=package["schema_version"],
            package_fingerprint=fingerprint,
            package=package,
            status="rejected",
            created_at=now,
            failure_code="WORKFORCE_PLANNING_PACKAGE_REPLAY_CONFLICT",
            db_path=db_path,
        )
        repository.record_run(
            session_id=session_id,
            attempt_id=None,
            step_key="validate",
            status="rejected",
            counts=_preview_counts(package),
            warning_codes=["WORKFORCE_PLANNING_PACKAGE_REPLAY_CONFLICT"],
            created_at=now,
            db_path=db_path,
        )
        return {
            "status": "rejected",
            "session_id": session_id,
            "idempotent": False,
            "failure_code": "WORKFORCE_PLANNING_PACKAGE_REPLAY_CONFLICT",
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
    counts = _preview_counts(package)
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
        "coverage": {"authoritative_manifest": True, "missing_record_count": 0},
        "confirmation_required": True,
    }


def _failure_code(exc: Exception) -> str:
    if isinstance(exc, ValueError) and str(exc).startswith("WORKFORCE_PLANNING_"):
        return str(exc)
    if isinstance(exc, RuntimeError) and str(exc).startswith("WORKFORCE_PLANNING_"):
        return str(exc)
    return "WORKFORCE_PLANNING_PUBLICATION_FAILED"


def confirm_import(
    session_id: str,
    *,
    replace_current: bool = False,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    session = repository.load_session(session_id, db_path=db_path)
    if not session:
        raise ValueError("WORKFORCE_PLANNING_SESSION_NOT_FOUND")
    if session["status"] == "completed":
        return {
            "status": "completed",
            "session_id": session_id,
            "idempotent": True,
            "report": json.loads(session["report_json"]),
        }
    if session["status"] == "rejected":
        raise ValueError("WORKFORCE_PLANNING_SESSION_NOT_CONFIRMABLE")
    attempt_id = repository.start_attempt(session_id, started_at=_now(), db_path=db_path)
    try:
        report = repository.publish(
            session_id=session_id,
            attempt_id=attempt_id,
            package_fingerprint=session["package_fingerprint"],
            package=json.loads(session["package_json"]),
            published_at=_now(),
            replace_current=replace_current,
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
        "report": report,
    }
