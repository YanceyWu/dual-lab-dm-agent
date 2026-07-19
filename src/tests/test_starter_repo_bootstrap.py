from __future__ import annotations

from pathlib import Path

from pm_agent.config import settings
from pm_agent.repo_tools import bootstrap


def _redirect_bootstrap_paths(monkeypatch, root: Path) -> None:
    config_root = root / "configs"
    monkeypatch.setattr(bootstrap, "ENV_EXAMPLE_PATH", root / ".env.example")
    monkeypatch.setattr(bootstrap, "ENV_PATH", root / ".env")
    monkeypatch.setattr(bootstrap, "CONFIG_ROOT", config_root)
    monkeypatch.setattr(bootstrap, "COMPANY_DIR", config_root / "company")
    monkeypatch.setattr(bootstrap, "TEAM_DIR", config_root / "teams")
    monkeypatch.setattr(bootstrap, "PROJECT_DIR", config_root / "projects")
    monkeypatch.setattr(bootstrap, "COMPANY_BASELINE_PATH", config_root / "company" / "baseline.yaml")
    monkeypatch.setattr(bootstrap, "LOCKED_CONTROLS_PATH", config_root / "company" / "locked-controls.yaml")
    monkeypatch.setattr(bootstrap, "EXAMPLE_TEAM_PATH", config_root / "teams" / "example-team.yaml")
    monkeypatch.setattr(bootstrap, "EXAMPLE_PROJECT_PATH", config_root / "projects" / "example-project.yaml")
    monkeypatch.setattr(settings, "database_path", str(root / "data" / "pm.db"))


def test_starter_bootstrap_scaffolds_only_generic_defaults(tmp_path: Path, monkeypatch) -> None:
    _redirect_bootstrap_paths(monkeypatch, tmp_path)
    bootstrap.ENV_EXAMPLE_PATH.write_text(
        "DATABASE_PATH=data/pm.db\nJIRA_BASE_URL=\nSNOW_BASE_URL=\n",
        encoding="utf-8",
    )

    result = bootstrap.initialize_starter_repo(skip_db=True)

    generated_env = (tmp_path / ".env").read_text(encoding="utf-8")
    baseline = (tmp_path / "configs" / "company" / "baseline.yaml").read_text(encoding="utf-8")
    assert result.database_initialized is False
    assert generated_env == "DATABASE_PATH=data/pm.db\nJIRA_BASE_URL=\nSNOW_BASE_URL=\n"
    assert "Example Organization" in baseline
    assert "base_url: \"\"" in baseline
    assert not any(
        "http://" in status.path.read_text(encoding="utf-8") for status in result.created
    )


def test_starter_bootstrap_never_overwrites_existing_env_by_default(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _redirect_bootstrap_paths(monkeypatch, tmp_path)
    bootstrap.ENV_EXAMPLE_PATH.write_text("DATABASE_PATH=data/pm.db\n", encoding="utf-8")
    existing_env = tmp_path / ".env"
    existing_env.write_text("DATABASE_PATH=private/location.db\n", encoding="utf-8")

    result = bootstrap.initialize_starter_repo(skip_db=True)

    assert existing_env.read_text(encoding="utf-8") == "DATABASE_PATH=private/location.db\n"
    assert [status.label for status in result.reused] == [".env"]
