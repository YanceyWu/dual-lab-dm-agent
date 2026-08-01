"""Controlled, non-routed Weekly Brief v2 snapshot capture contract.

The B2 core deliberately receives query facts through an injected public-contract
lookup/recomposer.  It therefore cannot reach into Attention, Health, Resource,
Action, or legacy-report storage; B3 will supply the v2 composer at this seam.
"""

from __future__ import annotations

import hashlib
import json
import re
import secrets
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from pm_agent.weekly_brief import repository

_WARNING_INVALID = "WEEKLY_BRIEF_CAPTURE_CANDIDATE_INVALID"
_WARNING_STALE = "WEEKLY_BRIEF_CAPTURE_CANDIDATE_STALE"
_WARNING_EXPIRED = "WEEKLY_BRIEF_CAPTURE_OPERATION_EXPIRED"
_WARNING_TOKEN = "WEEKLY_BRIEF_CAPTURE_TOKEN_INVALID"
_WARNING_CONFIRMED = "WEEKLY_BRIEF_CAPTURE_ALREADY_CONFIRMED"
_WARNING_CONFLICT = "WEEKLY_BRIEF_CAPTURE_CONFLICT"
_WARNING_ACCESS = "WEEKLY_BRIEF_CAPTURE_DATA_ACCESS_FAILED"
_REQUIRED = {"execution_id", "contract_version", "comparison_rule_version", "generated_at", "week_key", "scope", "input", "baseline_snapshot_id", "baseline_fingerprint", "statement_manifest", "evidence_summary", "section_coverage", "limitation_codes"}
_STATEMENT_KEYS = {"identity_key", "producer", "scope_fingerprint", "semantic_fingerprint", "evidence_state_fingerprint", "active_material", "transition_state", "coverage_complete", "usable_evidence", "limited_active_proven"}
_PRODUCERS = {"attention", "project_health", "resource_intelligence", "action", "execution", "decision"}
_TRANSITIONS = {"active", "clear", "resolved", "completed", "green"}
_ANON_ID = re.compile(r"^[a-z][a-z0-9-]{2,127}$")
_HEX = re.compile(r"^[0-9a-f]{64}$")
_CODE = re.compile(r"^[A-Z][A-Z0-9_]{2,127}$")


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _fingerprint(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode()).hexdigest()


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _normalized(candidate: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(candidate, dict) or set(candidate) != _REQUIRED:
        raise ValueError(_WARNING_INVALID)
    if not isinstance(candidate["scope"], dict) or not isinstance(candidate["input"], dict):
        raise ValueError(_WARNING_INVALID)
    if not isinstance(candidate["statement_manifest"], list):
        raise ValueError(_WARNING_INVALID)
    if not isinstance(candidate["evidence_summary"], dict):
        raise ValueError(_WARNING_INVALID)
    if not isinstance(candidate["section_coverage"], dict) or not isinstance(candidate["limitation_codes"], list):
        raise ValueError(_WARNING_INVALID)
    required_text = _REQUIRED - {"scope", "input", "statement_manifest", "evidence_summary", "section_coverage", "limitation_codes", "baseline_snapshot_id", "baseline_fingerprint"}
    if not all(isinstance(candidate[key], str) and candidate[key] for key in required_text):
        raise ValueError(_WARNING_INVALID)
    if not _ANON_ID.fullmatch(candidate["execution_id"]):
        raise ValueError(_WARNING_INVALID)
    if not all(isinstance(candidate[key], str) for key in ("baseline_snapshot_id", "baseline_fingerprint")):
        raise ValueError(_WARNING_INVALID)
    if bool(candidate["baseline_snapshot_id"]) != bool(candidate["baseline_fingerprint"]):
        raise ValueError(_WARNING_INVALID)
    _parse_time(candidate["generated_at"])
    if _parse_time(candidate["generated_at"]).tzinfo is None or not _safe(candidate):
        raise ValueError(_WARNING_INVALID)
    seen = set()
    for statement in candidate["statement_manifest"]:
        if not isinstance(statement, dict) or set(statement) != _STATEMENT_KEYS:
            raise ValueError(_WARNING_INVALID)
        if not isinstance(statement["identity_key"], str) or not _ANON_ID.fullmatch(statement["identity_key"].replace(":", "-")) or statement["identity_key"] in seen:
            raise ValueError(_WARNING_INVALID)
        seen.add(statement["identity_key"])
        if statement["scope_fingerprint"] != _fingerprint(candidate["scope"]) or statement["producer"] not in _PRODUCERS or statement["transition_state"] not in _TRANSITIONS:
            raise ValueError(_WARNING_INVALID)
        if not all(isinstance(statement[key], str) and _HEX.fullmatch(statement[key]) for key in ("semantic_fingerprint", "evidence_state_fingerprint")):
            raise ValueError(_WARNING_INVALID)
        if not all(isinstance(statement[key], bool) for key in ("active_material", "coverage_complete", "usable_evidence", "limited_active_proven")):
            raise ValueError(_WARNING_INVALID)
        if (statement["transition_state"] == "active") != statement["active_material"]:
            raise ValueError(_WARNING_INVALID)
    normalized = {key: candidate[key] for key in _REQUIRED}
    normalized["scope_fingerprint"] = _fingerprint(normalized["scope"])
    normalized["input_fingerprint"] = _fingerprint(normalized["input"])
    normalized["statement_fingerprint"] = _fingerprint(normalized["statement_manifest"])
    normalized["evidence_state_fingerprint"] = _fingerprint({"evidence_summary": normalized["evidence_summary"], "section_coverage": normalized["section_coverage"], "limitation_codes": normalized["limitation_codes"]})
    normalized["result_fingerprint"] = _fingerprint({key: normalized[key] for key in ("scope_fingerprint", "input_fingerprint", "baseline_snapshot_id", "baseline_fingerprint", "statement_fingerprint", "evidence_state_fingerprint", "contract_version", "comparison_rule_version")})
    return normalized


def _safe(value: Any) -> bool:
    scope, inputs, evidence, coverage, limits = value["scope"], value["input"], value["evidence_summary"], value["section_coverage"], value["limitation_codes"]
    try:
        as_of = "as_of" not in inputs or isinstance(inputs["as_of"], str) and inputs["as_of"].endswith("Z") and _parse_time(inputs["as_of"]).tzinfo is not None
    except (TypeError, ValueError, AttributeError):
        as_of = False
    projects = scope.get("project_ids", [])
    evidence_ids, freshness = evidence.get("evidence_ids", []), evidence.get("freshness_states", [])
    return set(scope) <= {"project_ids"} and isinstance(projects, list) and 1 <= len(projects) <= 200 and projects == sorted(projects) and len(set(projects)) == len(projects) and all(isinstance(item, str) and _ANON_ID.fullmatch(item) for item in projects) and set(inputs) <= {"as_of", "plan_version_id", "limit"} and as_of and ("plan_version_id" not in inputs or isinstance(inputs["plan_version_id"], str) and _ANON_ID.fullmatch(inputs["plan_version_id"])) and ("limit" not in inputs or isinstance(inputs["limit"], int) and 1 <= inputs["limit"] <= 200) and set(evidence) <= {"producer", "evidence_ids", "freshness_states"} and isinstance(evidence.get("producer", ""), str) and _ANON_ID.fullmatch(evidence.get("producer", "")) and isinstance(evidence_ids, list) and isinstance(freshness, list) and all(isinstance(item, str) and _ANON_ID.fullmatch(item) for item in evidence_ids) and all(isinstance(item, str) and item in {"fresh", "stale", "partial", "unknown", "unavailable", "conflicting"} for item in freshness) and all(isinstance(key, str) and key in _PRODUCERS and isinstance(item, str) and item in {"complete", "partial", "not_available"} for key, item in coverage.items()) and all(isinstance(item, str) and _CODE.fullmatch(item) for item in limits)


class WeeklyBriefSnapshotService:
    """Preview/confirm capture using only B3-supplied public query contracts."""

    def __init__(self, *, query_lookup: Callable[[str], dict[str, Any] | None], recompose: Callable[[dict[str, Any]], dict[str, Any] | None], db_path=None, clock: Callable[[], str] = _utc_now):
        self.query_lookup = query_lookup
        self.recompose = recompose
        self.db_path = db_path
        self.clock = clock

    def preview(self, *, candidate: dict[str, Any], actor_id: str, idempotency_key: str, expires_in_seconds: int = 600) -> dict[str, Any]:
        if not all(isinstance(value, str) and _ANON_ID.fullmatch(value) for value in (actor_id, idempotency_key)) or not isinstance(expires_in_seconds, int) or not 1 <= expires_in_seconds <= 3600:
            return self._failed(_WARNING_INVALID)
        try:
            normalized = _normalized(candidate)
            observed = self.query_lookup(normalized["execution_id"])
            if observed is None or _normalized(observed) != normalized:
                return self._failed(_WARNING_INVALID)
            if normalized["baseline_snapshot_id"] and not repository.baseline_is_eligible(normalized["baseline_snapshot_id"], normalized["baseline_fingerprint"], normalized["scope_fingerprint"], normalized["comparison_rule_version"], normalized["contract_version"], db_path=self.db_path):
                return self._failed(_WARNING_INVALID)
        except (TypeError, ValueError, KeyError):
            return self._failed(_WARNING_INVALID)
        except Exception:
            return self._failed(_WARNING_ACCESS)
        try:
            existing = repository.load_by_idempotency(actor_id, idempotency_key, db_path=self.db_path)
        except Exception:
            return self._failed(_WARNING_ACCESS)
        if existing:
            if existing["result_fingerprint"] == normalized["result_fingerprint"] and existing["status"] == "confirmed":
                return self._result("already_confirmed", existing, [_WARNING_CONFIRMED])
            return self._failed(_WARNING_CONFLICT)
        now = self.clock()
        try:
            expires_at = (_parse_time(now) + timedelta(seconds=expires_in_seconds)).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        except ValueError:
            return self._failed(_WARNING_INVALID)
        token = secrets.token_urlsafe(32)
        operation_id = f"weekly-brief-capture-{uuid4().hex}"
        row = {"operation_id": operation_id, "snapshot_id": None, "execution_id": normalized["execution_id"], "contract_version": normalized["contract_version"], "comparison_rule_version": normalized["comparison_rule_version"], "generated_at": normalized["generated_at"], "week_key": normalized["week_key"], "scope_json": repository.json_value(normalized["scope"]), "scope_fingerprint": normalized["scope_fingerprint"], "input_fingerprint": normalized["input_fingerprint"], "baseline_snapshot_id": normalized["baseline_snapshot_id"], "baseline_fingerprint": normalized["baseline_fingerprint"], "statement_fingerprint": normalized["statement_fingerprint"], "evidence_state_fingerprint": normalized["evidence_state_fingerprint"], "result_fingerprint": normalized["result_fingerprint"], "candidate_json": repository.json_value(normalized), "statement_manifest_json": repository.json_value(normalized["statement_manifest"]), "evidence_summary_json": repository.json_value(normalized["evidence_summary"]), "section_coverage_json": repository.json_value(normalized["section_coverage"]), "limitation_codes_json": repository.json_value(normalized["limitation_codes"]), "structural_status": "complete", "actor_id": actor_id, "idempotency_key": idempotency_key, "confirmation_token_hash": _token_hash(token), "expires_at": expires_at, "status": "proposed", "created_at": now, "confirmed_at": "", "failure_code": ""}
        try:
            inserted = repository.insert_proposal(row, db_path=self.db_path)
        except Exception:
            return self._failed(_WARNING_ACCESS)
        if not inserted:
            existing = repository.load_by_idempotency(actor_id, idempotency_key, db_path=self.db_path)
            if existing and existing["result_fingerprint"] == normalized["result_fingerprint"]:
                return self._result("already_confirmed" if existing["status"] == "confirmed" else "failed", existing, [_WARNING_CONFIRMED if existing["status"] == "confirmed" else _WARNING_CONFLICT])
            return self._failed(_WARNING_CONFLICT)
        return {"status": "previewed", "operation_id": operation_id, "candidate": normalized, "confirmation_required": True, "expires_at": expires_at, "confirmation_token": token, "warnings": []}

    def confirm(self, *, operation_id: str, confirmation_token: str) -> dict[str, Any]:
        if not isinstance(operation_id, str) or not operation_id.startswith("weekly-brief-capture-") or len(operation_id) > 128 or not isinstance(confirmation_token, str) or not 32 <= len(confirmation_token) <= 512:
            return self._failed(_WARNING_TOKEN)
        try:
            row = repository.claim(operation_id, token_hash=_token_hash(confirmation_token), now=self.clock(), db_path=self.db_path)
        except Exception:
            return self._failed(_WARNING_ACCESS)
        if row is None:
            return self._failed(_WARNING_INVALID)
        if row["status"] == "confirmed":
            if secrets.compare_digest(row["confirmation_token_hash"], _token_hash(confirmation_token)):
                return self._result("already_confirmed", row, [_WARNING_CONFIRMED])
            return self._failed(_WARNING_TOKEN)
        if row["status"] == "expired":
            return self._result("expired", row, [_WARNING_EXPIRED])
        if row["status"] == "proposed":
            return self._failed(_WARNING_TOKEN)
        if row["status"] == "claimed" and not secrets.compare_digest(row["confirmation_token_hash"], _token_hash(confirmation_token)):
            return self._failed(_WARNING_TOKEN)
        if row["status"] != "claimed":
            return self._failed(_WARNING_CONFLICT)
        try:
            candidate = json.loads(row["candidate_json"])
            current = self.recompose(candidate)
            if current is None or _normalized(current) != candidate:
                try:
                    repository.fail_claim(operation_id, code=_WARNING_STALE, db_path=self.db_path)
                except Exception:
                    return self._failed(_WARNING_ACCESS)
                return self._result("stale", row, [_WARNING_STALE])
            if candidate["baseline_snapshot_id"] and not repository.baseline_is_eligible(candidate["baseline_snapshot_id"], candidate["baseline_fingerprint"], candidate["scope_fingerprint"], candidate["comparison_rule_version"], candidate["contract_version"], db_path=self.db_path):
                try:
                    repository.fail_claim(operation_id, code=_WARNING_STALE, db_path=self.db_path)
                except Exception:
                    return self._failed(_WARNING_ACCESS)
                return self._result("stale", row, [_WARNING_STALE])
        except Exception:
            try:
                repository.fail_claim(operation_id, code=_WARNING_ACCESS, db_path=self.db_path)
            except Exception:
                pass
            return self._failed(_WARNING_ACCESS)
        snapshot_id = f"weekly-brief-snapshot-{uuid4().hex}"
        confirmed_at = self.clock()
        try:
            if not repository.confirm(operation_id, snapshot_id=snapshot_id, confirmed_at=confirmed_at, db_path=self.db_path):
                expired = repository.claim(operation_id, token_hash=_token_hash(confirmation_token), now=confirmed_at, db_path=self.db_path)
                if expired and expired["status"] == "expired":
                    return self._result("expired", expired, [_WARNING_EXPIRED])
                return self._failed(_WARNING_CONFLICT)
            confirmed = repository.load_operation(operation_id, db_path=self.db_path)
        except Exception:
            return self._failed(_WARNING_ACCESS)
        return self._result("confirmed", confirmed or row, [])

    @staticmethod
    def _failed(code: str) -> dict[str, Any]:
        return {"status": "failed", "warnings": [code]}

    @staticmethod
    def _result(status: str, row: dict[str, Any], warnings: list[str]) -> dict[str, Any]:
        return {"status": status, "operation_id": row["operation_id"], "confirmed_snapshot_id": row.get("snapshot_id"), "confirmed_at": row.get("confirmed_at") or None, "scope_fingerprint": row["scope_fingerprint"], "result_fingerprint": row["result_fingerprint"], "warnings": warnings}
