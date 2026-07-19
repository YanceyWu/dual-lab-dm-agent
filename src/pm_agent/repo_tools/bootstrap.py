from __future__ import annotations

import copy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pm_agent.config import PROJECT_ROOT, settings

ENV_EXAMPLE_PATH = PROJECT_ROOT / ".env.example"
ENV_PATH = PROJECT_ROOT / ".env"
CONFIG_ROOT = PROJECT_ROOT / "configs"
COMPANY_DIR = CONFIG_ROOT / "company"
TEAM_DIR = CONFIG_ROOT / "teams"
PROJECT_DIR = CONFIG_ROOT / "projects"
COMPANY_BASELINE_PATH = COMPANY_DIR / "baseline.yaml"
LOCKED_CONTROLS_PATH = COMPANY_DIR / "locked-controls.yaml"
EXAMPLE_TEAM_PATH = TEAM_DIR / "example-team.yaml"
EXAMPLE_PROJECT_PATH = PROJECT_DIR / "example-project.yaml"

DEFAULT_BASELINE_YAML = """company:
  name: Example Organization
  region: Example Region
  shared_baseline_id: dm-agent-example-v1

runtime:
  database:
    path: data/pm.db
  log_level: INFO

scoring:
  allocation:
    skill_weight: 0.35
    availability_weight: 0.30
    track_record_weight: 0.20
    team_fit_weight: 0.15

rules:
  allocation:
    max_load_threshold: 1.0
    min_skill_threshold: 0.20
    max_concurrent_projects: 2

workflows:
  weekly_status:
    default_day: Friday
    snapshot_retention: 12
  planning:
    default_horizon: milestone
    default_state: draft

presentation:
  default_language: en
  table_row_limit: 10

connectors:
  jira:
    enabled: true
    auth_mode: atlassian_oauth
    base_url: ""
    cloud_id: ""
    refresh_sla_hours: 24
  confluence:
    enabled: true
    auth_mode: atlassian_oauth
    base_url: ""
    cloud_id: ""
    refresh_sla_hours: 24
  servicenow:
    enabled: true
    auth_mode: browser_session
    base_url: ""
    browser: edge
    refresh_sla_hours: 168
"""

DEFAULT_LOCKED_CONTROLS_YAML = """locked:
  - company.name
  - company.region
  - company.shared_baseline_id
  - scoring.allocation
  - rules.allocation.max_load_threshold
"""

DEFAULT_TEAM_YAML = """team:
  id: example-team
  name: Example PM Team

overrides:
  workflows:
    weekly_status:
      default_sections:
        - delivery
        - staffing
        - risks
    planning:
      focus_projects:
        - example-program
  presentation:
    default_language: zh-HK
"""

DEFAULT_PROJECT_YAML = """project:
  id: example-project
  name: Example Project

overrides:
  workflows:
    planning:
      default_horizon: weekly
  reporting:
    highlight_metrics:
      - schedule
      - capacity
      - risks
"""


class StarterRepoError(ValueError):
    """Raised when starter repo bootstrap or config checks fail."""


@dataclass(frozen=True)
class PathStatus:
    label: str
    path: Path
    exists: bool


@dataclass(frozen=True)
class InitResult:
    created: list[PathStatus]
    reused: list[PathStatus]
    database_initialized: bool
    database_path: Path


@dataclass(frozen=True)
class EffectiveConfigResult:
    config: dict[str, Any]
    sources: list[PathStatus]


@dataclass(frozen=True)
class ConfigValidationResult:
    checked_paths: list[PathStatus]
    warnings: list[str]
    errors: list[str]


def _require_yaml() -> Any:
    try:
        import yaml
    except ImportError as exc:
        raise StarterRepoError(
            "PyYAML is required for `pm config *`. Install it with `pip install pyyaml` "
            "or `pip install -e .` from the repo root."
        ) from exc
    return yaml


def _base_config() -> dict[str, Any]:
    return {
        "company": {
            "name": "Example Organization",
            "region": "Example Region",
            "shared_baseline_id": "dm-agent-example-v1",
        },
        "runtime": {
            "database": {"path": "data/pm.db"},
            "log_level": "INFO",
        },
        "scoring": {
            "allocation": {
                "skill_weight": 0.35,
                "availability_weight": 0.30,
                "track_record_weight": 0.20,
                "team_fit_weight": 0.15,
            }
        },
        "rules": {
            "allocation": {
                "max_load_threshold": 1.0,
                "min_skill_threshold": 0.20,
                "max_concurrent_projects": 2,
            }
        },
        "workflows": {
            "weekly_status": {
                "default_day": "Friday",
                "snapshot_retention": 12,
            },
            "planning": {
                "default_horizon": "milestone",
                "default_state": "draft",
            },
        },
        "presentation": {
            "default_language": "en",
            "table_row_limit": 10,
        },
        "connectors": {
            "jira": {
                "enabled": True,
                "auth_mode": "atlassian_oauth",
                "base_url": "",
                "cloud_id": "",
                "refresh_sla_hours": 24,
            },
            "confluence": {
                "enabled": True,
                "auth_mode": "atlassian_oauth",
                "base_url": "",
                "cloud_id": "",
                "refresh_sla_hours": 24,
            },
            "servicenow": {
                "enabled": True,
                "auth_mode": "browser_session",
                "base_url": "",
                "browser": "edge",
                "refresh_sla_hours": 168,
            },
        },
    }


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def _status(label: str, path: Path) -> PathStatus:
    return PathStatus(label=label, path=path.resolve(), exists=path.exists())


def _resolve_override_path(root: Path, value: str | None) -> Path | None:
    if not value:
        return None
    candidate = Path(value)
    if candidate.is_absolute() or candidate.suffix in {".yaml", ".yml"} or len(candidate.parts) > 1:
        return candidate if candidate.is_absolute() else (PROJECT_ROOT / candidate).resolve()
    return (root / f"{value}.yaml").resolve()


def _write_text_file(path: Path, content: str, force: bool = False) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not force:
        return False
    path.write_text(content.rstrip() + "\n", encoding="utf-8")
    return True


def _load_yaml_mapping(path: Path) -> dict[str, Any]:
    yaml = _require_yaml()
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise StarterRepoError(f"Invalid YAML in {path}: {exc}") from exc
    if loaded is None:
        return {}
    if not isinstance(loaded, dict):
        raise StarterRepoError(f"Config file {path} must use a mapping at the root.")
    return loaded


def _extract_override_payload(config: dict[str, Any]) -> dict[str, Any]:
    overrides = config.get("overrides")
    if overrides is None:
        return config
    if not isinstance(overrides, dict):
        raise StarterRepoError("Override payload must be a mapping under `overrides`.")
    return overrides


def _env_overlay() -> dict[str, Any]:
    overlay = {
        "runtime": {
            "database": {"path": settings.database_path},
            "log_level": settings.log_level,
        },
        "scoring": {
            "allocation": {
                "skill_weight": settings.scoring.skill_weight,
                "availability_weight": settings.scoring.availability_weight,
                "track_record_weight": settings.scoring.track_record_weight,
                "team_fit_weight": settings.scoring.team_fit_weight,
            }
        },
        "rules": {
            "allocation": {
                "max_load_threshold": settings.rules.max_load_threshold,
                "min_skill_threshold": settings.rules.min_skill_threshold,
                "max_concurrent_projects": settings.rules.max_concurrent_projects,
            }
        },
    }
    jira_overlay: dict[str, Any] = {}
    if settings.jira_base_url:
        jira_overlay["base_url"] = settings.jira_base_url
    if settings.jira_user_email:
        jira_overlay["user_email"] = settings.jira_user_email
    if settings.jira_api_token:
        jira_overlay["api_token"] = settings.jira_api_token
    jira_overlay["verify_ssl"] = settings.jira_verify_ssl
    if jira_overlay:
        overlay["connectors"] = {"jira": jira_overlay}
    confluence_overlay: dict[str, Any] = {"verify_ssl": settings.confluence_verify_ssl}
    if settings.confluence_base_url:
        confluence_overlay["base_url"] = settings.confluence_base_url
    if settings.confluence_email:
        confluence_overlay["user_email"] = settings.confluence_email
    elif settings.jira_user_email:
        confluence_overlay["user_email"] = settings.jira_user_email
    if settings.confluence_api_token:
        confluence_overlay["api_token"] = settings.confluence_api_token
    elif settings.jira_api_token:
        confluence_overlay["api_token"] = settings.jira_api_token
    if settings.confluence_cloud_id:
        confluence_overlay["cloud_id"] = settings.confluence_cloud_id
    elif settings.atlassian_cloud_id:
        confluence_overlay["cloud_id"] = settings.atlassian_cloud_id
    overlay["connectors"] = _deep_merge(
        overlay.get("connectors", {}),
        {"confluence": confluence_overlay},
    )
    servicenow_overlay: dict[str, Any] = {
        "base_url": settings.snow_base_url,
        "browser": settings.snow_browser,
    }
    if settings.snow_browser_profile:
        servicenow_overlay["browser_profile"] = settings.snow_browser_profile
    overlay["connectors"] = _deep_merge(
        overlay.get("connectors", {}),
        {"servicenow": servicenow_overlay},
    )
    return overlay


def _flatten_paths(value: Any, prefix: str = "") -> list[str]:
    if not isinstance(value, dict):
        return [prefix] if prefix else []
    paths: list[str] = []
    for key, nested in value.items():
        current = f"{prefix}.{key}" if prefix else key
        paths.append(current)
        paths.extend(_flatten_paths(nested, current))
    return paths


def _load_locked_paths() -> list[str]:
    if not LOCKED_CONTROLS_PATH.exists():
        return []
    payload = _load_yaml_mapping(LOCKED_CONTROLS_PATH)
    raw_locked = payload.get("locked", [])
    if not isinstance(raw_locked, list) or any(not isinstance(item, str) for item in raw_locked):
        raise StarterRepoError("`configs/company/locked-controls.yaml` must contain a string list at `locked`.")
    return raw_locked


def _path_conflicts_with_locked(path: str, locked_paths: list[str]) -> bool:
    return any(
        path == locked
        or path.startswith(f"{locked}.")
        or locked.startswith(f"{path}.")
        for locked in locked_paths
    )


def _validate_locked_overrides(
    label: str,
    path: Path,
    override_payload: dict[str, Any],
    locked_paths: list[str],
    errors: list[str],
) -> None:
    for dotted_path in _flatten_paths(override_payload):
        if dotted_path and _path_conflicts_with_locked(dotted_path, locked_paths):
            errors.append(f"{label} override {path} cannot change locked setting `{dotted_path}`.")


def _selected_team_status(team: str | None) -> PathStatus:
    return _status("team override", _resolve_override_path(TEAM_DIR, team) or EXAMPLE_TEAM_PATH)


def _selected_project_status(project: str | None) -> PathStatus:
    return _status("project override", _resolve_override_path(PROJECT_DIR, project) or EXAMPLE_PROJECT_PATH)


def get_repo_path_statuses(team: str | None = None, project: str | None = None) -> list[PathStatus]:
    return [
        _status(".env", ENV_PATH),
        _status(".env.example", ENV_EXAMPLE_PATH),
        _status("database", Path(settings.database_path)),
        _status("company baseline", COMPANY_BASELINE_PATH),
        _status("locked controls", LOCKED_CONTROLS_PATH),
        _selected_team_status(team),
        _selected_project_status(project),
    ]


def initialize_starter_repo(
    force_env: bool = False,
    force_config: bool = False,
    skip_db: bool = False,
) -> InitResult:
    if not ENV_EXAMPLE_PATH.exists():
        raise StarterRepoError(f"Missing {ENV_EXAMPLE_PATH.name}; starter repo cannot scaffold .env.")

    created: list[PathStatus] = []
    reused: list[PathStatus] = []

    files_to_seed = [
        (".env", ENV_PATH, ENV_EXAMPLE_PATH.read_text(encoding="utf-8"), force_env),
        ("company baseline", COMPANY_BASELINE_PATH, DEFAULT_BASELINE_YAML, force_config),
        ("locked controls", LOCKED_CONTROLS_PATH, DEFAULT_LOCKED_CONTROLS_YAML, force_config),
        ("team override", EXAMPLE_TEAM_PATH, DEFAULT_TEAM_YAML, force_config),
        ("project override", EXAMPLE_PROJECT_PATH, DEFAULT_PROJECT_YAML, force_config),
    ]

    for label, path, content, force in files_to_seed:
        written = _write_text_file(path, content, force=force)
        status = _status(label, path)
        if written:
            created.append(status)
        else:
            reused.append(status)

    database_path = Path(settings.database_path)
    database_path.parent.mkdir(parents=True, exist_ok=True)
    if not skip_db:
        from pm_agent.database.bootstrap import main as init_db_main

        init_db_main(quiet=True)

    return InitResult(
        created=created,
        reused=reused,
        database_initialized=not skip_db,
        database_path=database_path.resolve(),
    )


def build_effective_config(
    team: str | None = None,
    project: str | None = None,
) -> EffectiveConfigResult:
    effective = _base_config()
    sources = [
        _status(".env", ENV_PATH),
        _status("company baseline", COMPANY_BASELINE_PATH),
    ]

    if COMPANY_BASELINE_PATH.exists():
        effective = _deep_merge(effective, _load_yaml_mapping(COMPANY_BASELINE_PATH))

    team_path = _resolve_override_path(TEAM_DIR, team)
    if team_path:
        if not team_path.exists():
            raise StarterRepoError(f"Team override not found: {team_path}")
        sources.append(_status("team override", team_path))
        effective = _deep_merge(effective, _extract_override_payload(_load_yaml_mapping(team_path)))

    project_path = _resolve_override_path(PROJECT_DIR, project)
    if project_path:
        if not project_path.exists():
            raise StarterRepoError(f"Project override not found: {project_path}")
        sources.append(_status("project override", project_path))
        effective = _deep_merge(effective, _extract_override_payload(_load_yaml_mapping(project_path)))

    effective = _deep_merge(effective, _env_overlay())
    return EffectiveConfigResult(config=effective, sources=sources)


def validate_config(
    team: str | None = None,
    project: str | None = None,
) -> ConfigValidationResult:
    checked_paths = get_repo_path_statuses(team=team, project=project)
    warnings: list[str] = []
    errors: list[str] = []

    if not ENV_PATH.exists():
        warnings.append("`.env` is missing. Run `pm init` to scaffold it from `.env.example`.")
    if not COMPANY_BASELINE_PATH.exists():
        warnings.append("`configs/company/baseline.yaml` is missing; code defaults will be used.")
    if not LOCKED_CONTROLS_PATH.exists():
        warnings.append("`configs/company/locked-controls.yaml` is missing; no locked-key guardrails are active.")

    try:
        locked_paths = _load_locked_paths()
        effective = build_effective_config(team=team, project=project).config
    except StarterRepoError as exc:
        errors.append(str(exc))
        return ConfigValidationResult(checked_paths=checked_paths, warnings=warnings, errors=errors)

    team_path = _resolve_override_path(TEAM_DIR, team)
    if team_path and team_path.exists() and locked_paths:
        _validate_locked_overrides(
            "team",
            team_path,
            _extract_override_payload(_load_yaml_mapping(team_path)),
            locked_paths,
            errors,
        )

    project_path = _resolve_override_path(PROJECT_DIR, project)
    if project_path and project_path.exists() and locked_paths:
        _validate_locked_overrides(
            "project",
            project_path,
            _extract_override_payload(_load_yaml_mapping(project_path)),
            locked_paths,
            errors,
        )

    allocation = effective.get("scoring", {}).get("allocation", {})
    total_weight = sum(
        float(allocation.get(key, 0.0))
        for key in (
            "skill_weight",
            "availability_weight",
            "track_record_weight",
            "team_fit_weight",
        )
    )
    if abs(total_weight - 1.0) > 0.01:
        errors.append(f"Allocation scoring weights must sum to 1.0, got {total_weight:.3f}.")

    allocation_rules = effective.get("rules", {}).get("allocation", {})
    max_load = float(allocation_rules.get("max_load_threshold", 0.0))
    min_skill = float(allocation_rules.get("min_skill_threshold", 0.0))
    max_projects = int(allocation_rules.get("max_concurrent_projects", 0))
    if max_load <= 0 or max_load > 1.0:
        errors.append("`rules.allocation.max_load_threshold` must be between 0 and 1.")
    if min_skill < 0 or min_skill > 1.0:
        errors.append("`rules.allocation.min_skill_threshold` must be between 0 and 1.")
    if max_projects < 1:
        errors.append("`rules.allocation.max_concurrent_projects` must be at least 1.")

    jira_config = effective.get("connectors", {}).get("jira", {})
    if jira_config.get("enabled") and not jira_config.get("base_url"):
        warnings.append("JIRA connector is enabled but no base URL is configured.")
    confluence_config = effective.get("connectors", {}).get("confluence", {})
    if confluence_config.get("enabled") and not confluence_config.get("base_url"):
        warnings.append("Confluence connector is enabled but no base URL is configured.")
    servicenow_config = effective.get("connectors", {}).get("servicenow", {})
    if servicenow_config.get("enabled") and not servicenow_config.get("base_url"):
        warnings.append("ServiceNow connector is enabled but no base URL is configured.")

    return ConfigValidationResult(checked_paths=checked_paths, warnings=warnings, errors=errors)


def mask_secrets(config: dict[str, Any]) -> dict[str, Any]:
    def _mask(value: Any) -> Any:
        if isinstance(value, dict):
            masked: dict[str, Any] = {}
            for key, nested in value.items():
                if isinstance(nested, str) and nested and any(
                    token in key.lower() for token in ("token", "secret", "password")
                ):
                    masked[key] = "********"
                else:
                    masked[key] = _mask(nested)
            return masked
        if isinstance(value, list):
            return [_mask(item) for item in value]
        return value

    return _mask(copy.deepcopy(config))
