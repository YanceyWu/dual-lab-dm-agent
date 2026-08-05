"""HIREF management service for contractor expiry, slot, and placeholder review."""

from __future__ import annotations

from pm_agent.database import repository
from pm_agent.use_cases.service import BaseService, ServiceRequest, ServiceResponse


class HirefManagementService(BaseService):
    supported_requests = ["hiref_summary", "hiref_review", "hiref_slots", "hiref_placeholders"]

    def run(self, inp: ServiceRequest) -> ServiceResponse:
        days = int(inp.context.get("days", 180))
        return self.summary(days=days)

    def summary(self, days: int = 180) -> ServiceResponse:
        freshness = repository.get_contract_coverage_publication_freshness()
        freshness_state = str(freshness.get("state") or "unknown")
        full_review = self._review_rows(days=None)
        review_rows = self._review_rows(days=days)
        slot_rows = self._slot_rows(free_only=False)
        placeholder_rows = self._placeholder_rows()

        summary = {
            "active_stfte": len(full_review),
            "review_window_days": days,
            "missing_current_hiref": sum(1 for row in full_review if row["current_hiref_missing"]),
            "expiring_without_next": sum(
                1
                for row in review_rows
                if not row["current_hiref_missing"]
                and not row.get("next_hiref")
                and row["urgency"] in {"expired", "critical", "high", "medium"}
            ),
            "expiring_with_next": sum(
                1
                for row in review_rows
                if not row["current_hiref_missing"]
                and bool(row.get("next_hiref"))
            ),
            "project_mismatches": sum(1 for row in full_review if row["project_alignment_status"] == "mismatch"),
            "free_slots": sum(1 for row in slot_rows if row["is_free"]),
            "assigned_slots": sum(1 for row in slot_rows if row["occupancy_status"] == "assigned"),
            "reserved_slots": sum(
                1
                for row in slot_rows
                if row["occupancy_status"] in {"reserved_for_next", "placeholder_reserved"}
            ),
            "open_placeholders": sum(1 for row in placeholder_rows if not row["has_linked_employee"]),
            "unregistered_placeholder_slots": sum(
                1
                for row in placeholder_rows
                if row.get("hiref_id") and not row["slot_registered"]
            ),
        }
        if freshness_state not in {"fresh", "stale"}:
            summary.update(
                {
                    "active_stfte": None,
                    "missing_current_hiref": None,
                    "expiring_without_next": None,
                    "expiring_with_next": None,
                    "project_mismatches": None,
                    "free_slots": None,
                    "assigned_slots": None,
                    "reserved_slots": None,
                }
            )

        top_risks = [row for row in review_rows if row["requires_action"]][:5]
        open_placeholders = [row for row in placeholder_rows if not row["has_linked_employee"]][:5]

        return ServiceResponse(
            success=True,
            message=f"HIREF summary generated for next {days} days.",
            data={
                "summary": summary,
                "top_risks": top_risks,
                "open_placeholders": open_placeholders,
                "freshness": freshness,
            },
        )

    def review(self, days: int | None = 180) -> ServiceResponse:
        label = "all active STFTE staff" if days is None else f"next {days} days"
        rows = self._review_rows(days=days)
        freshness = repository.get_contract_coverage_publication_freshness()
        return ServiceResponse(
            success=True,
            message=f"HIREF review generated for {label}.",
            data={"rows": rows, "days": days, "freshness": freshness},
        )

    def slots(self, free_only: bool = False) -> ServiceResponse:
        rows = self._slot_rows(free_only=free_only)
        label = "free slots only" if free_only else "all slots"
        freshness = repository.get_contract_coverage_publication_freshness()
        return ServiceResponse(
            success=True,
            message=f"HIREF slot review generated ({label}).",
            data={"rows": rows, "free_only": free_only, "freshness": freshness},
        )

    def placeholders(self) -> ServiceResponse:
        rows = self._placeholder_rows()
        return ServiceResponse(
            success=True,
            message="HIREF placeholder review generated.",
            data={"rows": rows},
        )

    def _review_rows(self, days: int | None) -> list[dict]:
        rows = repository.get_hiref_staff_review(days=days)
        for row in rows:
            row["recommendation"] = _build_staff_recommendation(row)
        return sorted(rows, key=_review_priority)

    def _slot_rows(self, free_only: bool) -> list[dict]:
        rows = repository.get_hiref_contracts()
        for row in rows:
            row["recommendation"] = _build_slot_recommendation(row)
        if free_only:
            rows = [row for row in rows if row["is_free"]]
        return rows

    def _placeholder_rows(self) -> list[dict]:
        rows = repository.get_staffing_placeholders()
        for row in rows:
            row["recommendation"] = _build_placeholder_recommendation(row)
        return rows


def _review_priority(row: dict) -> tuple[int, int, str]:
    urgency_rank = {
        "expired": 0,
        "critical": 1,
        "high": 2,
        "medium": 3,
        "ok": 4,
        "unknown": 5,
    }
    alignment_rank = {
        "missing_current_hiref": 0,
        "mismatch": 1,
        "no_active_assignment": 2,
        "aligned": 3,
        "unknown": 4,
    }
    return (
        urgency_rank.get(row.get("urgency", "unknown"), 9),
        alignment_rank.get(row.get("project_alignment_status", "unknown"), 9),
        row.get("name", ""),
    )


def _build_staff_recommendation(row: dict) -> str:
    if row["current_hiref_missing"]:
        return "Confirm STFTE status and register a current HIREF, or correct the worker type."
    if row["project_alignment_status"] == "mismatch":
        if row.get("next_hiref"):
            return "Fix the HIREF project mismatch before the next HIREF is activated."
        return "Fix the HIREF project mismatch and prepare renewal against the correct project."
    if row["project_alignment_status"] == "no_active_assignment":
        return "Review whether the contractor still needs an active HIREF or should be released."
    if row.get("next_hiref"):
        return "Next HIREF is already reserved; confirm timing and project continuity."
    if row["urgency"] in {"expired", "critical"}:
        return "Renew now or release the contractor from the project immediately."
    if row["urgency"] == "high":
        return "Start renewal preparation now and confirm owner/project alignment."
    if row["urgency"] == "medium":
        return "Monitor and prepare the renewal plan before the next review cycle."
    return "No immediate action; keep under routine review."


def _build_slot_recommendation(row: dict) -> str:
    occupancy_status = row["occupancy_status"]
    if occupancy_status == "assigned":
        return "Keep with the current assignee and monitor expiry."
    if occupancy_status == "reserved_for_next":
        return "Reserved for a named next assignee; monitor activation timing."
    if occupancy_status == "placeholder_reserved":
        return "Reserved for an open placeholder; use it before requesting a new HIREF."
    if row["urgency"] in {"expired", "critical", "high"}:
        return "Free slot is reusable soon; validate the project before reassigning."
    return "Reusable free slot; prefer this before asking for a new HIREF."


def _build_placeholder_recommendation(row: dict) -> str:
    if row["has_linked_employee"]:
        return "Linked to an employee already; monitor onboarding and close the placeholder when filled."
    if row.get("hiref_id") and not row["slot_registered"]:
        return "Placeholder has a HIREF ID but no registered slot; validate or register the slot before onboarding."
    if row.get("hiref_id") and row["slot_registered"]:
        return "Open demand with a registered HIREF slot; fill this before requesting a new slot."
    return "Open demand without a HIREF slot; create or map a slot before onboarding."
