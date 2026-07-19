"""Period-aware staffing read, feasibility, proposal, and confirmation services."""

from __future__ import annotations

from calendar import monthrange
from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from pm_agent.database import repository


class StaffingDemand(BaseModel):
    project_id: str
    start_period: str
    end_period: str
    effort: float = Field(gt=0)
    role: str = ""
    required_skills: list[str] = Field(default_factory=list)
    minimum_allocation: float = Field(default=0.1, gt=0, le=1)
    maximum_people: int = Field(default=1, ge=1)
    splittable: bool = True
    priority: str = "medium"
    plan_version_id: str | None = None
    rule_version: str = "staffing-feasibility-v1"


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
    snapshots: dict[str, list[dict]] = {}
    plan_version = None
    for period in periods:
        facts, selected_plan = repository.get_staffing_facts(
            period["year"], period["month"], demand.plan_version_id
        )
        snapshots[f"{period['year']}-{period['month']:02d}"] = facts
        plan_version = plan_version or selected_plan
    members: dict[str, dict] = {}
    for period_key, facts in snapshots.items():
        for fact in facts:
            member = members.setdefault(
                fact["id"],
                {
                    "member_id": fact["id"], "name": fact["name"], "skills": fact["skills"],
                    "resource_type": fact.get("resource_type", ""), "periods": {},
                },
            )
            member["periods"][period_key] = {
                "load": fact["month_load"],
                "contract": fact["contract"],
                "status": fact["status"],
            }
    return {
        "periods": periods,
        "plan_version": plan_version,
        "members": list(members.values()),
        "missing_period_members": [member["member_id"] for member in members.values() if len(member["periods"]) != len(periods)],
    }


def assess_feasibility(demand: StaffingDemand) -> dict[str, Any]:
    model = staffing_read_model(demand)
    candidates = []
    for member in model["members"]:
        reasons = []
        if any(state["status"] != "active" for state in member["periods"].values()):
            reasons.append("member_not_active")
        missing_skills = [skill for skill in demand.required_skills if member["skills"].get(skill.lower(), 0) <= 0]
        if missing_skills:
            reasons.append("missing_required_skills")
        available = round(
            min(1.0 - float(state["load"]) for state in member["periods"].values()), 6
        ) if member["periods"] else 0.0
        if available < demand.minimum_allocation:
            reasons.append("insufficient_capacity")
        if member.get("resource_type") == "STFTE" and not _contract_covers(member["periods"], model["periods"]):
            reasons.append("contract_not_covered")
        candidates.append({**member, "available_allocation": round(max(0.0, available), 2), "reasons": reasons})
    eligible = sorted([item for item in candidates if not item["reasons"]], key=lambda item: (-item["available_allocation"], item["member_id"]))
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
    return {
        "feasible": remaining <= 0,
        "demand": demand.model_dump(),
        "periods": model["periods"],
        "plan_version_id": (model["plan_version"] or {}).get("plan_version_id"),
        "selections": selections,
        "unmet_effort": round(max(0.0, remaining), 2),
        "candidates": [{key: item[key] for key in ("member_id", "name", "available_allocation", "reasons")} for item in candidates],
        "unknowns": model["missing_period_members"],
        "source_states": _source_states(),
        "rule_version": demand.rule_version,
    }


def _source_states() -> list[dict[str, str]]:
    relevant = {"import-resource-portal", "import-skills-matrix"}
    rows = {row["id"]: row for row in repository.get_data_source_freshness(active_only=False)}
    return [
        {"source_id": source_id, "state": (rows.get(source_id) or {}).get("freshness_state", "unknown")}
        for source_id in sorted(relevant)
    ]


def _contract_covers(states: dict[str, dict], periods: list[dict[str, int]]) -> bool:
    for period in periods:
        key = f"{period['year']}-{period['month']:02d}"
        contract = states[key]["contract"]
        if contract is None:
            continue
        start = datetime.fromisoformat(contract["start_date"]).date()
        end = datetime.fromisoformat(contract["end_date"]).date()
        period_start = datetime(period["year"], period["month"], 1).date()
        period_end = datetime(period["year"], period["month"], monthrange(period["year"], period["month"])[1]).date()
        if start > period_start or end < period_end:
            return False
    return True


class StaffingProposalService:
    def propose(self, demand: StaffingDemand, expires_in_minutes: int = 30) -> dict[str, Any]:
        feasibility = assess_feasibility(demand)
        if not feasibility["feasible"]:
            return {"status": "infeasible", "feasibility": feasibility}
        proposal_id = f"proposal-{uuid4().hex}"
        token = uuid4().hex
        expires_at = (datetime.now() + timedelta(minutes=expires_in_minutes)).isoformat()
        repository.create_staffing_proposal({
            "proposal_id": proposal_id, "expires_at": expires_at, "confirmation_token": token,
            "request": demand.model_dump(), "evidence": {"periods": feasibility["periods"], "candidates": feasibility["candidates"]},
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
        if datetime.fromisoformat(stored["expires_at"]) <= datetime.now():
            try:
                expired = repository.confirm_staffing_proposal(proposal_id, confirmation_token, stored["proposal"])
                if expired["status"] == "expired":
                    return {"status": "invalid", "warning": "Proposal has expired"}
            except ValueError as exc:
                return {"status": "invalid", "warning": str(exc)}
        demand = StaffingDemand(**stored["request"])
        refreshed = assess_feasibility(demand)
        if not refreshed["feasible"] or refreshed["selections"] != stored["proposal"]["selections"]:
            return {"status": "invalid", "warning": "Decision-critical staffing facts changed; create a new proposal."}
        try:
            return repository.confirm_staffing_proposal(proposal_id, confirmation_token, refreshed)
        except ValueError as exc:
            return {"status": "invalid", "warning": str(exc)}

    def cancel(self, proposal_id: str, reason: str = "") -> dict[str, Any]:
        return {"status": "cancelled" if repository.resolve_staffing_proposal(proposal_id, "cancelled", reason) else "invalid"}

    def reject(self, proposal_id: str, reason: str = "") -> dict[str, Any]:
        return {"status": "rejected" if repository.resolve_staffing_proposal(proposal_id, "rejected", reason) else "invalid"}
