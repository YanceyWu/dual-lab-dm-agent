from __future__ import annotations

import importlib.util
import json
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


def _fake_artifacts(tmp_path: Path) -> tuple[Path, Path]:
    wheel = tmp_path / "ai_pm_agent-0.2.0rc1-py3-none-any.whl"
    sdist = tmp_path / "ai_pm_agent-0.2.0rc1.tar.gz"
    wheel.write_bytes(b"wheel")
    sdist.write_bytes(b"sdist")
    return wheel, sdist


def test_stage_bundle_tree_builds_trimmed_workspace(tmp_path: Path) -> None:
    bundle_dir = tmp_path / "macos-bundle"
    build_usage_bundle.stage_bundle_tree(
        bundle_dir,
        build_usage_bundle.default_targets()["macos"],
        _fake_artifacts(tmp_path),
    )

    assert (bundle_dir / "README.md").exists()
    assert (bundle_dir / ".gitignore").exists()
    assert (bundle_dir / ".github/agents/delivery-manager.agent.md").exists()
    assert (bundle_dir / ".github/copilot-instructions.md").exists()
    assert (bundle_dir / ".github/prompts/dm-workload.prompt.md").exists()
    assert (bundle_dir / "src/pm_agent").is_dir()
    assert (bundle_dir / "src/configs").is_dir()
    assert (bundle_dir / "src/scripts").is_dir()
    assert (bundle_dir / "src/scripts/init_db.py").exists()
    assert not (bundle_dir / "src/scripts/import_workforce_planning.py").exists()
    assert (bundle_dir / "scripts/install.command").exists()
    assert (bundle_dir / "scripts/open-in-vscode.command").exists()
    assert (bundle_dir / "artifacts/ai_pm_agent-0.2.0rc1-py3-none-any.whl").exists()
    assert (bundle_dir / "wheelhouse").is_dir()
    assert not (bundle_dir / "src/tests").exists()
    assert not (bundle_dir / "src/sample-data").exists()
    assert not (bundle_dir / "tools").exists()
    assert not (bundle_dir / "docs").exists()
    assert not (bundle_dir / "src/scripts/load_sample_data.py").exists()
    assert not (bundle_dir / "src/scripts/seed_demo_evidence.py").exists()


def test_stage_bundle_tree_writes_manifest_and_runtime_metadata(tmp_path: Path) -> None:
    bundle_dir = tmp_path / "windows-bundle"
    target = build_usage_bundle.default_targets()["windows"]
    build_usage_bundle.stage_bundle_tree(
        bundle_dir,
        target,
        _fake_artifacts(tmp_path),
    )

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
    assert "README.md" in manifest_paths
    assert ".github/copilot-instructions.md" in manifest_paths
    assert "src/README.md" in manifest_paths
    assert "artifacts/ai_pm_agent-0.2.0rc1-py3-none-any.whl" in manifest_paths

    install_script = (bundle_dir / "scripts/install.cmd").read_text(encoding="utf-8")
    assert "if errorlevel 1 goto :python_executable_check" in install_script
    assert "if not errorlevel 1 set \"PYTHON=py -3.12\"" in install_script
    assert "in ('amd64', 'x86_64')" in install_script


def test_validate_bundle_tree_rejects_dev_entries(tmp_path: Path) -> None:
    bundle_dir = tmp_path / "bundle"
    target = build_usage_bundle.default_targets()["macos"]
    build_usage_bundle.stage_bundle_tree(
        bundle_dir,
        target,
        _fake_artifacts(tmp_path),
    )

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
