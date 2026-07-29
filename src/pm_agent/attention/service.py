"""Preview/confirm service for deterministic Attention reconciliation and lifecycle."""

from __future__ import annotations

import hashlib
import json
import re
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from pm_agent.attention import rules
from pm_agent.database import attention as attention_repository

TOKEN_TTL_SECONDS = 300
MAX_SNOOZE_DAYS = 30
_STABLE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_SUBJECT_KIND_BY_RULE = {
    "project_health_attention": "project",
    "overdue_action_attention": "action",
    "source_freshness_attention": "source",
    "resource_overload_attention": "member",
    "pending_decision_attention": "decision",
}


class AttentionService:
    """Attention-specific preview/confirm service outside ToolTransport."""

    def preview_reconciliation(
        self,
        *,
        actor: str,
        rule_keys: list[str] | None = None,
        subject_kind: str | None = None,
        subject_id: str | None = None,
    ) -> dict[str, Any]:
        try:
            normalized_actor = _bounded_id(actor, "actor")
            scope = _reconciliation_scope(rule_keys, subject_kind, subject_id)
            with attention_repository.attention_connection() as connection:
                now = _utc_now()
                evaluation = rules.evaluate(connection, **scope, now=now)
                current = attention_repository.list_signals(connection, **scope)
                proposed = _transition_plan(evaluation, current, now=now)
                return _create_preview(
                    connection,
                    action="reconcile",
                    actor=normalized_actor,
                    scope=scope,
                    proposed=proposed,
                )
        except (rules.InvalidAttentionCatalog, ValueError):
            return _failure("ATTENTION_PREVIEW_INVALID")
        except (json.JSONDecodeError, sqlite3.Error):
            return _failure("DATA_ACCESS_FAILED")

    def preview_acknowledgement(
        self,
        *,
        attention_id: str,
        actor: str,
    ) -> dict[str, Any]:
        return self._preview_lifecycle(
            action="acknowledge",
            attention_id=attention_id,
            actor=actor,
        )

    def preview_project_health_rag_configuration(
        self,
        *,
        actor: str,
        target: str,
        configuration: dict[str, Any] | None = None,
        project_id: str | None = None,
        remove_override: bool = False,
    ) -> dict[str, Any]:
        """Reject the unaccepted legacy mapping-configuration surface."""
        return _failure("ATTENTION_RAG_CONFIGURATION_UNAVAILABLE")

    def preview_snooze(
        self,
        *,
        attention_id: str,
        actor: str,
        snoozed_until: str,
    ) -> dict[str, Any]:
        try:
            expiry = _parse_timestamp(snoozed_until)
            now = _utc_now()
            if expiry <= now or expiry > now + timedelta(days=MAX_SNOOZE_DAYS):
                return _failure("ATTENTION_SNOOZE_EXPIRY_INVALID")
        except ValueError:
            return _failure("ATTENTION_SNOOZE_EXPIRY_INVALID")
        return self._preview_lifecycle(
            action="snooze",
            attention_id=attention_id,
            actor=actor,
            snoozed_until=_iso(expiry),
        )

    def preview_resolution(
        self,
        *,
        attention_id: str,
        actor: str,
    ) -> dict[str, Any]:
        return self._preview_lifecycle(
            action="resolve",
            attention_id=attention_id,
            actor=actor,
        )

    def confirm(
        self,
        *,
        operation_id: str,
        confirmation_token: str,
    ) -> dict[str, Any]:
        normalized_operation_id = ""
        try:
            normalized_operation_id = _bounded_id(operation_id, "operation_id")
            if (
                not isinstance(confirmation_token, str)
                or not confirmation_token
                or len(confirmation_token) > 256
            ):
                return _failure("ATTENTION_CONFIRMATION_INVALID")
            return self._confirm_transaction(
                normalized_operation_id,
                confirmation_token,
            )
        except rules.InvalidAttentionCatalog:
            _record_operation_failure(
                normalized_operation_id,
                "ATTENTION_RULE_CATALOG_INVALID",
            )
            return _failure("ATTENTION_RULE_CATALOG_INVALID")
        except ValueError:
            _record_operation_failure(
                normalized_operation_id,
                "ATTENTION_CONFIRMATION_INVALID",
            )
            return _failure("ATTENTION_CONFIRMATION_INVALID")
        except (json.JSONDecodeError, KeyError, TypeError, sqlite3.Error):
            _record_operation_failure(
                normalized_operation_id,
                "DATA_ACCESS_FAILED",
            )
            return _failure("DATA_ACCESS_FAILED")

    def _preview_lifecycle(
        self,
        *,
        action: str,
        attention_id: str,
        actor: str,
        snoozed_until: str = "",
    ) -> dict[str, Any]:
        try:
            normalized_actor = _bounded_id(actor, "actor")
            normalized_attention_id = _bounded_id(attention_id, "attention_id")
            with attention_repository.attention_connection() as connection:
                signal = attention_repository.get_signal(
                    connection,
                    normalized_attention_id,
                )
                failure_code = _validate_lifecycle(
                    action,
                    signal,
                    snoozed_until=snoozed_until,
                )
                if failure_code:
                    return _failure(failure_code)
                scope = {"attention_id": normalized_attention_id}
                if snoozed_until:
                    scope["snoozed_until"] = snoozed_until
                proposed = {
                    "transition_count": 1,
                    "prior_attention_state": signal["attention_state"],
                    "new_attention_state": _target_state(action),
                }
                return _create_preview(
                    connection,
                    action=action,
                    actor=normalized_actor,
                    scope=scope,
                    proposed=proposed,
                )
        except ValueError:
            return _failure("ATTENTION_PREVIEW_INVALID")
        except sqlite3.Error:
            return _failure("DATA_ACCESS_FAILED")

    def _confirm_transaction(
        self,
        operation_id: str,
        confirmation_token: str,
    ) -> dict[str, Any]:
        with attention_repository.attention_connection(immediate=True) as connection:
            operation = attention_repository.get_operation(connection, operation_id)
            if operation is None:
                if attention_repository.get_configuration_operation(
                    connection,
                    operation_id,
                ):
                    return _failure("ATTENTION_RAG_CONFIGURATION_UNAVAILABLE")
                return _failure("ATTENTION_OPERATION_NOT_FOUND")
            if operation["status"] != "proposed":
                return _failure("ATTENTION_OPERATION_ALREADY_USED")
            if not secrets.compare_digest(
                operation["token_hash"],
                _token_hash(confirmation_token),
            ):
                return _failure("ATTENTION_CONFIRMATION_INVALID")
            now = _utc_now()
            if _parse_timestamp(operation["expires_at"]) <= now:
                attention_repository.expire_operation(
                    connection,
                    operation_id=operation_id,
                    finished_at=_iso(now),
                )
                return _failure("ATTENTION_CONFIRMATION_EXPIRED")
            if not attention_repository.claim_operation(
                connection,
                operation_id=operation_id,
                claimed_at=_iso(now),
            ):
                return _failure("ATTENTION_OPERATION_ALREADY_USED")

            if operation["action"] == "reconcile":
                result = self._confirm_reconciliation(
                    connection,
                    operation,
                    now,
                )
            else:
                result = self._confirm_lifecycle(
                    connection,
                    operation,
                    now,
                )
            attention_repository.finish_operation(
                connection,
                operation_id=operation_id,
                success=result["status"] == "success",
                result=result,
                failure_code=result.get("failure_code", ""),
                finished_at=_iso(_utc_now()),
            )
            return result

    def _confirm_reconciliation(
        self,
        connection,
        operation: dict[str, Any],
        now: datetime,
    ) -> dict[str, Any]:
        evaluation = rules.evaluate(connection, **operation["scope"], now=now)
        current = attention_repository.list_signals(
            connection,
            **operation["scope"],
        )
        plan = _transition_plan(evaluation, current, now=now)
        reconciliation_id = f"rec-{uuid4().hex}"
        record = {
            "reconciliation_id": reconciliation_id,
            "operation_id": operation["operation_id"],
            "status": (
                "partial"
                if "partial" in evaluation["rule_status"].values()
                else "success"
            ),
            "actor": operation["actor"],
            "started_at": _iso(now),
            "finished_at": _iso(now),
            "rule_set_version": evaluation["rule_set_version"],
            "warning_codes": evaluation["warning_codes"],
            "candidate_count": plan["candidate_count"],
            "created_count": plan["created_count"],
            "updated_count": plan["updated_count"],
            "cleared_count": plan["cleared_count"],
            "reopened_count": plan["reopened_count"],
        }
        attention_repository.insert_reconciliation(connection, record)
        _apply_reconciliation(
            connection,
            evaluation=evaluation,
            current=current,
            reconciliation_id=reconciliation_id,
            operation_id=operation["operation_id"],
            actor=operation["actor"],
            now=now,
        )
        return {
            "status": "success",
            "reconciliation_id": reconciliation_id,
            "reconciliation_status": record["status"],
            "warning_codes": record["warning_codes"],
            "transitions": plan,
            "preview_changed": plan != operation["proposed"],
        }

    def _confirm_lifecycle(
        self,
        connection,
        operation: dict[str, Any],
        now: datetime,
    ) -> dict[str, Any]:
        signal = attention_repository.get_signal(
            connection,
            operation["scope"]["attention_id"],
        )
        failure_code = _validate_lifecycle(
            operation["action"],
            signal,
            snoozed_until=operation["scope"].get("snoozed_until", ""),
        )
        if failure_code:
            return _failure(failure_code)
        prior_state = signal["attention_state"]
        target_state = _target_state(operation["action"])
        values: dict[str, Any] = {
            "attention_state": target_state,
            "updated_at": _iso(now),
        }
        if operation["action"] == "acknowledge":
            values.update(
                {
                    "acknowledged_at": _iso(now),
                    "acknowledged_by": operation["actor"],
                    "snoozed_until": "",
                    "snoozed_by": "",
                }
            )
        elif operation["action"] == "snooze":
            expiry = _parse_timestamp(operation["scope"]["snoozed_until"])
            if expiry <= now or expiry > now + timedelta(days=MAX_SNOOZE_DAYS):
                return _failure("ATTENTION_SNOOZE_EXPIRY_INVALID")
            values.update(
                {
                    "snoozed_until": _iso(expiry),
                    "snoozed_by": operation["actor"],
                }
            )
        else:
            if signal["attention_state"] != "resolved":
                values.update(
                    {
                        "resolved_at": _iso(now),
                        "resolved_by": operation["actor"],
                        "resolution_reason": "manager_confirmed_clear",
                        "snoozed_until": "",
                        "snoozed_by": "",
                    }
                )
        attention_repository.update_signal(
            connection,
            signal["attention_id"],
            values,
        )
        _history(
            connection,
            signal=signal,
            operation_id=operation["operation_id"],
            reconciliation_id=None,
            event_type={
                "acknowledge": "acknowledged",
                "snooze": "snoozed",
                "resolve": "resolved",
            }[operation["action"]],
            actor=operation["actor"],
            now=now,
            new_attention_state=target_state,
        )
        return {
            "status": "success",
            "attention_id": signal["attention_id"],
            "prior_attention_state": prior_state,
            "attention_state": target_state,
        }


def _create_preview(
    connection,
    *,
    action: str,
    actor: str,
    scope: dict[str, Any],
    proposed: dict[str, Any],
) -> dict[str, Any]:
    now = _utc_now()
    expires_at = now + timedelta(seconds=TOKEN_TTL_SECONDS)
    operation_id = f"attop-{uuid4().hex}"
    token = secrets.token_urlsafe(32)
    attention_repository.create_operation(
        connection,
        {
            "operation_id": operation_id,
            "action": action,
            "actor": actor,
            "scope": scope,
            "token_hash": _token_hash(token),
            "proposed": proposed,
            "created_at": _iso(now),
            "expires_at": _iso(expires_at),
        },
    )
    return {
        "status": "proposed",
        "operation_id": operation_id,
        "confirmation_token": token,
        "expires_at": _iso(expires_at),
        "actor": actor,
        "scope": scope,
        "proposed": proposed,
    }


def _transition_plan(
    evaluation: dict[str, Any],
    current: list[dict[str, Any]],
    *,
    now: datetime,
) -> dict[str, int]:
    current_by_identity = {
        (item["rule_key"], item["subject_kind"], item["subject_id"]): item
        for item in current
    }
    observations = {
        (item["rule_key"], item["subject_kind"], item["subject_id"]): item
        for item in evaluation["observations"]
    }
    counts = {
        "candidate_count": sum(item["active"] for item in observations.values()),
        "created_count": 0,
        "updated_count": 0,
        "cleared_count": 0,
        "reopened_count": 0,
        "lifecycle_count": 0,
        "disabled_count": 0,
        "limited_count": 0,
    }
    for identity, observation in observations.items():
        existing = current_by_identity.get(identity)
        if not existing:
            if observation["active"]:
                counts["created_count"] += 1
            continue
        if observation["active"] and existing["rule_state"] != "active":
            counts["reopened_count"] += 1
        elif observation["active"]:
            updated = (
                _observation_hash(observation["observation"])
                != _last_evaluation_hash(existing)
            )
            target_status = (
                "complete" if observation["complete"] else "partial"
            )
            if existing["evaluation_status"] != target_status:
                updated = True
                if target_status == "partial":
                    counts["limited_count"] += 1
            if _snooze_is_expired(existing, now=now):
                updated = True
                counts["lifecycle_count"] += 1
            counts["updated_count"] += int(updated)
        elif (
            not observation["active"]
            and observation["complete"]
            and existing["rule_state"] == "active"
        ):
            counts["cleared_count"] += 1
        elif (
            not observation["active"]
            and not observation["complete"]
            and existing["rule_state"] == "active"
            and (
                existing["evaluation_status"] != "partial"
                or _observation_hash(observation["observation"])
                != _last_evaluation_hash(existing)
            )
        ):
            counts["updated_count"] += 1
            counts["limited_count"] += 1
    for identity, existing in current_by_identity.items():
        if identity in observations or existing["rule_state"] != "active":
            continue
        status = evaluation["rule_status"].get(existing["rule_key"])
        if status == "complete":
            counts["cleared_count"] += 1
        elif status == "disabled" and existing["evaluation_status"] != "disabled":
            counts["updated_count"] += 1
            counts["disabled_count"] += 1
        elif (
            status in {"partial", "failed"}
            and existing["evaluation_status"] != status
        ):
            counts["updated_count"] += 1
            counts["limited_count"] += 1
    return counts


def _apply_reconciliation(
    connection,
    *,
    evaluation: dict[str, Any],
    current: list[dict[str, Any]],
    reconciliation_id: str,
    operation_id: str,
    actor: str,
    now: datetime,
) -> None:
    current_by_identity = {
        (item["rule_key"], item["subject_kind"], item["subject_id"]): item
        for item in current
    }
    observed_identities: set[tuple[str, str, str]] = set()
    now_text = _iso(now)
    for observation in evaluation["observations"]:
        identity = (
            observation["rule_key"],
            observation["subject_kind"],
            observation["subject_id"],
        )
        observed_identities.add(identity)
        existing = current_by_identity.get(identity)
        if not existing:
            if not observation["active"]:
                continue
            attention_id = _attention_id(*identity)
            record = {
                "attention_id": attention_id,
                "rule_key": observation["rule_key"],
                "rule_version": observation["rule_version"],
                "subject_kind": observation["subject_kind"],
                "subject_id": observation["subject_id"],
                "rule_state": "active",
                "attention_state": "open",
                "evaluation_status": "complete" if observation["complete"] else "partial",
                "severity": observation["severity"],
                "first_seen_at": now_text,
                "last_seen_at": now_text,
                "last_reconciliation_id": reconciliation_id,
                "observation_hash": _observation_hash(observation["observation"]),
                "last_evaluation_hash": _observation_hash(
                    observation["observation"]
                ),
                "observation": observation["observation"],
                "created_at": now_text,
                "updated_at": now_text,
            }
            attention_repository.insert_signal(connection, record)
            _history(
                connection,
                signal=record,
                operation_id=operation_id,
                reconciliation_id=reconciliation_id,
                event_type="detected",
                actor=actor,
                now=now,
                prior_rule_state="",
                new_rule_state="active",
                prior_attention_state="",
                new_attention_state="open",
            )
            continue
        _apply_observation(
            connection,
            existing=existing,
            observation=observation,
            reconciliation_id=reconciliation_id,
            operation_id=operation_id,
            actor=actor,
            now=now,
        )

    for identity, existing in current_by_identity.items():
        if identity in observed_identities:
            continue
        status = evaluation["rule_status"].get(existing["rule_key"])
        if status == "disabled":
            if existing["evaluation_status"] != "disabled":
                attention_repository.update_signal(
                    connection,
                    existing["attention_id"],
                    {
                        "evaluation_status": "disabled",
                        "last_reconciliation_id": reconciliation_id,
                        "updated_at": now_text,
                    },
                )
                _history(
                    connection,
                    signal=existing,
                    operation_id=operation_id,
                    reconciliation_id=reconciliation_id,
                    event_type="rule_disabled",
                    actor=actor,
                    now=now,
                )
            else:
                attention_repository.update_signal(
                    connection,
                    existing["attention_id"],
                    {
                        "last_reconciliation_id": reconciliation_id,
                        "updated_at": now_text,
                    },
                )
        elif status == "complete" and existing["rule_state"] == "active":
            _clear_signal(
                connection,
                existing=existing,
                reconciliation_id=reconciliation_id,
                operation_id=operation_id,
                actor=actor,
                now=now,
            )
        elif status in {"partial", "failed"} and existing["rule_state"] == "active":
            _limit_signal(
                connection,
                existing=existing,
                reconciliation_id=reconciliation_id,
                operation_id=operation_id,
                actor=actor,
                now=now,
                status=status,
            )


def _apply_observation(
    connection,
    *,
    existing: dict[str, Any],
    observation: dict[str, Any],
    reconciliation_id: str,
    operation_id: str,
    actor: str,
    now: datetime,
) -> None:
    if not observation["active"]:
        if observation["complete"] and existing["rule_state"] == "active":
            _clear_signal(
                connection,
                existing=existing,
                reconciliation_id=reconciliation_id,
                operation_id=operation_id,
                actor=actor,
                now=now,
                observation=observation,
            )
        elif not observation["complete"] and existing["rule_state"] == "active":
            _limit_signal(
                connection,
                existing=existing,
                reconciliation_id=reconciliation_id,
                operation_id=operation_id,
                actor=actor,
                now=now,
                status="partial",
                observation=observation,
            )
        return

    now_text = _iso(now)
    new_hash = _observation_hash(observation["observation"])
    values: dict[str, Any] = {
        "rule_version": observation["rule_version"],
        "rule_state": "active",
        "evaluation_status": "complete" if observation["complete"] else "partial",
        "severity": observation["severity"],
        "last_seen_at": now_text,
        "last_reconciliation_id": reconciliation_id,
        "observation_hash": new_hash,
        "last_evaluation_hash": new_hash,
        "observation": observation["observation"],
        "updated_at": now_text,
    }
    event_types: list[str] = []
    new_attention_state = existing["attention_state"]
    rule_version_changed = (
        observation["rule_version"] != existing["rule_version"]
    )
    if existing["rule_state"] != "active":
        event_types.append("reopened")
        if rule_version_changed:
            event_types.append("rule_changed")
        new_attention_state = "open"
        values.update(
            {
                "attention_state": "open",
                "acknowledged_at": "",
                "acknowledged_by": "",
                "snoozed_until": "",
                "snoozed_by": "",
                "resolved_at": "",
                "resolved_by": "",
                "resolution_reason": "",
            }
        )
    else:
        if rule_version_changed:
            event_types.append("rule_changed")
        elif new_hash != existing["observation_hash"]:
            event_types.append("observed_again")
        if (
            not observation["complete"]
            and existing["evaluation_status"] != "partial"
        ):
            event_types.append("evaluation_limited")
    if existing["rule_state"] == "active" and _snooze_is_expired(
        existing,
        now=now,
    ):
        event_types.append("snooze_expired")
        new_attention_state = "open"
        values.update(
            {
                "attention_state": "open",
                "snoozed_until": "",
                "snoozed_by": "",
            }
        )
    attention_repository.update_signal(connection, existing["attention_id"], values)
    for event_type in dict.fromkeys(event_types):
        _history(
            connection,
            signal=existing,
            operation_id=operation_id,
            reconciliation_id=reconciliation_id,
            event_type=event_type,
            actor=actor,
            now=now,
            new_rule_state="active",
            new_attention_state=new_attention_state,
            observation=observation["observation"],
            severity=observation["severity"],
            rule_version=observation["rule_version"],
        )


def _clear_signal(
    connection,
    *,
    existing: dict[str, Any],
    reconciliation_id: str,
    operation_id: str,
    actor: str,
    now: datetime,
    observation: dict[str, Any] | None = None,
) -> None:
    now_text = _iso(now)
    normalized = (
        observation["observation"]
        if observation
        else {
            **existing["observation"],
            "signal": {
                "state": "clear",
                "severity": "none",
                "reason_codes": ["condition_no_longer_present"],
            },
        }
    )
    if (
        observation
        and observation["rule_version"] != existing["rule_version"]
    ):
        _history(
            connection,
            signal=existing,
            operation_id=operation_id,
            reconciliation_id=reconciliation_id,
            event_type="rule_changed",
            actor=actor,
            now=now,
            new_rule_state="clear",
            new_attention_state="resolved",
            observation=normalized,
            severity=observation["severity"],
            rule_version=observation["rule_version"],
        )
    attention_repository.update_signal(
        connection,
        existing["attention_id"],
        {
            "rule_version": (
                observation["rule_version"]
                if observation
                else existing["rule_version"]
            ),
            "rule_state": "clear",
            "attention_state": "resolved",
            "evaluation_status": "complete",
            "severity": "none",
            "last_seen_at": now_text,
            "last_reconciliation_id": reconciliation_id,
            "snoozed_until": "",
            "snoozed_by": "",
            "resolved_at": now_text,
            "resolved_by": "system",
            "resolution_reason": "rule_clear",
            "observation_hash": _observation_hash(normalized),
            "last_evaluation_hash": _observation_hash(normalized),
            "observation": normalized,
            "updated_at": now_text,
        },
    )
    _history(
        connection,
        signal=existing,
        operation_id=operation_id,
        reconciliation_id=reconciliation_id,
        event_type="cleared",
        actor=actor,
        now=now,
        new_rule_state="clear",
        new_attention_state="resolved",
        observation=normalized,
        severity="none",
        rule_version=(
            observation["rule_version"]
            if observation
            else existing["rule_version"]
        ),
    )


def _limit_signal(
    connection,
    *,
    existing: dict[str, Any],
    reconciliation_id: str,
    operation_id: str,
    actor: str,
    now: datetime,
    status: str,
    observation: dict[str, Any] | None = None,
) -> None:
    status_changed = existing["evaluation_status"] != status
    observation_changed = bool(
        observation
        and _observation_hash(observation["observation"])
        != _last_evaluation_hash(existing)
    )
    values = {
        "evaluation_status": status,
        "last_reconciliation_id": reconciliation_id,
        "updated_at": _iso(now),
    }
    if observation:
        values["last_evaluation_hash"] = _observation_hash(
            observation["observation"]
        )
    attention_repository.update_signal(
        connection,
        existing["attention_id"],
        values,
    )
    if status_changed or observation_changed:
        _history(
            connection,
            signal=existing,
            operation_id=operation_id,
            reconciliation_id=reconciliation_id,
            event_type="evaluation_limited",
            actor=actor,
            now=now,
            observation=(
                observation["observation"]
                if observation
                else existing["observation"]
            ),
            rule_version=(
                observation["rule_version"]
                if observation
                else existing["rule_version"]
            ),
            severity=(
                observation["severity"]
                if observation
                else existing["severity"]
            ),
        )


def _history(
    connection,
    *,
    signal: dict[str, Any],
    operation_id: str,
    reconciliation_id: str | None,
    event_type: str,
    actor: str,
    now: datetime,
    prior_rule_state: str | None = None,
    new_rule_state: str | None = None,
    prior_attention_state: str | None = None,
    new_attention_state: str | None = None,
    observation: dict[str, Any] | None = None,
    severity: str | None = None,
    rule_version: str | None = None,
) -> None:
    attention_repository.insert_history(
        connection,
        {
            "event_id": f"attevt-{uuid4().hex}",
            "attention_id": signal["attention_id"],
            "operation_id": operation_id,
            "reconciliation_id": reconciliation_id,
            "event_type": event_type,
            "prior_rule_state": (
                signal.get("rule_state", "")
                if prior_rule_state is None
                else prior_rule_state
            ),
            "new_rule_state": (
                signal.get("rule_state", "")
                if new_rule_state is None
                else new_rule_state
            ),
            "prior_attention_state": (
                signal.get("attention_state", "")
                if prior_attention_state is None
                else prior_attention_state
            ),
            "new_attention_state": (
                signal.get("attention_state", "")
                if new_attention_state is None
                else new_attention_state
            ),
            "severity": severity if severity is not None else signal["severity"],
            "rule_version": (
                rule_version
                if rule_version is not None
                else signal["rule_version"]
            ),
            "actor": actor,
            "observation": observation or signal["observation"],
            "created_at": _iso(now),
        },
    )


def _validate_lifecycle(
    action: str,
    signal: dict[str, Any] | None,
    *,
    snoozed_until: str = "",
) -> str:
    if signal is None:
        return "ATTENTION_NOT_FOUND"
    if action == "resolve":
        if signal["attention_state"] == "resolved":
            return "ATTENTION_ALREADY_RESOLVED"
        if signal["rule_state"] != "clear":
            return "ATTENTION_STILL_ACTIVE"
        return ""
    if signal["rule_state"] != "active":
        return "ATTENTION_NOT_ACTIVE"
    if signal["attention_state"] == "resolved":
        return "ATTENTION_ALREADY_RESOLVED"
    if signal["evaluation_status"] == "disabled":
        return "ATTENTION_RULE_DISABLED"
    if (
        action == "acknowledge"
        and signal["attention_state"] == "acknowledged"
    ):
        return "ATTENTION_ALREADY_ACKNOWLEDGED"
    if (
        action == "snooze"
        and signal["attention_state"] == "snoozed"
        and signal["snoozed_until"] == snoozed_until
    ):
        return "ATTENTION_SNOOZE_UNCHANGED"
    return ""


def _target_state(action: str) -> str:
    return {
        "acknowledge": "acknowledged",
        "snooze": "snoozed",
        "resolve": "resolved",
    }[action]


def _snooze_is_expired(
    signal: dict[str, Any],
    *,
    now: datetime | None = None,
) -> bool:
    return bool(
        signal["attention_state"] == "snoozed"
        and signal["snoozed_until"]
        and _parse_timestamp(signal["snoozed_until"]) <= (now or _utc_now())
    )


def _reconciliation_scope(
    rule_keys: list[str] | None,
    subject_kind: str | None,
    subject_id: str | None,
) -> dict[str, Any]:
    normalized_keys = (
        [_bounded_id(rule_key, "rule_key") for rule_key in rule_keys]
        if rule_keys
        else None
    )
    normalized_kind = (
        _bounded_id(subject_kind, "subject_kind")
        if subject_kind is not None
        else None
    )
    if (
        normalized_kind is not None
        and normalized_kind not in set(_SUBJECT_KIND_BY_RULE.values())
    ):
        raise ValueError("Unsupported subject kind")
    if normalized_keys:
        if normalized_kind:
            expected_kinds = {_SUBJECT_KIND_BY_RULE.get(key) for key in normalized_keys}
            if expected_kinds != {normalized_kind}:
                raise ValueError("Subject kind does not match rule scope")
    normalized_subject = (
        _bounded_id(subject_id, "subject_id")
        if subject_id is not None
        else None
    )
    if normalized_subject and not normalized_kind:
        raise ValueError("Subject ID requires subject kind")
    return {
        "rule_keys": normalized_keys,
        "subject_kind": normalized_kind,
        "subject_id": normalized_subject,
    }


def _attention_id(rule_key: str, subject_kind: str, subject_id: str) -> str:
    canonical = f"{rule_key}|{subject_kind}|{subject_id}"
    return f"attn-{hashlib.sha256(canonical.encode('utf-8')).hexdigest()[:32]}"


def _observation_hash(observation: dict[str, Any]) -> str:
    semantic = {
        "rule_key": observation["rule_key"],
        "rule_version": observation["rule_version"],
        "subject": observation["subject"],
        "fact": observation["fact"],
        "signal": observation["signal"],
        "evidence": {
            key: value
            for key, value in observation["evidence"].items()
            if key not in {"snapshot_ids", "snapshot_observed_at", "latest_run_id"}
        },
        "freshness": {
            key: value
            for key, value in observation["freshness"].items()
            if key != "observed_at"
        },
    }
    normalized = json.dumps(
        semantic,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _last_evaluation_hash(signal: dict[str, Any]) -> str:
    return signal.get("last_evaluation_hash") or signal["observation_hash"]


def _bounded_id(value: str | None, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"Invalid {field}")
    candidate = value.strip()
    if not _STABLE_ID.fullmatch(candidate):
        raise ValueError(f"Invalid {field}")
    return candidate


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds")


def _parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(str(value))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _failure(code: str) -> dict[str, Any]:
    return {"status": "failed", "failure_code": code}


def _record_operation_failure(operation_id: str, failure_code: str) -> None:
    if not operation_id:
        return
    try:
        with attention_repository.attention_connection(immediate=True) as connection:
            attention_repository.fail_operation(
                connection,
                operation_id=operation_id,
                failure_code=failure_code,
                finished_at=_iso(_utc_now()),
            )
    except sqlite3.Error:
        pass
