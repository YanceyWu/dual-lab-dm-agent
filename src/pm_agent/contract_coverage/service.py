"""Preview/confirm service for canonical contract-coverage publication."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from pm_agent.contract_coverage import repository

PACKAGE_SCHEMA_VERSION = "contract-coverage-v1"
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
    error_code: str = "CONTRACT_COVERAGE_STRING_INVALID",
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
    error_code: str = "CONTRACT_COVERAGE_STRING_INVALID",
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
        raise ValueError("CONTRACT_COVERAGE_TIMESTAMP_INVALID") from exc
    if parsed.tzinfo is None:
        raise ValueError("CONTRACT_COVERAGE_TIMESTAMP_INVALID")
    return parsed.isoformat(timespec="seconds")


def _iso_date(value: object, *, error_code: str = "CONTRACT_COVERAGE_DATE_INVALID") -> str:
    normalized = _bounded_string(value, limit=10, error_code=error_code)
    try:
        parsed = date.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(error_code) from exc
    if parsed.isoformat() != normalized:
        raise ValueError(error_code)
    return normalized


def _unique(items: list[Any], key, error_code: str) -> None:
    keys = [key(item) for item in items]
    if len(keys) != len(set(keys)):
        raise ValueError(error_code)


def _normalize_scope(value: object) -> dict[str, Any]:
    item = _exact_fields(
        value,
        {"scope_key", "as_of_date"},
        "CONTRACT_COVERAGE_SCOPE_FIELDS_INVALID",
    )
    return {
        "scope_key": _identifier_string(
            item["scope_key"], error_code="CONTRACT_COVERAGE_SCOPE_KEY_INVALID"
        ),
        "as_of_date": _iso_date(item["as_of_date"]),
    }


def _normalize_member(value: object) -> dict[str, Any]:
    item = _allowed_fields(
        value,
        required={"member_id", "display_name", "status", "resource_type"},
        optional={"current_hiref_id", "hiref_end_date"},
        error_code="CONTRACT_COVERAGE_MEMBER_FIELDS_INVALID",
    )
    member = {
        "member_id": _identifier_string(
            item["member_id"], error_code="CONTRACT_COVERAGE_MEMBER_ID_INVALID"
        ),
        "display_name": _bounded_string(
            item["display_name"],
            limit=120,
            error_code="CONTRACT_COVERAGE_MEMBER_NAME_INVALID",
        ),
        "status": _enum_string(
            item["status"],
            {"active", "inactive"},
            "CONTRACT_COVERAGE_MEMBER_STATUS_INVALID",
        ),
        "resource_type": _enum_string(
            item["resource_type"],
            {"", "LTFTE", "STFTE"},
            "CONTRACT_COVERAGE_MEMBER_RESOURCE_TYPE_INVALID",
        ),
        "current_hiref_id": _optional_bounded_string(
            item.get("current_hiref_id"),
            limit=80,
            error_code="CONTRACT_COVERAGE_MEMBER_HIREF_ID_INVALID",
        ),
        "hiref_end_date": (
            _iso_date(
                item["hiref_end_date"],
                error_code="CONTRACT_COVERAGE_MEMBER_HIREF_END_DATE_INVALID",
            )
            if item.get("hiref_end_date") is not None
            else None
        ),
    }
    if bool(member["current_hiref_id"]) != bool(member["hiref_end_date"]):
        raise ValueError("CONTRACT_COVERAGE_MEMBER_HIREF_FIELDS_INCOMPLETE")
    return member


def validate_package(payload: object) -> dict[str, Any]:
    package = _exact_fields(
        payload,
        _TOP_LEVEL_FIELDS,
        "CONTRACT_COVERAGE_PACKAGE_FIELDS_INVALID",
    )
    if package["schema_version"] != PACKAGE_SCHEMA_VERSION:
        raise ValueError("CONTRACT_COVERAGE_PACKAGE_VERSION_INVALID")
    normalized: dict[str, Any] = {
        "dataset_marker": _bounded_string(
            package["dataset_marker"],
            error_code="CONTRACT_COVERAGE_DATASET_MARKER_INVALID",
        ),
        "package_id": _identifier_string(
            package["package_id"],
            error_code="CONTRACT_COVERAGE_PACKAGE_ID_INVALID",
        ),
        "schema_version": PACKAGE_SCHEMA_VERSION,
        "generated_at": _iso_timestamp(package["generated_at"]),
        "source_id": _identifier_string(
            package["source_id"],
            error_code="CONTRACT_COVERAGE_SOURCE_ID_INVALID",
        ),
        "publication_scope": _normalize_scope(package["publication_scope"]),
    }
    if not isinstance(package["members"], list):
        raise ValueError("CONTRACT_COVERAGE_MEMBER_COLLECTION_INVALID")
    normalized["members"] = [_normalize_member(item) for item in package["members"]]
    if not normalized["members"]:
        raise ValueError("CONTRACT_COVERAGE_PACKAGE_EMPTY_REQUIRED_SCOPE")
    _unique(
        normalized["members"],
        lambda item: item["member_id"],
        "CONTRACT_COVERAGE_MEMBER_DUPLICATE",
    )

    manifest = _exact_fields(
        package["manifest"],
        {
            "member_ids",
            "stfte_member_ids",
            "ltfte_member_ids",
            "contract_member_ids",
            "unknown_resource_type_member_ids",
        },
        "CONTRACT_COVERAGE_MANIFEST_FIELDS_INVALID",
    )
    for field in manifest:
        if not isinstance(manifest[field], list):
            raise ValueError("CONTRACT_COVERAGE_MANIFEST_COLLECTION_INVALID")
    normalized_manifest = {
        field: [
            _identifier_string(
                item,
                error_code="CONTRACT_COVERAGE_MEMBER_ID_INVALID",
            )
            for item in manifest[field]
        ]
        for field in manifest
    }
    for field, error_code in (
        ("member_ids", "CONTRACT_COVERAGE_MEMBER_MANIFEST_DUPLICATE"),
        ("stfte_member_ids", "CONTRACT_COVERAGE_STFTE_MANIFEST_DUPLICATE"),
        ("ltfte_member_ids", "CONTRACT_COVERAGE_LTFTE_MANIFEST_DUPLICATE"),
        ("contract_member_ids", "CONTRACT_COVERAGE_CONTRACT_MANIFEST_DUPLICATE"),
        (
            "unknown_resource_type_member_ids",
            "CONTRACT_COVERAGE_UNKNOWN_TYPE_MANIFEST_DUPLICATE",
        ),
    ):
        if len(normalized_manifest[field]) != len(set(normalized_manifest[field])):
            raise ValueError(error_code)

    member_ids = {item["member_id"] for item in normalized["members"]}
    stfte_member_ids = {
        item["member_id"] for item in normalized["members"] if item["resource_type"] == "STFTE"
    }
    ltfte_member_ids = {
        item["member_id"] for item in normalized["members"] if item["resource_type"] == "LTFTE"
    }
    contract_member_ids = {
        item["member_id"]
        for item in normalized["members"]
        if item["current_hiref_id"] and item["hiref_end_date"]
    }
    unknown_resource_type_member_ids = {
        item["member_id"] for item in normalized["members"] if item["resource_type"] == ""
    }
    if member_ids != set(normalized_manifest["member_ids"]):
        raise ValueError("CONTRACT_COVERAGE_MEMBER_MANIFEST_INCOMPLETE")
    if stfte_member_ids != set(normalized_manifest["stfte_member_ids"]):
        raise ValueError("CONTRACT_COVERAGE_STFTE_MANIFEST_INCOMPLETE")
    if ltfte_member_ids != set(normalized_manifest["ltfte_member_ids"]):
        raise ValueError("CONTRACT_COVERAGE_LTFTE_MANIFEST_INCOMPLETE")
    if contract_member_ids != set(normalized_manifest["contract_member_ids"]):
        raise ValueError("CONTRACT_COVERAGE_CONTRACT_MANIFEST_INCOMPLETE")
    if unknown_resource_type_member_ids != set(
        normalized_manifest["unknown_resource_type_member_ids"]
    ):
        raise ValueError("CONTRACT_COVERAGE_UNKNOWN_TYPE_MANIFEST_INCOMPLETE")

    normalized["members"].sort(key=lambda item: item["member_id"])
    for field in normalized_manifest:
        normalized_manifest[field].sort()
    normalized["manifest"] = normalized_manifest
    return normalized


def _preview_counts(package: dict[str, Any]) -> dict[str, int]:
    members = package["members"]
    stfte_members = [item for item in members if item["resource_type"] == "STFTE"]
    contract_members = [
        item for item in members if item["current_hiref_id"] and item["hiref_end_date"]
    ]
    unknown_resource_type_members = [
        item for item in members if item["resource_type"] == ""
    ]
    return {
        "members": len(members),
        "active_members": sum(item["status"] == "active" for item in members),
        "inactive_members": sum(item["status"] == "inactive" for item in members),
        "stfte_members": len(stfte_members),
        "ltfte_members": sum(item["resource_type"] == "LTFTE" for item in members),
        "contract_members": len(contract_members),
        "uncovered_stfte_members": sum(
            not (item["current_hiref_id"] and item["hiref_end_date"]) for item in stfte_members
        ),
        "unknown_resource_type_members": len(unknown_resource_type_members),
    }


def _coverage(counts: dict[str, int]) -> dict[str, Any]:
    contract_state = (
        "complete" if counts["uncovered_stfte_members"] == 0 else "partial"
    )
    resource_type_state = (
        "complete" if counts["unknown_resource_type_members"] == 0 else "partial"
    )
    return {
        "member_roster_state": "complete",
        "member_contract_state": contract_state,
        "member_resource_type_state": resource_type_state,
        "missing_record_count": counts["uncovered_stfte_members"]
        + counts["unknown_resource_type_members"],
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
    session_id = f"contract-coverage-session-{uuid4().hex}"
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
            failure_code="CONTRACT_COVERAGE_PACKAGE_REPLAY_CONFLICT",
            db_path=db_path,
        )
        repository.record_run(
            session_id=session_id,
            attempt_id=None,
            step_key="validate",
            status="rejected",
            counts=counts,
            warning_codes=["CONTRACT_COVERAGE_PACKAGE_REPLAY_CONFLICT"],
            created_at=now,
            db_path=db_path,
        )
        return {
            "status": "rejected",
            "session_id": session_id,
            "idempotent": False,
            "failure_code": "CONTRACT_COVERAGE_PACKAGE_REPLAY_CONFLICT",
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
        "coverage": _coverage(counts),
        "confirmation_required": True,
    }


def _publication_report(
    package: dict[str, Any],
    *,
    package_fingerprint: str,
    published_at: str,
) -> dict[str, Any]:
    counts = _preview_counts(package)
    return {
        "package_id": package["package_id"],
        "package_fingerprint": package_fingerprint,
        "scope_key": package["publication_scope"]["scope_key"],
        "as_of_date": package["publication_scope"]["as_of_date"],
        "published_at": published_at,
        "coverage": _coverage(counts),
        "counts": counts,
    }


def _failure_code(exc: Exception) -> str:
    if isinstance(exc, ValueError) and str(exc).startswith("CONTRACT_COVERAGE_"):
        return str(exc)
    if isinstance(exc, RuntimeError) and str(exc).startswith("CONTRACT_COVERAGE_"):
        return str(exc)
    return "CONTRACT_COVERAGE_PUBLICATION_FAILED"


def confirm_import(
    session_id: str,
    *,
    replace_current: bool = True,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    session = repository.load_session(session_id, db_path=db_path)
    if not session:
        raise ValueError("CONTRACT_COVERAGE_SESSION_NOT_FOUND")
    if session["status"] == "completed":
        return {
            "status": "completed",
            "session_id": session_id,
            "idempotent": True,
            "report": json.loads(session["report_json"]),
        }
    if session["status"] == "rejected":
        raise ValueError("CONTRACT_COVERAGE_SESSION_NOT_CONFIRMABLE")
    attempt_id = repository.start_attempt(session_id, started_at=_now(), db_path=db_path)
    package = json.loads(session["package_json"])
    counts = _preview_counts(package)
    published_at = _now()
    report = _publication_report(
        package,
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
