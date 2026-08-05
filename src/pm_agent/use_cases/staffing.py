"""Period-aware staffing read, feasibility, proposal, and confirmation services."""

from __future__ import annotations

from calendar import monthrange
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from typing import Any, Literal
from uuid import uuid4
import secrets

from pydantic import BaseModel, Field

from pm_agent.database import repository, staffing_capacity
from pm_agent.resource_intelligence.read_model import get_effective_capacity
from pm_agent.rules.hiref import project_alignment_status

RULE_VERSION = "staffing-feasibility-v2"
CAPACITY_RULE_VERSION = "staffing-effective-capacity-v1"
STAFFING_SOURCE_IDS = (
    "import-hiref-report",
)
CURRENT_STATE_PUBLICATION_SOURCE_ID = "current-state-staffing-publication"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


class StaffingDemand(BaseModel):
    project_id: str
    start_period: str
    end_period: str
    effort: float = Field(gt=0)
    role: str = ""
    minimum_allocation: float = Field(default=0.1, gt=0, le=1)
    maximum_people: int = Field(default=1, ge=1)
    splittable: bool = True
    priority: str = "medium"
    plan_version_id: str | None = None
    rule_version: Literal["staffing-feasibility-v2"] = RULE_VERSION


def _periods(start: str, end: str) -> list[dict[str, int]]:
    start_year, start_month = map(int, start.split("-"))
    end_year, end_month = map(int, end.split("-"))
    if (end_year, end_month) < (start_year, start_month):
        raise ValueError("end_period must not precede start_period")
    result = []
    year, month = start_year, start_month
    while (year, month) <= (end_year, end_month):
        result.append({"year": year, "month": month})
        month += 1
        if month == 13:
            year, month = year + 1, 1
    return result


def staffing_read_model(demand: StaffingDemand) -> dict[str, Any]:
    periods = _periods(demand.start_period, demand.end_period)
    target_project = repository.get_project(demand.project_id)
    snapshots: dict[str, list[dict]] = {}
    selected_plans: list[dict | None] = []
    for period in periods:
        facts, selected_plan = repository.get_staffing_facts(
            period["year"], period["month"], demand.plan_version_id
        )
        snapshots[f"{period['year']}-{period['month']:02d}"] = facts
        selected_plans.append(selected_plan)
    members: dict[str, dict] = {}
    for period_key, facts in snapshots.items():
        for fact in facts:
            member = members.setdefault(
                fact["id"],
                {
                    "member_id": fact["id"], "name": fact["name"],
                    "role": fact.get("role") or "",
                    "resource_type": fact.get("resource_type", ""), "periods": {},
                },
            )
            member["periods"][period_key] = {
                "load": fact["month_load"],
                "contract": fact["contract"],
                "next_contract": fact["next_contract"],
                "status": fact["status"],
            }
    plan_ids = {
        str(plan["plan_version_id"])
        for plan in selected_plans
        if plan and plan.get("plan_version_id")
    }
    plan_errors = []
    if not plan_ids:
        plan_errors.append(
            "requested_plan_version_not_found"
            if demand.plan_version_id
            else "active_plan_version_not_found"
        )
    elif len(plan_ids) != 1:
        plan_errors.append("inconsistent_plan_version")
    plan_version = next(
        (plan for plan in selected_plans if plan and plan.get("plan_version_id")),
        None,
    )
    if plan_version and plan_version.get("version_status") == "archived":
        plan_errors.append("plan_version_not_writable")
    requires_capacity = staffing_capacity.capacity_required()
    if requires_capacity and plan_version:
        plan_id = str(plan_version["plan_version_id"])
        for member in members.values():
            for period_key, state in member["periods"].items():
                year, month = map(int, period_key.split("-"))
                state["capacity"] = get_effective_capacity(
                    member["member_id"], year, month, plan_id
                )
    return {
        "periods": periods,
        "target_project": target_project,
        "plan_version": plan_version,
        "plan_errors": plan_errors,
        "members": list(members.values()),
        "missing_period_members": [member["member_id"] for member in members.values() if len(member["periods"]) != len(periods)],
        "capacity_required": requires_capacity,
    }


def assess_feasibility(demand: StaffingDemand) -> dict[str, Any]:
    model = staffing_read_model(demand)
    source_states = _source_states()
    candidates = []
    for member in model["members"]:
        reasons = []
        hiref_context = _hiref_context(
            member,
            model["periods"],
            model["target_project"],
        )
        if any(state["status"] != "active" for state in member["periods"].values()):
            reasons.append("member_not_active")
        capacity_evidence = []
        if model["capacity_required"]:
            expected_periods = [
                f"{period['year']}-{period['month']:02d}"
                for period in model["periods"]
            ]
            for period in expected_periods:
                state = member["periods"].get(period, {})
                capacity = state.get("capacity") or {}
                live_load = state.get("load")
                effective = capacity.get("effective_capacity")
                capacity_evidence.append({
                    "period": period,
                    "state": capacity.get("state", "unknown"),
                    "state_reason": capacity.get(
                        "state_reason", "current_capacity_derivation_not_found"
                    ),
                    "derivation_id": capacity.get("derivation_id"),
                    "publication_id": capacity.get("publication_id"),
                    "plan_version_id": capacity.get("plan_version_id"),
                    "derivation_rule_version": capacity.get("derivation_rule_version"),
                    "effective_capacity": capacity.get("effective_capacity"),
                    "planned_project_allocation": capacity.get(
                        "planned_project_allocation"
                    ),
                    "available_capacity": capacity.get("available_capacity"),
                    "current_planned_allocation": live_load,
                    "staffing_available_capacity": (
                        round(max(0.0, float(effective) - float(live_load)), 6)
                        if capacity.get("state") == "known" and live_load is not None
                        else None
                    ),
                })
            capacity_usable = True
            if any(item["state"] != "known" for item in capacity_evidence):
                reasons.append("effective_capacity_not_known")
                capacity_usable = False
            available = (
                min(
                    float(item["staffing_available_capacity"])
                    for item in capacity_evidence
                )
                if capacity_evidence and capacity_usable
                else 0.0
            )
        else:
            available = round(
                min(1.0 - float(state["load"]) for state in member["periods"].values()),
                6,
            ) if member["periods"] else 0.0
        if available < demand.minimum_allocation and not any(
            reason == "effective_capacity_not_known"
            for reason in reasons
        ):
            reasons.append("insufficient_capacity")
        candidates.append({
            **member,
            "available_allocation": round(max(0.0, available), 2),
            "reasons": reasons,
            "capacity_evidence": capacity_evidence,
            "monthly_context": [
                {
                    "period": period,
                    "current_load": state["load"],
                    "available_allocation": round(
                        max(
                            0.0,
                            max(
                                0.0,
                                float((state.get("capacity") or {}).get("effective_capacity"))
                                - float(state["load"]),
                            )
                            if model["capacity_required"]
                            and (state.get("capacity") or {}).get("state") == "known"
                            else 0.0
                            if model["capacity_required"]
                            else 1.0 - float(state["load"]),
                        ),
                        2,
                    ),
                    **(
                        {
                            "capacity": next(
                                (
                                    item
                                    for item in capacity_evidence
                                    if item["period"] == period
                                ),
                                None,
                            )
                        }
                        if model["capacity_required"]
                        else {}
                    ),
                }
                for period, state in sorted(member["periods"].items())
            ],
            "role_reference": {
                "requested_role": demand.role,
                "member_role": member.get("role", ""),
                "policy": "reference_only",
                "affects_eligibility": False,
                "affects_ranking": False,
            },
            "hiref_context": hiref_context,
        })
    eligible = sorted(
        [item for item in candidates if not item["reasons"]],
        key=lambda item: (
            0 if item["hiref_context"]["status"] in {"covered", "not_required"} else 1,
            -item["available_allocation"],
            item["member_id"],
        ),
    )
    remaining = demand.effort
    selections = []
    for candidate in eligible[:demand.maximum_people]:
        allocation = min(candidate["available_allocation"], remaining)
        if allocation >= demand.minimum_allocation:
            selections.append({"member_id": candidate["member_id"], "name": candidate["name"], "allocation": round(allocation, 2)})
            remaining = round(remaining - allocation, 6)
        if remaining <= 0:
            break
        if not demand.splittable:
            selections = []
            remaining = demand.effort
            break
    safety_blockers = [
        {
            "code": "source_not_fresh",
            "source_id": item["source_id"],
            "state": item["state"],
            "state_reason": item.get("state_reason"),
            "overrideable": item.get("overrideable", True),
        }
        for item in source_states
        if item["state"] != "fresh"
    ]
    safety_blockers.extend({"code": error} for error in model["plan_errors"])
    if model["target_project"] is None:
        safety_blockers.append({"code": "target_project_not_found"})
    selected_member_ids = {item["member_id"] for item in selections}
    decision_conditions = [
        {
            "code": "hiref_action_required",
            "member_id": candidate["member_id"],
            "hiref_status": candidate["hiref_context"]["status"],
            "recommended_action": candidate["hiref_context"]["recommended_action"],
        }
        for candidate in candidates
        if candidate["member_id"] in selected_member_ids
        and candidate["hiref_context"]["status"] not in {"covered", "not_required"}
    ]
    result = {
        "feasible": remaining <= 0,
        "decision_ready": (
            remaining <= 0
            and not safety_blockers
            and not decision_conditions
        ),
        "demand": demand.model_dump(),
        "periods": model["periods"],
        "plan_version_id": (model["plan_version"] or {}).get("plan_version_id"),
        "project_context": _project_context(model["target_project"]),
        "selections": selections,
        "unmet_effort": round(max(0.0, remaining), 2),
        "candidates": [
            {
                key: item[key]
                for key in (
                    "member_id",
                    "name",
                    "role",
                    "role_reference",
                    "hiref_context",
                    "monthly_context",
                    "available_allocation",
                    "capacity_evidence",
                    "reasons",
                )
            }
            for item in candidates
        ],
        "unknowns": model["missing_period_members"],
        "source_states": source_states,
        "safety_blockers": safety_blockers,
        "decision_conditions": decision_conditions,
        "role_policy": {
            "mode": "reference_only",
            "statement": (
                "Recorded and requested roles are context for manager review; "
                "they do not exclude or rank candidates."
            ),
        },
        "capacity_policy": {
            "required": model["capacity_required"],
            "policy_version": "staffing-capacity-policy-v1",
        },
        "rule_version": (
            CAPACITY_RULE_VERSION if model["capacity_required"] else demand.rule_version
        ),
    }
    result["decision_fingerprint"] = _decision_fingerprint(result)
    return result


def _source_states() -> list[dict[str, Any]]:
    rows = {row["id"]: row for row in repository.get_data_source_freshness(active_only=False)}
    publication = repository.get_current_state_staffing_publication_freshness()
    result = [
        {
            "source_id": CURRENT_STATE_PUBLICATION_SOURCE_ID,
            "state": publication.get("state", "unknown"),
            "state_reason": publication.get("state_reason"),
            "observed_at": publication.get("observed_at"),
            "latest_run_id": publication.get("publication_id"),
            "overrideable": publication.get("state_reason")
            != "current_state_staffing_schema_missing",
        }
    ]
    for source_id in STAFFING_SOURCE_IDS:
        row = rows.get(source_id) or {}
        raw_state = row.get("freshness_state")
        state = {
            "fresh": "fresh",
            "stale": "stale",
            "partial": "partial",
            "failed": "unavailable",
            "never_synced": "unknown",
            "inactive": "unknown",
            "running": "partial",
        }.get(raw_state, "unknown")
        result.append(
            {
                "source_id": source_id,
                "state": state,
                "state_reason": f"legacy_source_freshness_{raw_state or 'unknown'}",
                "observed_at": row.get("latest_finished_at") or row.get("latest_started_at"),
                "latest_run_id": row.get("latest_run_id"),
                "overrideable": True,
            }
        )
    return result


def _hiref_context(
    member: dict[str, Any],
    periods: list[dict[str, int]],
    target_project: dict[str, Any] | None,
) -> dict[str, Any]:
    if member.get("resource_type") != "STFTE":
        return {
            "status": "not_required",
            "recommended_action": "none",
            "affects_eligibility": False,
            "affects_ranking": False,
            "records": [],
        }

    unique_records: dict[str, dict[str, Any]] = {}
    for state in member["periods"].values():
        for key in ("contract", "next_contract"):
            record = state.get(key)
            if record and record.get("id"):
                unique_records[str(record["id"])] = record

    target_names = [target_project["name"]] if target_project else []
    target_ids = [target_project["id"]] if target_project else []
    target_keys = (
        [target_project["jira_key"]]
        if target_project and target_project.get("jira_key")
        else []
    )
    records = []
    aligned_intervals = []
    for record in unique_records.values():
        alignment = project_alignment_status(
            record.get("project"),
            actual_project_names=target_names,
            actual_project_ids=target_ids,
            actual_project_keys=target_keys,
        )
        records.append(
            {
                "hiref_id": record["id"],
                "request_type": record.get("request_type"),
                "project": record.get("project"),
                "start_date": record.get("start_date"),
                "end_date": record.get("end_date"),
                "project_alignment": alignment,
            }
        )
        if alignment != "aligned":
            continue
        try:
            aligned_intervals.append(
                (
                    datetime.fromisoformat(str(record["start_date"])).date(),
                    datetime.fromisoformat(str(record["end_date"])).date(),
                )
            )
        except (KeyError, TypeError, ValueError):
            continue

    records.sort(key=lambda item: (item["start_date"] or "", item["hiref_id"]))
    demand_start = datetime(periods[0]["year"], periods[0]["month"], 1).date()
    last_period = periods[-1]
    demand_end = datetime(
        last_period["year"],
        last_period["month"],
        monthrange(last_period["year"], last_period["month"])[1],
    ).date()
    if _intervals_cover(aligned_intervals, demand_start, demand_end):
        status = "covered"
        recommended_action = "none"
    elif not records:
        status = "missing"
        recommended_action = "submit_new_hiref"
    elif not aligned_intervals:
        status = "project_mismatch"
        recommended_action = "submit_target_project_hiref_or_reassign"
    else:
        status = "partial_coverage"
        recommended_action = "submit_or_extend_hiref"
    return {
        "status": status,
        "recommended_action": recommended_action,
        "affects_eligibility": False,
        "affects_ranking": True,
        "records": records,
        "required_period": {
            "start_date": demand_start.isoformat(),
            "end_date": demand_end.isoformat(),
        },
    }


def _intervals_cover(
    intervals: list[tuple[Any, Any]],
    start: Any,
    end: Any,
) -> bool:
    cursor = start
    for interval_start, interval_end in sorted(intervals):
        if interval_end < cursor:
            continue
        if interval_start > cursor:
            return False
        cursor = interval_end + timedelta(days=1)
        if cursor > end:
            return True
    return cursor > end


def _decision_fingerprint(result: dict[str, Any]) -> str:
    material = {
        "demand": result["demand"],
        "periods": result["periods"],
        "plan_version_id": result["plan_version_id"],
        "project_context": result["project_context"],
        "selections": result["selections"],
        "candidates": result["candidates"],
        "source_states": result["source_states"],
        "decision_conditions": result["decision_conditions"],
        "role_policy": result["role_policy"],
        "capacity_policy": result["capacity_policy"],
        "rule_version": result["rule_version"],
    }
    encoded = json.dumps(
        material,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def _project_context(project: dict[str, Any] | None) -> dict[str, Any]:
    if project is None:
        return {
            "project_id": None,
            "project_name": None,
            "status": "unknown",
            "tech_stack": [],
        }
    return {
        "project_id": project["id"],
        "project_name": project["name"],
        "status": project.get("status"),
        "tech_stack": project.get("tech_stack") or [],
    }


def _freshness_blockers(feasibility: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        blocker
        for blocker in feasibility["safety_blockers"]
        if blocker["code"] == "source_not_fresh"
        and blocker.get("overrideable", True)
    ]


def _non_overridable_blockers(feasibility: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        blocker
        for blocker in feasibility["safety_blockers"]
        if blocker["code"] != "source_not_fresh"
        or not blocker.get("overrideable", True)
    ]


def _hiref_conditions(feasibility: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        condition
        for condition in feasibility["decision_conditions"]
        if condition["code"] == "hiref_action_required"
    ]


class StaffingProposalService:
    def propose(
        self,
        demand: StaffingDemand,
        expires_in_minutes: int = 30,
        *,
        allow_non_fresh: bool = False,
        freshness_override_reason: str = "",
        acknowledge_hiref_actions: bool = False,
        hiref_action_note: str = "",
    ) -> dict[str, Any]:
        feasibility = assess_feasibility(demand)
        if not feasibility["feasible"]:
            return {"status": "infeasible", "feasibility": feasibility}
        hard_blockers = _non_overridable_blockers(feasibility)
        if hard_blockers:
            return {
                "status": "blocked",
                "warning": "Staffing proposal is blocked by invalid decision facts.",
                "safety_blockers": hard_blockers,
                "feasibility": feasibility,
            }
        freshness_blockers = _freshness_blockers(feasibility)
        override_reason = freshness_override_reason.strip()
        if freshness_blockers and (not allow_non_fresh or not override_reason):
            return {
                "status": "blocked",
                "warning": (
                    "Staffing sources are not fresh. A Delivery Manager may "
                    "explicitly allow non-fresh facts and provide a reason."
                ),
                "safety_blockers": freshness_blockers,
                "feasibility": feasibility,
            }
        freshness_override = None
        if freshness_blockers:
            freshness_override = {
                "authorized": True,
                "reason": override_reason,
                "source_states": feasibility["source_states"],
                "acknowledged_at": _utc_now().isoformat(),
            }
            feasibility["freshness_override"] = freshness_override
        hiref_conditions = _hiref_conditions(feasibility)
        action_note = hiref_action_note.strip()
        if hiref_conditions and (
            not acknowledge_hiref_actions
            or not action_note
        ):
            return {
                "status": "blocked",
                "warning": (
                    "Selected staffing options require a Delivery Manager HIREF "
                    "action decision and a non-empty audit note."
                ),
                "decision_conditions": hiref_conditions,
                "feasibility": feasibility,
            }
        hiref_acknowledgement = None
        if hiref_conditions:
            hiref_acknowledgement = {
                "acknowledged": True,
                "note": action_note,
                "conditions": hiref_conditions,
                "acknowledged_at": _utc_now().isoformat(),
            }
            feasibility["hiref_action_acknowledgement"] = hiref_acknowledgement
        proposal_id = f"proposal-{uuid4().hex}"
        token = secrets.token_urlsafe(32)
        expires_at = (
            _utc_now() + timedelta(minutes=expires_in_minutes)
        ).isoformat(timespec="seconds")
        repository.create_staffing_proposal({
            "proposal_id": proposal_id, "expires_at": expires_at, "confirmation_token": token,
            "request": demand.model_dump(),
            "evidence": {
                "periods": feasibility["periods"],
                "candidates": feasibility["candidates"],
                "source_states": feasibility["source_states"],
                "role_policy": feasibility["role_policy"],
                "decision_fingerprint": feasibility["decision_fingerprint"],
                "capacity_policy": feasibility["capacity_policy"],
                "capacity_evidence": [
                    {
                        "member_id": candidate["member_id"],
                        "periods": candidate["capacity_evidence"],
                    }
                    for candidate in feasibility["candidates"]
                    if candidate["member_id"]
                    in {item["member_id"] for item in feasibility["selections"]}
                ],
                "freshness_override": freshness_override,
                "hiref_action_acknowledgement": hiref_acknowledgement,
            },
            "proposal": feasibility,
        })
        return {"status": "proposed", "proposal_id": proposal_id, "confirmation_token": token, "expires_at": expires_at, "preview": feasibility}

    def preview(self, proposal_id: str) -> dict[str, Any] | None:
        proposal = repository.get_staffing_proposal(proposal_id)
        if not proposal:
            return None
        return {"proposal_id": proposal_id, "status": proposal["status"], "expires_at": proposal["expires_at"], "preview": proposal["proposal"]}

    def confirm(self, proposal_id: str, confirmation_token: str) -> dict[str, Any]:
        stored = repository.get_staffing_proposal(proposal_id)
        if not stored:
            return {"status": "unavailable", "warning": "Unknown staffing proposal"}
        if stored["status"] == "confirmed":
            try:
                return repository.confirm_staffing_proposal(proposal_id, confirmation_token, stored["proposal"])
            except ValueError as exc:
                return {"status": "invalid", "warning": str(exc)}
        if _parse_utc(stored["expires_at"]) <= _utc_now():
            try:
                expired = repository.confirm_staffing_proposal(proposal_id, confirmation_token, stored["proposal"])
                if expired["status"] == "expired":
                    return {"status": "invalid", "warning": "Proposal has expired"}
            except ValueError as exc:
                return {"status": "invalid", "warning": str(exc)}
        stored_fingerprint = stored["proposal"].get("decision_fingerprint")
        if not stored_fingerprint:
            return {
                "status": "invalid",
                "warning": (
                    "Proposal predates the fail-closed decision fingerprint; "
                    "create a new proposal."
                ),
            }
        demand = StaffingDemand(**stored["request"])
        refreshed = assess_feasibility(demand)
        if (
            not refreshed["feasible"]
            or refreshed["decision_fingerprint"] != stored_fingerprint
        ):
            return {"status": "invalid", "warning": "Decision-critical staffing facts changed; create a new proposal."}
        if _non_overridable_blockers(refreshed):
            return {
                "status": "invalid",
                "warning": "Staffing decision facts are no longer valid; create a new proposal.",
            }
        freshness_blockers = _freshness_blockers(refreshed)
        freshness_override = stored["proposal"].get("freshness_override")
        if freshness_blockers and not (
            freshness_override
            and freshness_override.get("authorized")
            and str(freshness_override.get("reason") or "").strip()
        ):
            return {
                "status": "invalid",
                "warning": (
                    "Staffing sources are not fresh and the proposal has no "
                    "audited Delivery Manager override."
                ),
            }
        hiref_conditions = _hiref_conditions(refreshed)
        hiref_acknowledgement = stored["proposal"].get(
            "hiref_action_acknowledgement"
        )
        if hiref_conditions and not (
            hiref_acknowledgement
            and hiref_acknowledgement.get("acknowledged")
            and str(hiref_acknowledgement.get("note") or "").strip()
        ):
            return {
                "status": "invalid",
                "warning": (
                    "Selected staffing options require an audited Delivery "
                    "Manager HIREF action decision."
                ),
            }
        refreshed["freshness_override"] = freshness_override
        refreshed["hiref_action_acknowledgement"] = hiref_acknowledgement
        try:
            return repository.confirm_staffing_proposal(proposal_id, confirmation_token, refreshed)
        except ValueError as exc:
            return {"status": "invalid", "warning": str(exc)}

    def cancel(self, proposal_id: str, reason: str = "") -> dict[str, Any]:
        return {"status": "cancelled" if repository.resolve_staffing_proposal(proposal_id, "cancelled", reason) else "invalid"}

    def reject(self, proposal_id: str, reason: str = "") -> dict[str, Any]:
        return {"status": "rejected" if repository.resolve_staffing_proposal(proposal_id, "rejected", reason) else "invalid"}
