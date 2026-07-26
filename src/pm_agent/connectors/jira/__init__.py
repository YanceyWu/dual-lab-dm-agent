from __future__ import annotations

import sqlite3
from pathlib import Path

from pm_agent.sync.jira.health_sync import run_sync as _run_health_sync
from pm_agent.sync.jira.release_sync import sync_all as _sync_release_sync
from pm_agent.config import settings
from pm_agent.connectors.base import ConnectorValidationResult
from pm_agent.connectors.shared import AtlassianAuthError, get_auth_session
from pm_agent.repo_tools import bootstrap as repo_bootstrap

CONNECTOR_NAME = "jira"
DISPLAY_NAME = "JIRA"
SOURCE_TYPE = "jira"


def _effective_config() -> dict:
    try:
        return repo_bootstrap.build_effective_config().config.get("connectors", {}).get("jira", {})
    except repo_bootstrap.StarterRepoError:
        return {}


def sync_releases(board: str = "", project: str = "", dry_run: bool = False) -> None:
    _sync_release_sync(board_filter=board, project_filter=project, dry_run=dry_run)


def sync_health(board: str | None = None, dry_run: bool = False) -> None:
    _run_health_sync(board=board, dry_run=dry_run)


def validate_connector() -> ConnectorValidationResult:
    config = _effective_config()
    enabled = bool(config.get("enabled", False))
    auth_mode = str(config.get("auth_mode", "atlassian_oauth"))
    base_url = str(config.get("base_url") or settings.jira_base_url).strip()

    warnings: list[str] = []
    errors: list[str] = []
    details: dict[str, str] = {
        "base_url": base_url or "-",
    }

    db_path = Path(settings.database_path)
    board_count = 0
    if db_path.exists():
        try:
            with sqlite3.connect(db_path) as conn:
                row = conn.execute(
                    "SELECT COUNT(*) FROM jira_board_configs WHERE COALESCE(active, 0) = 1"
                ).fetchone()
                board_count = int(row[0] if row else 0)
        except sqlite3.OperationalError:
            warnings.append("JIRA runtime tables are not initialized yet. Run `pm init` or `python scripts/init_db.py`.")
    details["active_boards"] = str(board_count)

    if enabled and not base_url:
        errors.append("JIRA connector is enabled but no base URL is configured.")

    if enabled and base_url:
        token_refreshed = False

        def mark_token_refreshed() -> None:
            nonlocal token_refreshed
            token_refreshed = True

        try:
            auth = get_auth_session(
                "jira",
                base_url_hint=base_url,
                email=settings.jira_user_email,
                api_token=settings.jira_api_token,
                verify_ssl=True,
                cloud_id_hint=str(config.get("cloud_id") or settings.atlassian_cloud_id),
                refresh_observer=mark_token_refreshed,
            )
            details["resolved_auth_type"] = auth.auth_type
            details["resolved_base_url"] = auth.base_url
            if auth.cloud_id:
                details["cloud_id"] = auth.cloud_id
            if auth.token_source:
                details["token_source"] = auth.token_source
            token_refreshed = token_refreshed or auth.token_refreshed
        except AtlassianAuthError as exc:
            errors.append(str(exc))
        except Exception as exc:
            errors.append(f"JIRA auth probe failed: {exc}")
        finally:
            details["token_refreshed"] = "yes" if token_refreshed else "no"

    if enabled and board_count == 0:
        warnings.append("No active JIRA boards configured. Run `pm release add-board` before syncing.")

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
