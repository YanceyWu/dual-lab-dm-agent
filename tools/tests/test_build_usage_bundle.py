from __future__ import annotations

import importlib.util
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "tools" / "build_usage_bundle.py"
sys.path.insert(0, str(ROOT / "tools"))
SPEC = importlib.util.spec_from_file_location("build_usage_bundle", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
build_usage_bundle = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = build_usage_bundle
SPEC.loader.exec_module(build_usage_bundle)


def _sqlite_db(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE marker (id INTEGER PRIMARY KEY, value TEXT)")
        connection.execute("INSERT INTO marker(value) VALUES ('demo')")
        connection.commit()
    return path


def _fake_artifacts(tmp_path: Path) -> build_usage_bundle.BundleArtifacts:
    wheel = tmp_path / "ai_pm_agent-0.2.0rc1-py3-none-any.whl"
    sdist = tmp_path / "ai_pm_agent-0.2.0rc1.tar.gz"
    demo_db = _sqlite_db(tmp_path / "sample_pm.db")
    wheel.write_bytes(b"wheel")
    sdist.write_bytes(b"sdist")
    return build_usage_bundle.BundleArtifacts(wheel=wheel, sdist=sdist, demo_db=demo_db)


def _stage_bundle(tmp_path: Path, target_key: str = "macos") -> tuple[Path, object]:
    bundle_dir = tmp_path / f"{target_key}-bundle"
    target = build_usage_bundle.default_targets()[target_key]
    build_usage_bundle.stage_bundle_tree(
        bundle_dir,
        target,
        _fake_artifacts(tmp_path),
    )
    return bundle_dir, target


def _run_install_helper(bundle_dir: Path, *, first_install: bool = False) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        str(bundle_dir / "scripts" / "install-helper.py"),
        "--bundle-root",
        str(bundle_dir),
    ]
    if first_install:
        command.append("--first-install")
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )


def test_stage_bundle_tree_builds_slice4_trial_workspace(tmp_path: Path) -> None:
    bundle_dir, _ = _stage_bundle(tmp_path)

    assert (bundle_dir / "README.md").exists()
    assert (bundle_dir / ".gitignore").exists()
    assert (bundle_dir / ".github/agents/delivery-manager.agent.md").exists()
    assert (bundle_dir / ".github/copilot-instructions.md").exists()
    assert (bundle_dir / ".github/prompts/dm-workload.prompt.md").exists()
    assert (bundle_dir / "src/pm_agent").is_dir()
    assert (bundle_dir / "src/configs").is_dir()
    assert (bundle_dir / "src/scripts").is_dir()
    assert (bundle_dir / "src/scripts/init_db.py").exists()
    assert (bundle_dir / "scripts/install.command").exists()
    assert (bundle_dir / "scripts/open-in-vscode.command").exists()
    assert (bundle_dir / "scripts/install-helper.py").exists()
    assert (bundle_dir / "demo/sample_pm.db").exists()
    assert (bundle_dir / "demo/sample_pm.db").stat().st_mode & 0o222 == 0
    assert (bundle_dir / "artifacts/ai_pm_agent-0.2.0rc1-py3-none-any.whl").exists()
    assert (bundle_dir / "wheelhouse").is_dir()
    assert not (bundle_dir / "src/tests").exists()
    assert not (bundle_dir / "src/sample-data").exists()
    assert not (bundle_dir / "tools").exists()
    assert not (bundle_dir / "docs").exists()
    assert not (bundle_dir / "src/scripts/load_sample_data.py").exists()
    assert not (bundle_dir / "src/scripts/seed_demo_evidence.py").exists()

    root_readme = (bundle_dir / "README.md").read_text(encoding="utf-8")
    runtime_readme = (bundle_dir / "src/README.md").read_text(encoding="utf-8")
    bundle_agent = (
        bundle_dir / ".github/agents/delivery-manager.agent.md"
    ).read_text(encoding="utf-8")
    copilot_instructions = (
        bundle_dir / ".github/copilot-instructions.md"
    ).read_text(encoding="utf-8")

    assert root_readme.startswith("# Delivery Manager Trial Bundle")
    assert "## Choose your first run path" in root_readme
    assert "### Try demo" in root_readme
    assert "### Use local data" in root_readme
    assert root_readme.index("## Install locally") < root_readme.index("## Open in VS Code")
    assert root_readme.index("## Open in VS Code") < root_readme.index("## Choose your first run path")
    assert root_readme.index("### Try demo") < root_readme.index("### Use local data")
    assert root_readme.count("**When to choose it:**") == 2
    assert root_readme.count("**Do this:**") == 2
    assert root_readme.count("**Then:**") == 2
    assert "DATABASE_PATH=.dm-demo/sample_pm.db" in root_readme
    assert "DATABASE_PATH=data/pm.db" in root_readme
    assert "## Included" not in root_readme
    assert "## Normal operator flow" not in root_readme

    assert "## Structured data onboarding" in runtime_readme
    assert "pm onboarding profile save" in runtime_readme
    assert "pm onboarding preview" in runtime_readme
    assert "pm onboarding confirm" in runtime_readme
    assert "pm onboarding run show" in runtime_readme
    assert "DATABASE_PATH=.dm-demo/sample_pm.db" in runtime_readme
    assert "DATABASE_PATH=data/pm.db" in runtime_readme
    assert build_usage_bundle.PHASE1_LEGACY_PAGES_TEXT in runtime_readme

    assert build_usage_bundle.PHASE1_LEGACY_PAGES_TEXT in bundle_agent
    assert build_usage_bundle.PHASE1_LEGACY_PAGES_TEXT in copilot_instructions
    assert "open it in VS Code" in bundle_agent
    assert "open this workspace\nin VS Code" in copilot_instructions
    for out_of_scope_label in (
        "Management Attention",
        "Action Follow-up",
        "Weekly DM brief",
    ):
        assert out_of_scope_label in bundle_agent
    for experimental_token in (
        "delivery-attention-center",
        "management-attention",
        "resource-capacity-heatmap",
        "weekly-dm-brief",
        "weekly-brief-v2",
        "delivery-execution-review",
        "layered-project-health-review",
        "connector-status-review",
        "project-snapshot-list",
    ):
        assert experimental_token not in bundle_agent


def test_stage_bundle_tree_writes_manifest_and_install_metadata(tmp_path: Path) -> None:
    bundle_dir, target = _stage_bundle(tmp_path, target_key="windows")

    manifest = json.loads(
        (bundle_dir / build_usage_bundle.BUNDLE_MANIFEST).read_text(encoding="utf-8")
    )
    manifest_paths = {record["path"] for record in manifest["files"]}

    assert manifest["platform"]["key"] == "windows"
    assert manifest["platform"]["architecture"] == "amd64"
    assert manifest["platform"]["python_version"] == "3.12"
    assert manifest["offline_wheelhouse_included"] is False
    assert manifest["install_script"] == "scripts/install.cmd"
    assert manifest["open_script"] == "scripts/open-in-vscode.cmd"
    assert manifest["demo_db_source"] == "generated_from_synthetic_loader"
    assert "README.md" in manifest_paths
    assert ".github/copilot-instructions.md" in manifest_paths
    assert "src/README.md" in manifest_paths
    assert "demo/sample_pm.db" in manifest_paths
    assert "scripts/install-helper.py" in manifest_paths
    assert "artifacts/ai_pm_agent-0.2.0rc1-py3-none-any.whl" in manifest_paths
    assert not any(path.startswith("src/sample-data/") for path in manifest_paths)

    install_script = (bundle_dir / target.install_script).read_text(encoding="utf-8")
    assert "if errorlevel 1 goto :python_executable_check" in install_script
    assert "if not errorlevel 1 set \"PYTHON=py -3.12\"" in install_script
    assert "in ('amd64', 'x86_64')" in install_script
    assert "init --skip-db" in install_script
    assert "install-helper.py" in install_script
    assert "HELPER_FLAG=--first-install" in install_script


def test_install_helper_sets_demo_mode_on_first_install(tmp_path: Path) -> None:
    bundle_dir, _ = _stage_bundle(tmp_path)
    env_path = bundle_dir / "src/.env"
    env_path.write_text(
        "DATABASE_PATH=data/pm.db\nLOG_LEVEL=INFO\n",
        encoding="utf-8",
    )

    result = _run_install_helper(bundle_dir, first_install=True)

    assert result.returncode == 0, result.stderr
    assert env_path.read_text(encoding="utf-8").startswith(
        "DATABASE_PATH=.dm-demo/sample_pm.db\n"
    )
    assert (bundle_dir / "src/.dm-demo/sample_pm.db").exists()
    assert "src/.env now uses DATABASE_PATH=.dm-demo/sample_pm.db." in result.stdout


def test_install_helper_preserves_non_demo_database_path(tmp_path: Path) -> None:
    bundle_dir, _ = _stage_bundle(tmp_path)
    env_path = bundle_dir / "src/.env"
    original_env = "DATABASE_PATH=data/pm.db\nLOG_LEVEL=INFO\n"
    env_path.write_text(original_env, encoding="utf-8")

    result = _run_install_helper(bundle_dir)

    assert result.returncode == 0, result.stderr
    assert env_path.read_text(encoding="utf-8") == original_env
    assert (bundle_dir / "src/.dm-demo/sample_pm.db").exists()
    assert "preserved existing non-demo DATABASE_PATH" in result.stdout


def test_install_helper_rejects_duplicate_database_path_entries(tmp_path: Path) -> None:
    bundle_dir, _ = _stage_bundle(tmp_path)
    env_path = bundle_dir / "src/.env"
    original_env = (
        "DATABASE_PATH=data/pm.db\n"
        "LOG_LEVEL=INFO\n"
        "DATABASE_PATH=.dm-demo/sample_pm.db\n"
    )
    env_path.write_text(original_env, encoding="utf-8")

    result = _run_install_helper(bundle_dir, first_install=True)

    assert result.returncode != 0
    assert "INSTALL_HELPER_DATABASE_PATH_DUPLICATE" in result.stderr
    assert env_path.read_text(encoding="utf-8") == original_env
    assert not (bundle_dir / "src/.dm-demo/sample_pm.db").exists()


def test_install_helper_rolls_back_new_demo_copy_on_env_write_failure(tmp_path: Path) -> None:
    bundle_dir, _ = _stage_bundle(tmp_path)
    env_path = bundle_dir / "src/.env"
    env_path.write_text("DATABASE_PATH=data/pm.db\n", encoding="utf-8")
    (bundle_dir / "src/.env.tmp").mkdir()

    result = _run_install_helper(bundle_dir, first_install=True)

    assert result.returncode != 0
    assert "INSTALL_HELPER_ENV_WRITE_FAILED" in result.stderr
    assert env_path.read_text(encoding="utf-8") == "DATABASE_PATH=data/pm.db\n"
    assert not (bundle_dir / "src/.dm-demo/sample_pm.db").exists()


def test_validate_bundle_tree_rejects_dev_entries(tmp_path: Path) -> None:
    bundle_dir, target = _stage_bundle(tmp_path)
    (bundle_dir / "docs").mkdir()

    try:
        build_usage_bundle.validate_bundle_tree(
            bundle_dir,
            target,
            require_wheelhouse=False,
        )
    except RuntimeError as exc:
        assert str(exc) == "BUNDLE_CONTAINS_DEV_ENTRY:docs"
    else:
        raise AssertionError("expected RuntimeError")
