"""PM use-case services."""

from pm_agent.use_cases.action_items import ActionItemsService
from pm_agent.use_cases.hiref_management import HirefManagementService
from pm_agent.use_cases.resource_planning import ResourcePlanningService
from pm_agent.use_cases.team_workload import TeamWorkloadService
from pm_agent.use_cases.weekly_report import WeeklyReportService

resource_planning_service = ResourcePlanningService()
team_workload_service = TeamWorkloadService()
weekly_report_service = WeeklyReportService()
action_items_service = ActionItemsService()
hiref_management_service = HirefManagementService()

SERVICES = {
    "resource_planning": resource_planning_service,
    "team_workload": team_workload_service,
    "weekly_report": weekly_report_service,
    "action_items": action_items_service,
    "hiref_management": hiref_management_service,
}

__all__ = [
    "resource_planning_service",
    "team_workload_service",
    "weekly_report_service",
    "action_items_service",
    "hiref_management_service",
    "SERVICES",
]
