from __future__ import annotations

import json
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class ScoringWeights(BaseSettings):
    """
    Allocation scoring weights — must sum to 1.0.
    Override any value via .env (e.g. SKILL_WEIGHT=0.40).
    """

    skill_weight: float = 0.35
    availability_weight: float = 0.30
    track_record_weight: float = 0.20
    team_fit_weight: float = 0.15

    @model_validator(mode="after")
    def weights_sum_to_one(self) -> "ScoringWeights":
        total = (
            self.skill_weight
            + self.availability_weight
            + self.track_record_weight
            + self.team_fit_weight
        )
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Scoring weights must sum to 1.0, got {total:.3f}")
        return self


class HardRules(BaseSettings):
    """Hard-rule thresholds — one violation = candidate excluded."""

    max_load_threshold: float = 1.0       # 100% load = excluded
    min_skill_threshold: float = 0.20     # below 20% skill match = excluded
    max_concurrent_projects: int = 2      # more than N active projects = excluded


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_path: str = "data/pm.db"
    log_level: str = "INFO"

    jira_base_url: str = ""
    jira_user_email: str = ""
    jira_api_token: str = ""
    jira_verify_ssl: bool = True

    confluence_base_url: str = ""
    confluence_email: str = ""
    confluence_api_token: str = ""
    confluence_cloud_id: str = ""
    confluence_action_tracker_page_id: str = ""
    confluence_verify_ssl: bool = True

    atlassian_client_id: str = ""
    atlassian_client_secret: str = ""
    atlassian_refresh_token: str = ""
    atlassian_cloud_id: str = ""

    snow_base_url: str = ""
    snow_report_id: str = ""
    snow_browser: str = "edge"
    snow_browser_profile: str = ""

    project_alias_groups_json: str = "[]"

    # Nested config — values read from same .env
    scoring: ScoringWeights = ScoringWeights()
    rules: HardRules = HardRules()

    @model_validator(mode="after")
    def normalize_paths(self) -> "Settings":
        db_path = Path(self.database_path)
        if not db_path.is_absolute():
            self.database_path = str((PROJECT_ROOT / db_path).resolve())
        return self

    def project_alias_groups(self) -> list[set[str]]:
        """Return locally configured project aliases as normalized string sets."""
        try:
            raw_groups = json.loads(self.project_alias_groups_json or "[]")
        except json.JSONDecodeError as exc:
            raise ValueError("PROJECT_ALIAS_GROUPS_JSON must contain valid JSON") from exc
        if not isinstance(raw_groups, list):
            raise ValueError("PROJECT_ALIAS_GROUPS_JSON must be a JSON list")

        groups: list[set[str]] = []
        for raw_group in raw_groups:
            if not isinstance(raw_group, list) or not all(
                isinstance(value, str) for value in raw_group
            ):
                raise ValueError(
                    "Each PROJECT_ALIAS_GROUPS_JSON item must be a list of strings"
                )
            group = {value.strip() for value in raw_group if value.strip()}
            if group:
                groups.append(group)
        return groups


# Singleton — import this everywhere
settings = Settings()


def get_database_path() -> Path:
    """Resolve the current database setting at call time.

    Tests and local tools can safely redirect ``settings.database_path`` after
    module import. Callers must not cache the result at module scope.
    """
    db_path = Path(settings.database_path)
    if not db_path.is_absolute():
        db_path = PROJECT_ROOT / db_path
    return db_path.resolve()
