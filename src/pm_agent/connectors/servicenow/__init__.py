from __future__ import annotations

from pathlib import Path

from pm_agent.sync.servicenow.cr_import import import_cr as _import_cr_csv
from pm_agent.config import settings
from pm_agent.connectors.base import ConnectorValidationResult
from pm_agent.connectors.servicenow.browser_client import (
    default_browser_profile,
    download_change_request_csv,
    playwright_status,
)
from pm_agent.repo_tools import bootstrap as repo_bootstrap

CONNECTOR_NAME = "servicenow"
DISPLAY_NAME = "ServiceNow"
SOURCE_TYPE = "servicenow"


def _effective_config() -> dict:
    try:
        return repo_bootstrap.build_effective_config().config.get("connectors", {}).get("servicenow", {})
    except repo_bootstrap.StarterRepoError:
        return {}


def sync_change_requests(dry_run: bool = False) -> Path:
    save_path = Path(settings.database_path).parent.parent / "data-feed" / "cr_latest.csv"
    download_change_request_csv(save_path)
    if not dry_run:
        _import_cr_csv(str(save_path), dry_run=False)
    return save_path


def import_change_requests(file_path: str, dry_run: bool = False) -> None:
    _import_cr_csv(file_path, dry_run=dry_run)


def validate_connector() -> ConnectorValidationResult:
    config = _effective_config()
    enabled = bool(config.get("enabled", False))
    auth_mode = str(config.get("auth_mode", "browser_session"))
    base_url = str(config.get("base_url") or settings.snow_base_url).strip()

    warnings: list[str] = []
    errors: list[str] = []

    profile = default_browser_profile()
    playwright_ready, playwright_note = playwright_status()

    details = {
        "base_url": base_url or "-",
        "browser": str(config.get("browser", settings.snow_browser or "edge")),
        "browser_profile": str(profile),
        "browser_profile_exists": "yes" if profile.exists() else "no",
        "playwright": "ready" if playwright_ready else playwright_note,
        "file_import": "available via `pm cr import <csv>`",
    }

    if enabled and not base_url:
        errors.append("ServiceNow connector is enabled but no base URL is configured.")
    if auth_mode == "browser_session" and not playwright_ready:
        warnings.append(
            "Playwright is not installed, so `pm cr sync` cannot download from ServiceNow yet."
        )
    if auth_mode == "browser_session" and not profile.exists():
        warnings.append(
            "Edge browser profile not found. `pm cr sync` needs an authenticated browser session."
        )

    return ConnectorValidationResult(
        name=CONNECTOR_NAME,
        display_name=DISPLAY_NAME,
        enabled=enabled,
        ready=enabled and not errors,
        auth_mode=auth_mode,
        details=details,
        warnings=warnings,
        errors=errors,
    )
