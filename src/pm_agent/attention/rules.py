"""Approved deterministic rule catalog and candidate evaluation."""

from __future__ import annotations

import json
import re
from datetime import date, datetime, timezone
from typing import Any

from pm_agent.database import attention as attention_repository

PENDING_DECISION_RULE = "pending_decision_attention"
CRITICAL_MILESTONE_RULE = "critical_milestone_overdue_attention"
ACTIVE_RULE_KEYS = (
    "project_health_attention",
    "overdue_action_attention",
    "source_freshness_attention",
    "resource_overload_attention",
    CRITICAL_MILESTONE_RULE,
)
ALL_RULE_KEYS = (*ACTIVE_RULE_KEYS, PENDING_DECISION_RULE)
PROJECT_HEALTH_RULE = "project_health_attention"
PROJECT_HEALTH_VERSION = re.compile(r"^project-health-attention-v[1-9][0-9]*$")
RAG_SOURCE_KEYS = ("jira_grade", "confluence_rag")
RAG_MAPPING_KEYS = {
    "jira_grade": "jira_grade_mapping",
    "confluence_rag": "confluence_rag_mapping",
}
RAG_STATES = {"red", "amber", "clear"}
MAX_RAG_LABELS = 50
MAX_PROJECT_OVERRIDES = 100
_STABLE_PROJECT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
RULE_DEFINITIONS: dict[str, dict[str, Any]] = {
    PROJECT_HEALTH_RULE: {
        "version": "project-health-attention-v2",
        "enabled": True,
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
    CRITICAL_MILESTONE_RULE: {
        "version": "critical-milestone-overdue-attention-v1",
        "enabled": True,
        "parameters": {"criticality": "critical", "adherence": "overdue"},
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
    enabled_selected_keys = {
        rule_key
        for rule_key in selected_keys
        if rule_key != PENDING_DECISION_RULE
        and catalog[rule_key]["enabled"]
    }

    evaluations: dict[str, dict[str, Any]] = {}
    source_evaluation: dict[str, Any] | None = None
    if {
        PROJECT_HEALTH_RULE,
        "source_freshness_attention",
    } & enabled_selected_keys:
        source_evaluation = _evaluate_sources(connection, catalog, timestamp)
    if PROJECT_HEALTH_RULE in enabled_selected_keys:
        source_states = {
            item["subject_id"]: item["observation"]["freshness"]["state"]
            for item in source_evaluation["observations"]
        }
        evaluations[PROJECT_HEALTH_RULE] = _evaluate_projects(
            connection,
            catalog,
            source_states,
        )
    if "overdue_action_attention" in enabled_selected_keys:
        evaluations["overdue_action_attention"] = _evaluate_actions(
            connection,
            catalog,
            timestamp.date(),
        )
    if "source_freshness_attention" in enabled_selected_keys:
        evaluations["source_freshness_attention"] = source_evaluation
    if "resource_overload_attention" in enabled_selected_keys:
        evaluations["resource_overload_attention"] = _evaluate_resources(
            connection,
            catalog,
        )
    if CRITICAL_MILESTONE_RULE in enabled_selected_keys:
        evaluations[CRITICAL_MILESTONE_RULE] = _evaluate_critical_milestones(connection, catalog)

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
        if rule_key == PROJECT_HEALTH_RULE:
            if not PROJECT_HEALTH_VERSION.fullmatch(actual["rule_version"]):
                raise InvalidAttentionCatalog("ATTENTION_RULE_CATALOG_INVALID")
            validate_project_health_parameters(actual["parameters"])
        elif (
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


def validate_project_health_parameters(parameters: Any) -> None:
    """Validate the complete persisted project-health RAG configuration."""
    if not isinstance(parameters, dict) or set(parameters) != {
        "config_version",
        "default",
        "project_overrides",
    }:
        raise InvalidAttentionCatalog("ATTENTION_RAG_CONFIG_INVALID")
    if parameters["config_version"] != "1.0":
        raise InvalidAttentionCatalog("ATTENTION_RAG_CONFIG_INVALID")
    _validate_rag_definition(parameters["default"], require_mappings=True)
    overrides = parameters["project_overrides"]
    if (
        not isinstance(overrides, dict)
        or len(overrides) > MAX_PROJECT_OVERRIDES
    ):
        raise InvalidAttentionCatalog("ATTENTION_RAG_CONFIG_INVALID")
    for project_id, definition in overrides.items():
        if not isinstance(project_id, str) or not _STABLE_PROJECT_ID.fullmatch(
            project_id
        ):
            raise InvalidAttentionCatalog("ATTENTION_RAG_CONFIG_INVALID")
        _validate_rag_definition(definition, require_mappings=False)


def _validate_rag_definition(
    definition: Any,
    *,
    require_mappings: bool,
) -> None:
    allowed_keys = {
        "source_precedence",
        "state_precedence",
        "jira_grade_mapping",
        "confluence_rag_mapping",
    }
    if not isinstance(definition, dict) or not set(definition) <= allowed_keys:
        raise InvalidAttentionCatalog("ATTENTION_RAG_CONFIG_INVALID")
    required_keys = allowed_keys if require_mappings else set()
    if not required_keys <= set(definition):
        raise InvalidAttentionCatalog("ATTENTION_RAG_CONFIG_INVALID")
    if "source_precedence" in definition:
        source_precedence = definition["source_precedence"]
        if (
            not isinstance(source_precedence, list)
            or not source_precedence
            or not all(isinstance(item, str) for item in source_precedence)
            or len(source_precedence) != len(set(source_precedence))
            or set(source_precedence) - set(RAG_SOURCE_KEYS)
        ):
            raise InvalidAttentionCatalog("ATTENTION_RAG_CONFIG_INVALID")
    if "state_precedence" in definition:
        state_precedence = definition["state_precedence"]
        if (
            not isinstance(state_precedence, list)
            or not all(isinstance(item, str) for item in state_precedence)
            or set(state_precedence) != {"red", "amber"}
            or len(state_precedence) != 2
        ):
            raise InvalidAttentionCatalog("ATTENTION_RAG_CONFIG_INVALID")
    for mapping_key in RAG_MAPPING_KEYS.values():
        if mapping_key not in definition:
            continue
        mapping = definition[mapping_key]
        if (
            not isinstance(mapping, dict)
            or not mapping
            or len(mapping) > MAX_RAG_LABELS
        ):
            raise InvalidAttentionCatalog("ATTENTION_RAG_CONFIG_INVALID")
        for label, state in mapping.items():
            if (
                not isinstance(label, str)
                or not label
                or len(label) > 64
                or label != label.strip().upper()
                or not isinstance(state, str)
                or state not in RAG_STATES
            ):
                raise InvalidAttentionCatalog("ATTENTION_RAG_CONFIG_INVALID")


def _project_health_definition(
    parameters: dict[str, Any],
    project_id: str,
) -> dict[str, Any]:
    default = parameters["default"]
    override = parameters["project_overrides"].get(project_id, {})
    result = {
        "source_precedence": list(
            override.get(
                "source_precedence",
                default["source_precedence"],
            )
        ),
        "state_precedence": list(
            override.get(
                "state_precedence",
                default["state_precedence"],
            )
        ),
    }
    for mapping_key in RAG_MAPPING_KEYS.values():
        merged = dict(default[mapping_key])
        merged.update(override.get(mapping_key, {}))
        result[mapping_key] = merged
    return result


def _configured_project_state(
    boards: list[dict[str, Any]],
    definition: dict[str, Any],
) -> tuple[str, bool]:
    if not boards:
        return "unknown", False
    mapped_by_source: dict[str, list[str]] = {
        source_key: [] for source_key in definition["source_precedence"]
    }
    all_boards_complete = True
    for board in boards:
        board_sources_complete = True
        source_values = {
            "jira_grade": board.get("overall_grade"),
            "confluence_rag": board.get("rag_status"),
        }
        for source_key in definition["source_precedence"]:
            raw_value = source_values[source_key]
            if raw_value in (None, ""):
                board_sources_complete = False
                continue
            label = str(raw_value).strip().upper()
            state = definition[RAG_MAPPING_KEYS[source_key]].get(label)
            if state is None:
                board_sources_complete = False
                continue
            mapped_by_source[source_key].append(state)
        all_boards_complete = (
            all_boards_complete
            and board_sources_complete
        )

    for source_key in definition["source_precedence"]:
        states = set(mapped_by_source[source_key])
        for state in definition["state_precedence"]:
            if state in states:
                return state, all_boards_complete
    if all_boards_complete:
        return "clear", True
    return "unknown", False


def _project_required_source_ids(
    boards: list[dict[str, Any]],
    definition: dict[str, Any],
) -> list[str]:
    source_ids: list[str] = []
    if "confluence_rag" in definition["source_precedence"]:
        source_ids.append("confluence-status-batch")
    if "jira_grade" in definition["source_precedence"]:
        source_ids.extend(
            f"jira-health-{board['board_id']}"
            for board in boards
        )
    return source_ids


def _evaluate_projects(
    connection,
    catalog: dict[str, dict[str, Any]],
    source_states: dict[str, str],
) -> dict[str, Any]:
    rule_key = PROJECT_HEALTH_RULE
    version = catalog[rule_key]["rule_version"]
    observations = []
    limited = False
    for project in attention_repository.load_project_health_inputs(connection):
        boards = project["boards"]
        definition = _project_health_definition(
            catalog[rule_key]["parameters"],
            project["project_id"],
        )
        health_state, observations_complete = _configured_project_state(
            boards,
            definition,
        )
        required_source_ids = _project_required_source_ids(boards, definition)
        sources_complete = bool(boards) and all(
            source_states.get(source_id) == "fresh"
            for source_id in required_source_ids
        )
        complete = sources_complete and observations_complete
        limited = limited or not complete
        active = health_state in {"red", "amber"}
        if health_state == "unknown":
            reason_codes = ["project_health_unknown"]
            fact_value: object | None = None
            value_state = "unknown"
        elif active:
            reason_codes = [f"project_health_{health_state}"]
            fact_value = health_state
            value_state = "known"
        else:
            reason_codes = ["project_health_clear"]
            fact_value = health_state
            value_state = "known"
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
                reason_codes=reason_codes,
                fact_type="project_health_state",
                fact_value=fact_value,
                value_state=value_state,
                evidence={
                    "entity_kind": "project_health_snapshots",
                    "definition_source_precedence": definition[
                        "source_precedence"
                    ],
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
    limited = False
    for action in attention_repository.load_action_inputs(connection):
        due_date = _parse_date(action.get("due_date"))
        status = str(action.get("status") or "").strip().lower()
        complete = True
        if status == "open" and due_date is not None:
            active = due_date < today
            fact_value: object | None = "overdue" if active else "clear"
            value_state = "known"
            reason_codes = ["action_overdue"] if active else ["action_not_overdue"]
        elif status in {"done", "cancelled"}:
            active = False
            fact_value = "clear"
            value_state = "known"
            reason_codes = [f"action_{status}"]
        else:
            active = False
            complete = False
            limited = True
            fact_value = None
            value_state = "unknown"
            reason_codes = ["action_due_state_unknown"]
        observations.append(
            _observation(
                rule_key=rule_key,
                rule_version=version,
                subject_kind="action",
                subject_id=str(action["id"]),
                active=active,
                complete=complete,
                severity=(
                    "high"
                    if active and action.get("priority") == "high"
                    else "medium" if active
                    else "none"
                ),
                reason_codes=reason_codes,
                fact_type="action_due_state",
                fact_value=fact_value,
                value_state=value_state,
                evidence={
                    "entity_kind": "action_items",
                    "record_id": str(action["id"]),
                    "due_date": due_date.isoformat() if due_date else "",
                    "priority": action.get("priority") or "",
                    "status": status if status in {"open", "done", "cancelled"} else "invalid",
                },
                freshness={"state": "fresh", "basis": "local_record"},
            )
        )
    return {
        "status": "partial" if limited else "complete",
        "warning_codes": ["ATTENTION_ACTION_INPUT_LIMITED"] if limited else [],
        "observations": observations,
    }


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
    inputs = attention_repository.load_member_inputs(connection)
    if inputs["state"] != "known":
        return {
            "status": "partial",
            "warning_codes": ["ATTENTION_RESOURCE_INPUT_LIMITED"],
            "observations": [],
        }
    observations = []
    for member in inputs["members"]:
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
                fact_type="current_state_staffing_load",
                fact_value=current_load,
                value_state="known",
                evidence={
                    "entity_kind": "current_state_staffing_assignments",
                    "active_project_count": int(member.get("active_projects") or 0),
                },
                freshness={"state": "fresh", "basis": "local_record"},
            )
        )
    return {"status": "complete", "warning_codes": [], "observations": observations}


def _evaluate_critical_milestones(
    connection,
    catalog: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    rule_key = CRITICAL_MILESTONE_RULE
    version = catalog[rule_key]["rule_version"]
    rows = connection.execute(
        """
        SELECT f.subject_id, f.value_json, f.value_state, f.freshness_state,
               dr.completeness_state, dr.derivation_run_id, m.criticality
        FROM execution_facts f
        JOIN execution_derivation_runs dr
          ON dr.derivation_run_id = f.derivation_run_id
        JOIN execution_milestones m ON m.milestone_id=f.subject_id
        WHERE f.fact_key = 'milestone_adherence'
          AND f.subject_kind = 'milestone'
          AND NOT EXISTS (
              SELECT 1 FROM execution_derivation_runs later
              WHERE later.project_id = dr.project_id
                AND later.board_id = dr.board_id
                AND later.finished_at > dr.finished_at
          )
        """
    ).fetchall()
    observations = []
    limited = False
    for row in rows:
        complete = (
            row["completeness_state"] == "complete"
            and row["freshness_state"] == "fresh"
        )
        limited = limited or not complete
        fact_value = json.loads(row["value_json"]) if row["value_state"] == "known" else None
        active = (
            complete
            and row["criticality"] == "critical"
            and fact_value == "overdue"
        )
        observations.append(
            _observation(
                rule_key=rule_key,
                rule_version=version,
                subject_kind="milestone",
                subject_id=row["subject_id"],
                active=active,
                complete=complete,
                severity="critical" if active else "none",
                reason_codes=(
                    ["critical_milestone_overdue"]
                    if active else ["milestone_not_critical_overdue"]
                ),
                fact_type="milestone_adherence",
                fact_value=fact_value,
                value_state=row["value_state"],
                evidence={
                    "entity_kind": "execution_derivation",
                    "derivation_run_id": row["derivation_run_id"],
                    "criticality": row["criticality"],
                },
                freshness={"state": row["freshness_state"]},
            )
        )
    return {
        "status": "partial" if limited else "complete",
        "warning_codes": ["ATTENTION_MILESTONE_INPUT_LIMITED"] if limited else [],
        "observations": observations,
    }


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
