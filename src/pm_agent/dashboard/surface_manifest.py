"""Code-owned Phase 1 dashboard surface declarations."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DashboardTab:
    tab_id: str
    label: str
    group: str


@dataclass(frozen=True)
class DashboardSurfaceManifest:
    surface_id: str
    display_name: str
    default_tab: str
    visible_tab_ids: tuple[str, ...]


DASHBOARD_TABS: tuple[DashboardTab, ...] = (
    DashboardTab("overview", "Overview", "legacy"),
    DashboardTab("projects", "Projects", "legacy"),
    DashboardTab("team", "Team", "legacy"),
    DashboardTab("hiref", "HIREF", "legacy"),
    DashboardTab("allocation", "Monthly Plan", "legacy"),
    DashboardTab("health", "Project Health", "legacy"),
    DashboardTab("attention", "Attention", "experimental"),
    DashboardTab("weekly-brief", "Weekly Brief v2", "experimental"),
    DashboardTab("capacity", "Capacity Heatmap", "experimental"),
    DashboardTab("execution", "Delivery Execution", "experimental"),
    DashboardTab("layered-health", "Layered Health", "experimental"),
    DashboardTab("connectors", "Connectors", "experimental"),
    DashboardTab("snapshots", "Snapshots", "experimental"),
)

_TAB_BY_ID = {tab.tab_id: tab for tab in DASHBOARD_TABS}

LEGACY_TAB_IDS: tuple[str, ...] = tuple(
    tab.tab_id for tab in DASHBOARD_TABS if tab.group == "legacy"
)
EXPERIMENTAL_TAB_IDS: tuple[str, ...] = tuple(
    tab.tab_id for tab in DASHBOARD_TABS if tab.group == "experimental"
)

PHASE1_LEGACY_DASHBOARD_TRIAL = DashboardSurfaceManifest(
    surface_id="phase1-legacy-dashboard-trial",
    display_name="Phase 1 legacy dashboard trial",
    default_tab="overview",
    visible_tab_ids=LEGACY_TAB_IDS,
)


def tab_label(tab_id: str) -> str:
    return _TAB_BY_ID[tab_id].label


def visible_tab_labels(
    surface: DashboardSurfaceManifest = PHASE1_LEGACY_DASHBOARD_TRIAL,
) -> tuple[str, ...]:
    return tuple(tab_label(tab_id) for tab_id in surface.visible_tab_ids)


def surface_config_payload(
    surface: DashboardSurfaceManifest = PHASE1_LEGACY_DASHBOARD_TRIAL,
) -> dict[str, object]:
    return {
        "surfaceId": surface.surface_id,
        "displayName": surface.display_name,
        "defaultTab": surface.default_tab,
        "visibleTabs": list(surface.visible_tab_ids),
        "tabGroups": {
            "legacy": list(LEGACY_TAB_IDS),
            "experimental": list(EXPERIMENTAL_TAB_IDS),
        },
    }
