"""Action item service for add/list/complete workflows."""

from __future__ import annotations

from pm_agent.use_cases.service import ServiceRequest, ServiceResponse, BaseService
from pm_agent.rules import validation
from pm_agent.database import repository


class ActionItemsService(BaseService):
    supported_requests = ["add_action", "list_actions", "complete_action"]

    def run(self, inp: ServiceRequest) -> ServiceResponse:
        return self.list_open()

    def add(
        self,
        title: str,
        owner_id: str | None = None,
        due_date: str | None = None,
        priority: str = "medium",
        source: str = "manual",
        notes: str = "",
    ) -> ServiceResponse:
        data = {
            "title":    title.strip(),
            "owner_id": owner_id,
            "source":   source,
            "priority": priority,
            "due_date": due_date,
            "notes":    notes,
        }
        vr = validation.validate_action_item(data)
        if not vr.valid:
            return ServiceResponse(success=False, message="; ".join(vr.errors))

        item_id = repository.create_action_item(data)
        return ServiceResponse(
            success=True,
            message=f"✅ Action Item #{item_id} 已创建",
            data={"id": item_id, "title": title},
        )

    def list_open(
        self,
        owner_id: str | None = None,
        overdue_only: bool = False,
    ) -> ServiceResponse:
        items = repository.get_action_items(
            status="open", owner_id=owner_id, overdue_only=overdue_only
        )
        return ServiceResponse(
            success=True,
            message=f"共 {len(items)} 条待办",
            data={"items": items, "overdue_only": overdue_only},
        )

    def complete(self, item_id: int) -> ServiceResponse:
        repository.complete_action_item(item_id)
        return ServiceResponse(
            success=True,
            message=f"✅ Action Item #{item_id} 已完成",
        )
