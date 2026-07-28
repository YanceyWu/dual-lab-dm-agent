"""Approved deterministic rule catalog and candidate evaluation."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from pm_agent.database import attention as attention_repository

PENDING_DECISION_RULE = "pending_decision_attention"
ACTIVE_RULE_KEYS = (
    "project_health_attention",
    "overdue_action_attention",
    "source_freshness_attention",
    "resource_overload_attention",
)
ALL_RULE_KEYS = (*ACTIVE_RULE_KEYS, PENDING_DECISION_RULE)
RULE_DEFINITIONS: dict[str, dict[str, Any]] = {
    "project_health_attention": {
        "version": "project-health-attention-v1",
        "enabled": True,
        "parameters": {"health_states": ["red", "amber"]},
    },
    "overdue_action_attention": {
        "version": "overdue-action-attention-v1",
        "enabled": True,
        "parameters": {"status": "open", "due_before": "today"},
    },
    "source_freshness_attention": {
        "version": "source-freshness-attention-v1",
        "enabled": True,
        "parameters": {"required_sources": "management_attention"},
    },
    "resource_overload_attention": {
        "version": "resource-overload-attention-v1",
        "enabled": True,
        "parameters": {"active_assignment_load_strictly_greater_than": 1.0},
    },
    PENDING_DECISION_RULE: {
        "version": "pending-decision-attention-disabled-v1",
        "enabled": False,
        "parameters": {"governance_definition": "not_approved"},
    },
}


class InvalidAttentionCatalog(ValueError):
    """The persisted rule catalog differs from the approved Batch B contract."""


def evaluate(
    connection,
    *,
    rule_keys: list[str] | None = None,
    subject_kind: str | None = None,
    subject_id: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    timestamp = now or datetime.now(timezone.utc)
    catalog = _validated_catalog(attention_repository.load_rules(connection))
    selected_keys = rule_keys or list(ACTIVE_RULE_KEYS)
    _validate_requested_keys(selected_keys)

    source_evaluation = _evaluate_sources(connection, catalog, timestamp)
    source_states = {
        item["subject_id"]: item["observation"]["freshness"]["state"]
        for item in source_evaluation["observations"]
    }
    evaluations = {
        "project_health_attention": _evaluate_projects(
            connection,
            catalog,
            source_states,
        ),
        "overdue_action_attention": _evaluate_actions(
            connection,
            catalog,
            timestamp.date(),
        ),
        "source_freshness_attention": source_evaluation,
        "resource_overload_attention": _evaluate_resources(connection, catalog),
    }

    observations: list[dict[str, Any]] = []
    warning_codes: list[str] = []
    rule_status: dict[str, str] = {}
    disabled_rule_keys: list[str] = []
    for rule_key in selected_keys:
        if rule_key == PENDING_DECISION_RULE:
            disabled_rule_keys.append(rule_key)
            rule_status[rule_key] = "disabled"
            continue
        definition = catalog[rule_key]
        if not definition["enabled"]:
            disabled_rule_keys.append(rule_key)
            rule_status[rule_key] = "disabled"
            continue
        evaluation = evaluations[rule_key]
        scoped = [
            item
            for item in evaluation["observations"]
            if (not subject_kind or item["subject_kind"] == subject_kind)
            and (not subject_id or item["subject_id"] == subject_id)
        ]
        observations.extend(scoped)
        warning_codes.extend(evaluation["warning_codes"])
        rule_status[rule_key] = evaluation["status"]

    return {
        "observations": observations,
        "warning_codes": sorted(set(warning_codes)),
        "rule_status": rule_status,
        "disabled_rule_keys": disabled_rule_keys,
        "rule_set_version": _rule_set_version(catalog),
    }


def _validated_catalog(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    catalog = {row["rule_key"]: row for row in rows}
    if set(catalog) != set(ALL_RULE_KEYS):
        raise InvalidAttentionCatalog("ATTENTION_RULE_CATALOG_INVALID")
    for rule_key, expected in RULE_DEFINITIONS.items():
        actual = catalog[rule_key]
        if (
            actual["rule_version"] != expected["version"]
            or actual["parameters"] != expected["parameters"]
        ):
            raise InvalidAttentionCatalog("ATTENTION_RULE_CATALOG_INVALID")
        if rule_key == PENDING_DECISION_RULE and actual["enabled"]:
            raise InvalidAttentionCatalog("ATTENTION_PENDING_DECISION_FORBIDDEN")
    return catalog


def _validate_requested_keys(rule_keys: list[str]) -> None:
    if not rule_keys or len(rule_keys) > len(ALL_RULE_KEYS):
        raise InvalidAttentionCatalog("ATTENTION_SCOPE_INVALID")
    if len(set(rule_keys)) != len(rule_keys) or set(rule_keys) - set(ALL_RULE_KEYS):
        raise InvalidAttentionCatalog("ATTENTION_SCOPE_INVALID")


def _evaluate_projects(
    connection,
    catalog: dict[str, dict[str, Any]],
    source_states: dict[str, str],
) -> dict[str, Any]:
    rule_key = "project_health_attention"
    version = catalog[rule_key]["rule_version"]
    observations = []
    limited = False
    for project in attention_repository.load_project_health_inputs(connection):
        boards = project["boards"]
        grades = {
            str(board.get("overall_grade") or "").upper()
            for board in boards
            if board.get("overall_grade")
        }
        rags = {
            str(board.get("rag_status") or "").upper()
            for board in boards
            if board.get("rag_status")
        }
        if "RED" in grades or "RED" in rags:
            health_state = "red"
        elif {"YELLOW", "AMBER"} & (grades | rags):
            health_state = "amber"
        elif grades or rags:
            health_state = "clear"
        else:
            health_state = "unknown"

        required_source_ids = [
            "confluence-status-batch",
            *(f"jira-health-{board['board_id']}" for board in boards),
        ]
        sources_complete = bool(boards) and all(
            source_states.get(source_id) == "fresh"
            for source_id in required_source_ids
        )
        observations_complete = bool(boards) and all(
            board.get("overall_grade") or board.get("rag_status")
            for board in boards
        )
        complete = sources_complete and observations_complete
        limited = limited or not complete
        if health_state == "unknown":
            continue
        active = health_state in {"red", "amber"}
        observations.append(
            _observation(
                rule_key=rule_key,
                rule_version=version,
                subject_kind="project",
                subject_id=project["project_id"],
                active=active,
                complete=complete,
                severity=(
                    "critical" if health_state == "red"
                    else "high" if health_state == "amber"
                    else "none"
                ),
                reason_codes=(
                    [f"project_health_{health_state}"]
                    if active
                    else ["project_health_clear"]
                ),
                fact_type="project_health_state",
                fact_value=health_state,
                value_state="known",
                evidence={
                    "entity_kind": "project_health_snapshots",
                    "board_ids": [board["board_id"] for board in boards],
                    "snapshot_ids": sorted(
                        str(snapshot_id)
                        for board in boards
                        for snapshot_id in (
                            board.get("health_snapshot_id"),
                            board.get("status_snapshot_id"),
                        )
                        if snapshot_id is not None
                    ),
                    "snapshot_observed_at": sorted(
                        str(snapshot_date)
                        for board in boards
                        for snapshot_date in (
                            board.get("health_snapshot_date"),
                            board.get("status_snapshot_date"),
                        )
                        if snapshot_date
                    ),
                },
                freshness={
                    "source_ids": required_source_ids,
                    "states": {
                        source_id: source_states.get(source_id, "unknown")
                        for source_id in required_source_ids
                    },
                },
            )
        )
    return {
        "status": "partial" if limited else "complete",
        "warning_codes": ["ATTENTION_PROJECT_INPUT_LIMITED"] if limited else [],
        "observations": observations,
    }


def _evaluate_actions(
    connection,
    catalog: dict[str, dict[str, Any]],
    today: date,
) -> dict[str, Any]:
    rule_key = "overdue_action_attention"
    version = catalog[rule_key]["rule_version"]
    observations = []
    for action in attention_repository.load_action_inputs(connection):
        due_date = _parse_date(action.get("due_date"))
        active = (
            action.get("status") == "open"
            and due_date is not None
            and due_date < today
        )
        observations.append(
            _observation(
                rule_key=rule_key,
                rule_version=version,
                subject_kind="action",
                subject_id=str(action["id"]),
                active=active,
                complete=True,
                severity=(
                    "high"
                    if active and action.get("priority") == "high"
                    else "medium" if active
                    else "none"
                ),
                reason_codes=["action_overdue"] if active else ["action_not_overdue"],
                fact_type="action_due_state",
                fact_value="overdue" if active else "clear",
                value_state="known",
                evidence={
                    "entity_kind": "action_items",
                    "record_id": str(action["id"]),
                    "due_date": action.get("due_date") or "",
                    "priority": action.get("priority") or "",
                    "status": action.get("status") or "",
                },
                freshness={"state": "fresh", "basis": "local_record"},
            )
        )
    return {"status": "complete", "warning_codes": [], "observations": observations}


def _evaluate_sources(
    connection,
    catalog: dict[str, dict[str, Any]],
    now: datetime,
) -> dict[str, Any]:
    rule_key = "source_freshness_attention"
    version = catalog[rule_key]["rule_version"]
    rows = {
        row["id"]: row
        for row in attention_repository.load_source_inputs(connection)
    }
    observations = []
    limited = False
    for source_id in attention_repository.load_expected_source_ids(connection):
        row = rows.get(source_id)
        state = _freshness_state(row, now)
        active = state != "fresh"
        limited = limited or active
        observations.append(
            _observation(
                rule_key=rule_key,
                rule_version=version,
                subject_kind="source",
                subject_id=source_id,
                active=active,
                complete=True,
                severity=(
                    "high"
                    if state in {"stale", "unavailable"}
                    else "medium" if active
                    else "none"
                ),
                reason_codes=[f"source_{state}"],
                fact_type="source_freshness_state",
                fact_value=None if state in {"unknown", "unavailable"} else state,
                value_state=state if state in {"unknown", "unavailable"} else "known",
                evidence={
                    "entity_kind": "data_sources_sync_runs",
                    "record_count": int(row is not None),
                    "latest_run_id": (row or {}).get("latest_run_id") or "",
                },
                freshness={"state": state, "source_id": source_id},
            )
        )
        observations[-1]["observation"]["freshness"]["observed_at"] = (
            (row or {}).get("latest_finished_at")
            or (row or {}).get("latest_started_at")
            or None
        )
    return {
        "status": "partial" if limited else "complete",
        "warning_codes": ["ATTENTION_SOURCE_NOT_FRESH"] if limited else [],
        "observations": observations,
    }


def _evaluate_resources(
    connection,
    catalog: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    rule_key = "resource_overload_attention"
    version = catalog[rule_key]["rule_version"]
    observations = []
    for member in attention_repository.load_member_inputs(connection):
        current_load = float(member.get("current_load") or 0.0)
        active = current_load > 1.0
        observations.append(
            _observation(
                rule_key=rule_key,
                rule_version=version,
                subject_kind="member",
                subject_id=str(member["id"]),
                active=active,
                complete=True,
                severity="high" if active else "none",
                reason_codes=["resource_load_above_100"] if active else ["resource_load_not_above_100"],
                fact_type="active_assignment_load",
                fact_value=current_load,
                value_state="known",
                evidence={
                    "entity_kind": "active_assignments",
                    "active_project_count": int(member.get("active_projects") or 0),
                },
                freshness={"state": "fresh", "basis": "local_record"},
            )
        )
    return {"status": "complete", "warning_codes": [], "observations": observations}


def _observation(
    *,
    rule_key: str,
    rule_version: str,
    subject_kind: str,
    subject_id: str,
    active: bool,
    complete: bool,
    severity: str,
    reason_codes: list[str],
    fact_type: str,
    fact_value: Any,
    value_state: str,
    evidence: dict[str, Any],
    freshness: dict[str, Any],
) -> dict[str, Any]:
    return {
        "rule_key": rule_key,
        "rule_version": rule_version,
        "subject_kind": subject_kind,
        "subject_id": subject_id,
        "active": active,
        "complete": complete,
        "severity": severity,
        "observation": {
            "rule_key": rule_key,
            "rule_version": rule_version,
            "subject": {"kind": subject_kind, "id": subject_id},
            "fact": {
                "fact_type": fact_type,
                "value": fact_value,
                "value_state": value_state,
            },
            "signal": {
                "state": "active" if active else "clear",
                "severity": severity,
                "reason_codes": reason_codes,
            },
            "evidence": evidence,
            "freshness": freshness,
        },
    }


def _freshness_state(row: dict[str, Any] | None, now: datetime) -> str:
    if not row or not row.get("active"):
        return "unknown"
    timestamp_text = row.get("latest_finished_at") or row.get("latest_started_at") or ""
    if not timestamp_text:
        return "unknown"
    latest_status = row.get("latest_status") or ""
    if latest_status == "failed":
        return "unavailable"
    if latest_status in {"partial", "running"}:
        return "partial"
    try:
        observed_at = datetime.fromisoformat(str(timestamp_text))
        if observed_at.tzinfo is None:
            observed_at = observed_at.replace(tzinfo=timezone.utc)
        age_hours = (now - observed_at).total_seconds() / 3600
    except (TypeError, ValueError):
        return "unknown"
    if age_hours > float(row.get("refresh_sla_hours") or 0):
        return "stale"
    return "fresh"


def _parse_date(value: Any) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None


def _rule_set_version(catalog: dict[str, dict[str, Any]]) -> str:
    return "|".join(
        f"{key}:{catalog[key]['rule_version']}:{int(catalog[key]['enabled'])}"
        for key in sorted(catalog)
    )
