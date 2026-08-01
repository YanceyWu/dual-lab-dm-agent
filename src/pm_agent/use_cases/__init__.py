"""PM use-case services."""

from pm_agent.use_cases.action_items import ActionItemsService
from pm_agent.use_cases.action_followup import execute_action_followup
from pm_agent.use_cases.contract_continuity import execute_contract_continuity_review
from pm_agent.use_cases.connector_status import execute_connector_status_review
from pm_agent.use_cases.connector_sync_results import execute_connector_sync_results
from pm_agent.use_cases.delivery_attention_center import (
    execute_delivery_attention_center,
)
from pm_agent.use_cases.delivery_execution_review import execute_delivery_execution_review
from pm_agent.use_cases.execution import (
    IntelligenceCapabilities,
    UseCaseDescriptor,
    UseCaseExecutor,
)
from pm_agent.use_cases.hiref_management import HirefManagementService
from pm_agent.use_cases.management_attention import execute_management_attention
from pm_agent.use_cases.layered_project_health import execute_layered_project_health_review
from pm_agent.use_cases.project_health import execute_project_health_review
from pm_agent.use_cases.project_snapshots import execute_project_snapshot_list
from pm_agent.use_cases.resource_planning import ResourcePlanningService
from pm_agent.use_cases.resource_capacity_heatmap import execute_resource_capacity_heatmap
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
        use_case_id="resource-capacity-heatmap",
        purpose="Return current published member/month effective capacity and overload facts without recalculating or writing them.",
        parameter_schema={
            "year": {"type": "integer", "required": True, "minimum": 2000, "maximum": 2100},
            "month": {"type": "integer", "required": True, "minimum": 1, "maximum": 12},
            "plan_version_id": {"type": "string", "required": True, "maximum_length": 128},
            "member_ids": {"type": "array", "required": False},
            "states": {"type": "array", "required": False},
        },
        intelligence_capabilities=IntelligenceCapabilities(facts=True, signals=True),
    ),
    execute_resource_capacity_heatmap,
)
use_case_executor.register(
    UseCaseDescriptor(
        use_case_id="layered-project-health-review",
        purpose="Return the latest persisted seven-dimension Project Health assessment without evaluating or changing it.",
        parameter_schema={
            "project_id": {"type": "string", "required": False, "maximum_length": 128, "description": "Optional exact stable anonymous project ID."},
        },
        intelligence_capabilities=IntelligenceCapabilities(facts=True, signals=True),
    ),
    execute_layered_project_health_review,
)
use_case_executor.register(
    UseCaseDescriptor(
        use_case_id="delivery-execution-review",
        purpose="Return bounded read-only Sprint Execution and Release/Milestone facts from local derivations.",
        parameter_schema={
            "project_id": {"type": "string", "required": True, "maximum_length": 128, "description": "Existing stable anonymous project ID."},
            "layer": {"type": "string", "required": False, "enum": ["sprint", "release_milestone", "all"], "description": "Execution layer; defaults to all."},
            "subject_kind": {"type": "string", "required": False, "enum": ["sprint", "release", "milestone", "dependency"], "description": "Optional canonical subject kind."},
            "subject_id": {"type": "string", "required": False, "maximum_length": 128, "description": "Optional canonical subject ID; requires subject_kind."},
            "window_days": {"type": "integer", "required": False, "minimum": 1, "maximum": 365, "description": "Observation window in days; defaults to 30."},
            "limit": {"type": "integer", "required": False, "minimum": 1, "maximum": 200, "description": "Maximum facts, 1 to 200."},
        },
        intelligence_capabilities=IntelligenceCapabilities(facts=True, signals=True),
    ),
    execute_delivery_execution_review,
)
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
        use_case_id="delivery-attention-center",
        purpose=(
            "Return persisted Delivery Attention items, reconciliation coverage, "
            "and optional bounded history without reconciling or changing them."
        ),
        parameter_schema={
            "attention_states": {
                "type": "array",
                "required": False,
                "description": "Unique workflow states; defaults to unresolved states.",
            },
            "rule_key": {
                "type": "string",
                "required": False,
                "maximum_length": 128,
                "description": "Optional exact Attention rule key.",
            },
            "subject_kind": {
                "type": "string",
                "required": False,
                "maximum_length": 128,
                "description": "Optional canonical subject kind.",
            },
            "subject_id": {
                "type": "string",
                "required": False,
                "maximum_length": 128,
                "description": "Optional stable anonymous subject ID.",
            },
            "include_history": {
                "type": "boolean",
                "required": False,
                "description": "Include bounded newest-first event metadata.",
            },
            "limit": {
                "type": "integer",
                "required": False,
                "minimum": 1,
                "maximum": 50,
                "description": "Maximum current items, 1 to 50.",
            },
            "history_limit": {
                "type": "integer",
                "required": False,
                "minimum": 0,
                "maximum": 20,
                "description": "Maximum events per returned item, 0 to 20.",
            },
        },
        intelligence_capabilities=IntelligenceCapabilities(
            facts=True,
            signals=True,
            recommendations=True,
        ),
    ),
    execute_delivery_attention_center,
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
