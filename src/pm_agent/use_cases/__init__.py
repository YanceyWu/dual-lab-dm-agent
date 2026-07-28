"""PM use-case services."""

from pm_agent.use_cases.action_items import ActionItemsService
from pm_agent.use_cases.action_followup import execute_action_followup
from pm_agent.use_cases.contract_continuity import execute_contract_continuity_review
from pm_agent.use_cases.connector_status import execute_connector_status_review
from pm_agent.use_cases.connector_sync_results import execute_connector_sync_results
from pm_agent.use_cases.execution import (
    IntelligenceCapabilities,
    UseCaseDescriptor,
    UseCaseExecutor,
)
from pm_agent.use_cases.hiref_management import HirefManagementService
from pm_agent.use_cases.management_attention import execute_management_attention
from pm_agent.use_cases.project_health import execute_project_health_review
from pm_agent.use_cases.project_snapshots import execute_project_snapshot_list
from pm_agent.use_cases.resource_planning import ResourcePlanningService
from pm_agent.use_cases.team_workload import TeamWorkloadService, execute_team_workload_overview
from pm_agent.use_cases.weekly_report import WeeklyReportService
from pm_agent.use_cases.weekly_brief import execute_weekly_dm_brief

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

use_case_executor = UseCaseExecutor()
use_case_executor.register(
    UseCaseDescriptor(
        use_case_id="team-workload-overview",
        purpose="Return current workload and capacity statistics for active team members.",
        parameter_schema={
            "team": {"type": "string", "required": False, "maximum_length": 200, "description": "Exact team filter."},
        },
    ),
    execute_team_workload_overview,
)
use_case_executor.register(
    UseCaseDescriptor(
        use_case_id="project-health-review",
        purpose="Return the latest locally stored project-health observations and their freshness.",
        parameter_schema={
            "project_id": {"type": "string", "required": False, "maximum_length": 200, "description": "Exact active project ID."},
        },
    ),
    execute_project_health_review,
)
use_case_executor.register(
    UseCaseDescriptor(
        use_case_id="management-attention",
        purpose="Rank locally observed delivery issues that need Delivery Manager attention.",
        parameter_schema={"limit": {"type": "integer", "required": False, "minimum": 1, "maximum": 20, "description": "Maximum items, 1 to 20."}},
        intelligence_capabilities=IntelligenceCapabilities(
            facts=True,
            signals=True,
        ),
    ),
    execute_management_attention,
)
use_case_executor.register(
    UseCaseDescriptor(
        use_case_id="contract-continuity-review",
        purpose="Review recorded HIREF coverage and continuity risks for active STFTE staff.",
        parameter_schema={"days": {"type": "integer", "required": False, "minimum": 1, "maximum": 365, "description": "Review window in days, 1 to 365."}},
    ),
    execute_contract_continuity_review,
)
use_case_executor.register(UseCaseDescriptor(use_case_id="weekly-dm-brief", purpose="Return a structured weekly Delivery Manager brief from local facts.", parameter_schema={}), execute_weekly_dm_brief)
use_case_executor.register(UseCaseDescriptor(use_case_id="action-followup", purpose="Return open actions requiring follow-up without changing them.", parameter_schema={}), execute_action_followup)
use_case_executor.register(UseCaseDescriptor(use_case_id="connector-status-review", purpose="Return offline connector source and sync freshness without runtime probing.", parameter_schema={"connector": {"type": "string", "required": False, "enum": ["jira", "confluence", "servicenow"], "description": "Optional connector name."}}), execute_connector_status_review)
use_case_executor.register(UseCaseDescriptor(use_case_id="connector-sync-results", purpose="Return normalized latest local connector sync outcomes without credentials or raw errors.", parameter_schema={"connector": {"type": "string", "required": False, "enum": ["jira", "confluence", "servicenow"], "description": "Optional connector name."}}), execute_connector_sync_results)
use_case_executor.register(UseCaseDescriptor(use_case_id="project-snapshot-list", purpose="List stored project snapshots through the shared read-only contract.", parameter_schema={"project_id": {"type": "string", "required": False, "maximum_length": 200, "description": "Optional exact project ID."}, "artifact_kind": {"type": "string", "required": False, "maximum_length": 50, "description": "Optional snapshot kind."}, "artifact_state": {"type": "string", "required": False, "maximum_length": 50, "description": "Optional snapshot state."}, "health": {"type": "string", "required": False, "enum": ["green", "amber", "red", "unknown"], "description": "Optional health filter."}, "horizon": {"type": "string", "required": False, "maximum_length": 50, "description": "Optional horizon filter."}, "limit": {"type": "integer", "required": False, "minimum": 1, "maximum": 200, "description": "Maximum snapshots, 1 to 200."}}), execute_project_snapshot_list)

__all__ = [
    "resource_planning_service",
    "team_workload_service",
    "weekly_report_service",
    "action_items_service",
    "hiref_management_service",
    "SERVICES",
    "use_case_executor",
]
