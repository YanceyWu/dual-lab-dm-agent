"""Versioned preview/confirm contract for canonical effective capacity."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from pm_agent.resource_intelligence import repository
from pm_agent.workforce_planning_import.read_model import dependency_snapshot

PACKAGE_SCHEMA_VERSION = "resource-capacity-import-v1"
DATASET_MARKER = "SYNTHETIC_DATASET_V1"
COMMITMENT_KINDS = ("leave", "bau", "non_project")
SOURCE_AUTHORITY = {
    "leave": "source-synthetic-leave",
    "bau": "source-synthetic-bau",
    "non_project": "source-synthetic-non-project",
}
_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{2,127}$")
_TOP_FIELDS = {
    "dataset_marker", "package_id", "schema_version", "generated_at", "source_id",
    "idempotency_key", "plan_version_id", "assessment_time", "manifest", "observations",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _exact(value: object, fields: set[str], code: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError(code)
    return value


def _string(value: object, *, prefix: str | None = None, limit: int = 128) -> str:
    if not isinstance(value, str):
        raise ValueError("RESOURCE_CAPACITY_STRING_INVALID")
    value = value.strip()
    if not value or len(value) > limit or (prefix and (not _ID_RE.fullmatch(value) or not value.startswith(prefix))):
        raise ValueError("RESOURCE_CAPACITY_SYNTHETIC_ID_INVALID" if prefix else "RESOURCE_CAPACITY_STRING_INVALID")
    return value


def _timestamp(value: object) -> str:
    value = _string(value, limit=40)
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("RESOURCE_CAPACITY_TIMESTAMP_INVALID") from exc
    if parsed.tzinfo is None:
        raise ValueError("RESOURCE_CAPACITY_TIMESTAMP_INVALID")
    return parsed.isoformat(timespec="seconds")


def _period(value: object, *, with_kind: bool) -> dict[str, Any]:
    fields = {"member_id", "year", "month"}
    if with_kind:
        fields.add("commitment_kind")
    item = _exact(value, fields, "RESOURCE_CAPACITY_COVERAGE_FIELDS_INVALID")
    year, month = item["year"], item["month"]
    if (not isinstance(year, int) or isinstance(year, bool) or not 2000 <= year <= 2100
            or not isinstance(month, int) or isinstance(month, bool) or not 1 <= month <= 12):
        raise ValueError("RESOURCE_CAPACITY_PERIOD_INVALID")
    result = {"member_id": _string(item["member_id"], prefix="member-synthetic-"),
              "year": year, "month": month}
    if with_kind:
        if not isinstance(item["commitment_kind"], str) or item["commitment_kind"] not in COMMITMENT_KINDS:
            raise ValueError("RESOURCE_CAPACITY_COMMITMENT_KIND_INVALID")
        result["commitment_kind"] = item["commitment_kind"]
    return result


def _key(item: dict[str, Any]) -> tuple[str, int, int, str]:
    return item["member_id"], item["year"], item["month"], item["commitment_kind"]


def _normalize_observation(value: object, assessment: datetime) -> dict[str, Any]:
    item = _exact(value, {
        "member_id", "year", "month", "commitment_kind", "fraction", "value_state",
        "authoritative_source_id", "source_reference", "observed_at", "rule_version",
        "source_observation_version",
    }, "RESOURCE_CAPACITY_OBSERVATION_FIELDS_INVALID")
    result = _period({k: item[k] for k in ("member_id", "year", "month", "commitment_kind")}, with_kind=True)
    fraction = item["fraction"]
    if (not isinstance(fraction, (int, float)) or isinstance(fraction, bool)
            or not 0.0 <= float(fraction) <= 1.0):
        raise ValueError("RESOURCE_CAPACITY_FRACTION_RANGE_INVALID")
    if item["value_state"] != "known":
        raise ValueError("RESOURCE_CAPACITY_VALUE_STATE_INVALID")
    kind = result["commitment_kind"]
    source = _string(item["authoritative_source_id"], prefix="source-synthetic-")
    if source != SOURCE_AUTHORITY[kind]:
        raise ValueError("RESOURCE_CAPACITY_SOURCE_AUTHORITY_INVALID")
    observed_at = _timestamp(item["observed_at"])
    if datetime.fromisoformat(observed_at) > assessment:
        raise ValueError("RESOURCE_CAPACITY_OBSERVATION_IN_FUTURE")
    version = item["source_observation_version"]
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        raise ValueError("RESOURCE_CAPACITY_OBSERVATION_VERSION_INVALID")
    result.update({
        "fraction": float(fraction), "value_state": "known",
        "authoritative_source_id": source,
        "source_reference": _string(item["source_reference"], prefix="synthetic-"),
        "observed_at": observed_at,
        "rule_version": _string(item["rule_version"], limit=80),
        "source_observation_version": version,
    })
    result["fingerprint"] = hashlib.sha256(_json(result).encode()).hexdigest()
    return result


def validate_package(payload: object) -> dict[str, Any]:
    item = _exact(payload, _TOP_FIELDS, "RESOURCE_CAPACITY_PACKAGE_FIELDS_INVALID")
    if item["dataset_marker"] != DATASET_MARKER:
        raise ValueError("RESOURCE_CAPACITY_SYNTHETIC_MARKER_REQUIRED")
    if item["schema_version"] != PACKAGE_SCHEMA_VERSION:
        raise ValueError("RESOURCE_CAPACITY_PACKAGE_VERSION_INVALID")
    assessment_time = _timestamp(item["assessment_time"])
    assessment = datetime.fromisoformat(assessment_time)
    generated_at = _timestamp(item["generated_at"])
    if datetime.fromisoformat(generated_at) > assessment:
        raise ValueError("RESOURCE_CAPACITY_GENERATED_AFTER_ASSESSMENT")
    if not isinstance(item["observations"], list):
        raise ValueError("RESOURCE_CAPACITY_OBSERVATIONS_INVALID")
    manifest = _exact(item["manifest"], {"member_periods", "commitment_kinds", "coverage_keys"},
                      "RESOURCE_CAPACITY_MANIFEST_FIELDS_INVALID")
    if not all(isinstance(manifest.get(field), list) for field in manifest):
        raise ValueError("RESOURCE_CAPACITY_MANIFEST_COLLECTION_INVALID")
    periods = [_period(value, with_kind=False) for value in manifest["member_periods"]]
    if not periods:
        raise ValueError("RESOURCE_CAPACITY_MANIFEST_EMPTY")
    period_keys = [(p["member_id"], p["year"], p["month"]) for p in periods]
    if len(period_keys) != len(set(period_keys)):
        raise ValueError("RESOURCE_CAPACITY_PERIOD_DUPLICATE")
    if manifest["commitment_kinds"] != list(COMMITMENT_KINDS):
        raise ValueError("RESOURCE_CAPACITY_COMMITMENT_KINDS_INCOMPLETE")
    coverage = [_period(value, with_kind=True) for value in manifest["coverage_keys"]]
    coverage_keys = [_key(value) for value in coverage]
    if len(coverage_keys) != len(set(coverage_keys)):
        raise ValueError("RESOURCE_CAPACITY_COVERAGE_DUPLICATE")
    expected = {(member, year, month, kind) for member, year, month in period_keys
                for kind in COMMITMENT_KINDS}
    if set(coverage_keys) != expected:
        raise ValueError("RESOURCE_CAPACITY_COVERAGE_INCOMPLETE")
    observations = [_normalize_observation(value, assessment) for value in item["observations"]]
    observation_keys = [_key(value) for value in observations]
    if len(observation_keys) != len(set(observation_keys)):
        raise ValueError("RESOURCE_CAPACITY_OBSERVATION_DUPLICATE")
    if set(observation_keys) != expected:
        raise ValueError("RESOURCE_CAPACITY_OBSERVATION_COVERAGE_INCOMPLETE")
    normalized = {
        "dataset_marker": DATASET_MARKER,
        "package_id": _string(item["package_id"], prefix="package-synthetic-"),
        "schema_version": PACKAGE_SCHEMA_VERSION,
        "generated_at": generated_at,
        "source_id": _string(item["source_id"], prefix="source-synthetic-"),
        "idempotency_key": _string(item["idempotency_key"], prefix="resource-capacity-synthetic-"),
        "plan_version_id": _string(item["plan_version_id"], prefix="plan-synthetic-"),
        "assessment_time": assessment_time,
        "manifest": {"member_periods": periods, "commitment_kinds": list(COMMITMENT_KINDS),
                     "coverage_keys": coverage},
        "observations": observations,
    }
    periods.sort(key=lambda p: (p["member_id"], p["year"], p["month"]))
    coverage.sort(key=_key)
    observations.sort(key=_key)
    return normalized


def _reject(package: dict[str, Any], fingerprint: str, code: str, counts: dict[str, int], *, db_path=None) -> dict[str, Any]:
    session_id = f"resource-capacity-session-{uuid4().hex}"
    now = _now()
    repository.create_session(session_id=session_id, package=package, fingerprint=fingerprint,
                              status="rejected", created_at=now, failure_code=code, db_path=db_path)
    repository.record_run(session_id=session_id, attempt_id=None, step_key="validate",
                          status="rejected", counts=counts, warning_codes=[code],
                          created_at=now, db_path=db_path)
    return {"status": "rejected", "session_id": session_id, "idempotent": False,
            "failure_code": code}


def _fingerprint(value: Any) -> str:
    return hashlib.sha256(_json(value).encode()).hexdigest()


def preview_import(payload: object, *, db_path: str | Path | None = None) -> dict[str, Any]:
    package = validate_package(payload)
    fingerprint = hashlib.sha256(_json(package).encode()).hexdigest()
    counts = {"member_periods": len(package["manifest"]["member_periods"]),
              "coverage_keys": len(package["manifest"]["coverage_keys"]),
              "observations": len(package["observations"]),
              "explicit_zero_observations": sum(o["fraction"] == 0 for o in package["observations"])}
    existing = repository.session_by_fingerprint(fingerprint, db_path=db_path)
    if existing:
        if existing["status"] == "completed":
            return {"status": "already_completed", "session_id": existing["session_id"],
                    "idempotent": True, "report": json.loads(existing["report_json"])}
        return {"status": "in_progress" if existing["status"] == "running" else "retryable",
                "session_id": existing["session_id"], "idempotent": False, "counts": counts}
    if repository.completed_session_for_package(package["package_id"], db_path=db_path):
        return _reject(package, fingerprint, "RESOURCE_CAPACITY_PACKAGE_REPLAY_CONFLICT", counts, db_path=db_path)
    prior_idempotency = repository.session_for_idempotency_key(
        package["idempotency_key"], db_path=db_path
    )
    if prior_idempotency:
        return _reject(
            package, fingerprint, "RESOURCE_CAPACITY_IDEMPOTENCY_KEY_CONFLICT", counts,
            db_path=db_path,
        )
    dependency = dependency_snapshot(package["manifest"]["member_periods"], package["plan_version_id"], db_path=db_path)
    if any(period["state"] != "known" for period in dependency["periods"]):
        raise ValueError("RESOURCE_CAPACITY_DEPENDENCY_COVERAGE_INCOMPLETE")
    scope = set(_key(value) for value in package["manifest"]["coverage_keys"])
    current_scope = repository.current_scope(db_path=db_path)
    if current_scope is not None and scope != current_scope:
        return _reject(package, fingerprint, "RESOURCE_CAPACITY_REPLACEMENT_SCOPE_INCOMPLETE", counts, db_path=db_path)
    current = repository.current_observation_versions(db_path=db_path)
    for observation in package["observations"]:
        prior = current.get(_key(observation))
        if prior and observation["source_observation_version"] <= prior[0]:
            code = ("RESOURCE_CAPACITY_OBSERVATION_VERSION_CONFLICT"
                    if observation["source_observation_version"] == prior[0]
                    else "RESOURCE_CAPACITY_OBSERVATION_VERSION_STALE")
            return _reject(package, fingerprint, code, counts, db_path=db_path)
    derivations = _derive(package, dependency)
    preview_binding = {
        "dependency_fingerprint": _fingerprint(dependency),
        "derivation_fingerprint": _fingerprint(derivations),
    }
    session_id = f"resource-capacity-session-{uuid4().hex}"
    now = _now()
    repository.create_session(session_id=session_id, package=package, fingerprint=fingerprint,
                              status="previewed", created_at=now, report=preview_binding,
                              db_path=db_path)
    repository.record_run(session_id=session_id, attempt_id=None, step_key="validate",
                          status="completed", counts=counts, warning_codes=[], created_at=now,
                          db_path=db_path)
    return {"status": "previewed", "session_id": session_id, "idempotent": False,
            "package_fingerprint": fingerprint, "counts": counts,
            "coverage": {"authoritative_manifest": True, "missing_record_count": 0},
            "dependency": {"workforce_publication_id": dependency["publication_id"],
                           "plan_version_id": dependency["plan_version_id"]},
            "derivation_preview": [
                {key: item[key] for key in (
                    "member_id", "year", "month", "state", "state_reason",
                    "effective_capacity", "planned_project_allocation",
                    "available_capacity", "overload_amount", "overload_state",
                )}
                for item in derivations
            ],
            "confirmation_required": True}


def _derive(package: dict[str, Any], dependency: dict[str, Any]) -> list[dict[str, Any]]:
    observations = {_key(o): o for o in package["observations"]}
    assessment = datetime.fromisoformat(package["assessment_time"])
    results = []
    for fact in dependency["periods"]:
        identity = (fact["member_id"], fact["year"], fact["month"])
        by_kind = {kind: observations[(*identity, kind)] for kind in COMMITMENT_KINDS}
        fractions = {kind: by_kind[kind]["fraction"] for kind in COMMITMENT_KINDS}
        deduction = round(sum(fractions.values()), 10)
        planned = fact["planned_project_allocation"]
        stale = any((assessment - datetime.fromisoformat(o["observed_at"])).total_seconds() > 720 * 3600
                    for o in by_kind.values())
        state, reason = "known", "complete_fresh_evidence"
        if fact["state"] != "known" or fact["employment_status"] != "active":
            state, reason = "unknown", "workforce_or_allocation_not_active_complete"
        elif stale:
            state, reason = "stale", "commitment_observation_exceeds_720_hours"
        base = 1.0 if fact["state"] == "known" and fact["employment_status"] == "active" else None
        if state == "known":
            raw = round(base - deduction, 10)
            effective = max(0.0, raw)
            available_raw = round(effective - planned, 10)
            available = max(0.0, available_raw)
            total = round(planned + deduction, 10)
            overload = max(0.0, round(planned - effective, 10))
            overload_state = "clear" if overload == 0 else "amber" if overload <= 0.10 else "red"
        else:
            raw = effective = available_raw = available = total = overload = overload_state = None
        results.append({
            "member_id": identity[0], "year": identity[1], "month": identity[2],
            "state": state, "state_reason": reason, "base_capacity": base,
            "leave_fraction": fractions["leave"], "bau_fraction": fractions["bau"],
            "non_project_fraction": fractions["non_project"],
            "non_project_deduction": deduction, "effective_capacity_raw": raw,
            "effective_capacity": effective, "planned_project_allocation": planned,
            "available_capacity_raw": available_raw, "available_capacity": available,
            "total_commitment": total, "overload_amount": overload,
            "overload_state": overload_state,
            "evidence": {"workforce_publication_id": dependency["publication_id"],
                         "plan_version_id": dependency["plan_version_id"],
                         "allocation_evidence": fact["allocation_evidence"],
                         "commitment_observation_fingerprints":
                         {kind: by_kind[kind]["fingerprint"] for kind in COMMITMENT_KINDS}},
        })
    return results


def _failure_code(exc: Exception) -> str:
    if str(exc).startswith("RESOURCE_CAPACITY_"):
        return str(exc)
    return "RESOURCE_CAPACITY_PUBLICATION_FAILED"


def confirm_import(session_id: str, *, db_path: str | Path | None = None) -> dict[str, Any]:
    session = repository.load_session(session_id, db_path=db_path)
    if not session:
        raise ValueError("RESOURCE_CAPACITY_SESSION_NOT_FOUND")
    if session["status"] == "completed":
        return {"status": "completed", "session_id": session_id, "idempotent": True,
                "report": json.loads(session["report_json"])}
    if session["status"] == "rejected":
        raise ValueError("RESOURCE_CAPACITY_SESSION_NOT_CONFIRMABLE")
    attempt = repository.start_attempt(session_id, started_at=_now(), db_path=db_path)
    package = json.loads(session["package_json"])
    preview_binding = json.loads(session["report_json"])
    try:
        dependency = dependency_snapshot(package["manifest"]["member_periods"],
                                         package["plan_version_id"], db_path=db_path)
        if any(period["state"] != "known" for period in dependency["periods"]):
            raise ValueError("RESOURCE_CAPACITY_DEPENDENCY_COVERAGE_INCOMPLETE")
        derivations = _derive(package, dependency)
        if preview_binding != {
            "dependency_fingerprint": _fingerprint(dependency),
            "derivation_fingerprint": _fingerprint(derivations),
        }:
            raise ValueError("RESOURCE_CAPACITY_PREVIEW_BINDING_CHANGED")
        report = repository.publish(session_id=session_id, attempt_id=attempt,
                                    fingerprint=session["package_fingerprint"], package=package,
                                    dependency=dependency, derivations=derivations,
                                    published_at=_now(), db_path=db_path)
    except Exception as exc:
        repository.fail_attempt(session_id=session_id, attempt_id=attempt,
                                failure_code=_failure_code(exc), finished_at=_now(), db_path=db_path)
        raise
    return {"status": "completed", "session_id": session_id, "idempotent": False,
            "report": report}
