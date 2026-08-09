from __future__ import annotations

import importlib.util
import json
import os
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

MODULE_PATH = ROOT / "tools" / "build_usage_bundle.py"
sys.path.insert(0, str(ROOT / "tools"))
SPEC = importlib.util.spec_from_file_location("build_usage_bundle", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
bundle = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = bundle
SPEC.loader.exec_module(bundle)


def artifacts(tmp_path: Path) -> object:
    database = tmp_path / "sample_pm.db"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE marker (id INTEGER PRIMARY KEY)")
    return bundle.BundleArtifacts(demo_db=database)


def parse_bundle_workbook(path: Path) -> object:
    """Load the runtime parser only inside this tool-test helper.

    Tool tests are intentionally runnable without an editable runtime install.
    """
    source_root = str(ROOT / "src")
    sys.path.insert(0, source_root)
    try:
        from pm_agent.workbook_onboarding.parser import parse_workbook

        return parse_workbook(path)
    finally:
        sys.path.remove(source_root)


def stage(tmp_path: Path) -> Path:
    target = tmp_path / "Delivery Manager"
    bundle.stage_bundle_tree(target, artifacts(tmp_path))
    return target


def import_generated(path: Path, name: str) -> object:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def setup_modules(tmp_path: Path) -> tuple[Path, object, object]:
    target = stage(tmp_path)
    setup = import_generated(target / "scripts/setup.py", "generated_setup")
    installer = import_generated(
        target / "scripts/install-helper.py", "generated_installer"
    )
    return target, setup, installer


def successful_runner(root: Path, *, fail_command: tuple[str, ...] | None = None):
    calls: list[list[str]] = []

    def runner(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        assert cwd == root
        calls.append(command)
        if command[1:3] == ["-m", "venv"]:
            python = root / ".venv/bin/python"
            pm = root / ".venv/bin/pm"
            python.parent.mkdir(parents=True, exist_ok=True)
            python.write_text("", encoding="utf-8")
            pm.write_text("", encoding="utf-8")
        if command[1:] == ["init", "--skip-db"]:
            (root / "src/.env").write_text(
                "DATABASE_PATH=data/pm.db\n", encoding="utf-8"
            )
        if command[1:] == ["init"]:
            database = root / "src/data/pm.db"
            database.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(database) as connection:
                connection.execute("CREATE TABLE employees (id TEXT)")
                connection.execute("CREATE TABLE projects (id TEXT)")
                connection.execute("CREATE TABLE plan_versions (id TEXT)")
                connection.execute("CREATE TABLE monthly_allocations (id TEXT)")
        returncode = 1 if fail_command and tuple(command[1:]) == fail_command else 0
        stderr = "opaque private detail" if returncode else ""
        return subprocess.CompletedProcess(command, returncode, stderr=stderr)

    return runner, calls


def test_generated_setup_marks_complete_only_after_all_smokes_pass(
    tmp_path: Path,
) -> None:
    target, setup, _ = setup_modules(tmp_path)
    runner, calls = successful_runner(target)

    def initializer(
        root: Path, python: Path, mode: str, command_runner: object
    ) -> None:
        assert mode == "demo"
        (root / "src/.env").write_text(
            "DATABASE_PATH=.dm-demo/sample_pm.db\n", encoding="utf-8"
        )

    state, detail = setup.install(
        target, "demo", runner=runner, initializer=initializer, version=(3, 12)
    )

    assert (state, detail) == ("already_installed", {"mode": "demo"})
    marker = json.loads((target / setup.MARKER).read_text(encoding="utf-8"))
    assert marker["mode"] == "demo"
    assert not (target / f"{setup.MARKER}.tmp").exists()
    assert [call[1:] for call in calls[-3:]] == [
        ["config", "validate"],
        ["tool", "query", "team-workload-overview"],
        ["tool", "query", "project-health-review"],
    ]


def test_generated_setup_smoke_failure_is_sanitized_and_never_marks_complete(
    tmp_path: Path,
) -> None:
    target, setup, _ = setup_modules(tmp_path)
    runner, _ = successful_runner(
        target, fail_command=("tool", "query", "team-workload-overview")
    )

    state, detail = setup.install(
        target,
        "demo",
        runner=runner,
        version=(3, 12),
        initializer=lambda root, python, mode, command_runner: (
            root / "src/.env"
        ).write_text("DATABASE_PATH=.dm-demo/sample_pm.db\n", encoding="utf-8"),
    )

    assert state == "partial_install"
    assert detail["code"] == "smoke_validation_failed"
    assert "private" not in json.dumps(detail)
    assert not (target / setup.MARKER).exists()


def test_generated_setup_existing_healthy_is_already_installed(tmp_path: Path) -> None:
    target, setup, _ = setup_modules(tmp_path)
    lock = target / "src/runtime-requirements.lock"
    pm = target / ".venv/bin/pm"
    pm.parent.mkdir(parents=True)
    pm.write_text("", encoding="utf-8")
    (target / setup.MARKER).write_text(
        json.dumps({"lock_sha256": setup.digest(lock), "mode": "demo"}) + "\n", encoding="utf-8"
    )
    (target / "src/.env").write_text(
        "DATABASE_PATH=.dm-demo/sample_pm.db\n", encoding="utf-8"
    )
    runner, calls = successful_runner(target)

    state, detail = setup.install(target, "demo", runner=runner, version=(3, 12))

    assert (state, detail) == ("already_installed", {"mode": "demo"})
    assert len(calls) == 4


def test_generated_setup_partial_requires_repair_and_repair_recovers(
    tmp_path: Path,
) -> None:
    target, setup, _ = setup_modules(tmp_path)
    (target / ".venv").mkdir()
    runner, _ = successful_runner(target)

    state, detail = setup.install(target, "demo", runner=runner, version=(3, 12))
    assert state == "partial_install"
    assert detail["repair"] == "request explicit repair"

    state, detail = setup.install(
        target,
        "demo",
        runner=runner,
        repair=True,
        version=(3, 12),
        initializer=lambda root, python, mode, command_runner: (
            root / "src/.env"
        ).write_text("DATABASE_PATH=.dm-demo/sample_pm.db\n", encoding="utf-8"),
    )
    assert (state, detail) == ("already_installed", {"mode": "demo"})
    assert (target / setup.MARKER).is_file()


def test_generated_setup_local_mode_creates_empty_database(tmp_path: Path) -> None:
    target, setup, _ = setup_modules(tmp_path)
    runner, _ = successful_runner(target)

    state, detail = setup.install(
        target,
        "local",
        runner=runner,
        version=(3, 12),
        initializer=lambda root, python, mode, command_runner: (
            root / "src/.env"
        ).write_text("DATABASE_PATH=data/pm.db\n", encoding="utf-8"),
    )

    assert (state, detail) == ("already_installed", {"mode": "local"})
    database = target / "src/data/pm.db"
    assert database.is_file()
    with sqlite3.connect(database) as connection:
        assert connection.execute("PRAGMA integrity_check").fetchone() == ("ok",)


def test_generated_installer_demo_copy_is_atomic_hashed_and_sqlite_checked(
    tmp_path: Path,
) -> None:
    target, _, installer = setup_modules(tmp_path)
    env = target / "src/.env"
    env.write_text("DATABASE_PATH=data/pm.db\n", encoding="utf-8")
    replacements: list[tuple[Path, Path]] = []

    def replace(source: Path, destination: Path) -> None:
        replacements.append((source, destination))
        os.replace(source, destination)

    message = installer.configure(target, "demo", replace=replace)
    destination = target / "src/.dm-demo/sample_pm.db"
    assert message == "SETUP_DEMO_READY: synthetic demo selected."
    assert replacements == [
        (destination.with_name("sample_pm.db.tmp"), destination),
        (env.with_name(".env.tmp"), env),
    ]
    assert installer.sha256(target / "demo/sample_pm.db") == installer.sha256(
        destination
    )
    with sqlite3.connect(destination) as connection:
        assert connection.execute("PRAGMA integrity_check").fetchone() == ("ok",)
    assert not destination.with_name("sample_pm.db.tmp").exists()


def test_generated_setup_install_rechecks_the_requested_python_version(
    tmp_path: Path,
) -> None:
    target, setup, _ = setup_modules(tmp_path)
    runner, calls = successful_runner(target)

    state, detail = setup.install(target, "demo", runner=runner, version=(3, 11))

    assert state == "python_unsupported"
    assert detail["detected"] == "3.11"
    assert calls == []


def test_generated_setup_main_emits_one_sanitized_json_for_each_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    target, setup, _ = setup_modules(tmp_path)
    cases = (
        (("ready_to_install", {}), ("already_installed", {"mode": "demo"})),
        (
            (
                "partial_install",
                {"code": "opaque", "repair": "request explicit repair"},
            ),
            None,
        ),
        (
            (
                "partial_install",
                {"code": "opaque", "repair": "request explicit repair"},
            ),
            ("already_installed", {"mode": "demo"}),
        ),
        (("failed", {"code": "workspace_not_writable"}), None),
    )
    arguments = (
        ["--bundle-root", str(target), "--install", "--mode", "demo"],
        ["--bundle-root", str(target), "--install", "--mode", "demo"],
        ["--bundle-root", str(target), "--install", "--repair", "--mode", "demo"],
        ["--bundle-root", str(target), "--install", "--mode", "demo"],
    )
    for (preflight_state, install_state), argv in zip(cases, arguments, strict=True):
        monkeypatch.setattr(
            setup,
            "preflight",
            lambda root, state=preflight_state, **kwargs: state,
        )
        if install_state is not None:
            monkeypatch.setattr(
                setup,
                "install",
                lambda root, mode, repair=False, state=install_state: state,
            )
        assert setup.main(argv) == 0
        lines = capsys.readouterr().out.splitlines()
        assert len(lines) == 1
        payload = json.loads(lines[0])
        assert "private" not in lines[0]
        assert payload["state"] in {"already_installed", "partial_install", "failed"}


def test_generated_setup_windows_path_and_agent_never_fall_back_to_unix_or_bare_pm(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target, setup, _ = setup_modules(tmp_path)
    monkeypatch.setattr(setup.sys, "platform", "win32")
    assert setup.pm_path(target) == target / ".venv/Scripts/pm.exe"
    agent = (target / ".github/agents/delivery-manager.agent.md").read_text(
        encoding="utf-8"
    )
    assert "<workspace-pm>" in agent
    assert "& .\\.venv\\Scripts\\pm.exe" in agent
    assert (
        ".venv/bin/pm tool query interaction-memory-context --param-stdin message"
        in agent
    )
    assert "subprocess.run(..., input=<user turn>, text=True)" in agent
    for setup_constraint in (
        "python_missing",
        "python_unsupported",
        "Never automatically invoke brew, winget, choco, apt",
        "never request admin/sudo",
        "modify machine-wide Python",
        "install global packages",
    ):
        assert setup_constraint in agent
    for semantic in (
        "working_context.answer_preferences",
        "working_context.routing_hints",
        "working_context.follow_up_hints",
        "working_context.strategy_flags",
        "override a clear business intent",
        "invent parameters, IDs, time periods, teams, or connector names",
        "business facts/evidence/freshness",
        "only when that project ID is already known",
    ):
        assert semantic in agent
    assert "otherwise use `pm`" not in agent
    assert "`pm " not in agent
    assert "`pm`" not in agent
    assert "same pattern with\n`pm tool query" not in agent
    assert not re.search(r"(?m)^\s*pm\s", agent)
    assert not re.search(r"(?m)\|\s*pm\s", agent)


def test_generated_installer_env_selector_is_atomic_and_repair_restores_invalid_env(
    tmp_path: Path,
) -> None:
    target, setup, installer = setup_modules(tmp_path)
    env = target / "src/.env"
    original = "DATABASE_PATH=data/pm.db\n"
    env.write_text(original, encoding="utf-8")
    with pytest.raises(OSError):
        installer.configure(
            target,
            "demo",
            replace=lambda source, destination: (_ for _ in ()).throw(
                OSError("no write")
            ),
        )
    assert env.read_text(encoding="utf-8") == original
    assert not env.with_name(".env.tmp").exists()

    env.write_text("truncated", encoding="utf-8")
    (target / ".venv").mkdir()
    runner, _ = successful_runner(target)
    state, detail = setup.install(
        target,
        "demo",
        runner=runner,
        repair=True,
        version=(3, 12),
        initializer=lambda root, python, mode, command_runner: None,
    )
    assert (state, detail) == ("already_installed", {"mode": "demo"})
    assert "DATABASE_PATH=" in env.read_text(encoding="utf-8")


def test_generated_setup_classifies_network_only_for_dependency_install(
    tmp_path: Path,
) -> None:
    target, setup, _ = setup_modules(tmp_path)

    def failed(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 1, stderr="connection failed")

    with pytest.raises(RuntimeError, match="package_index_unavailable"):
        setup.run(["python", "-m", "pip", "install", "-r", "lock"], target, failed)
    with pytest.raises(RuntimeError, match="configuration_validation_failed"):
        setup.run(["pm", "config", "validate"], target, failed)
    with pytest.raises(RuntimeError, match="smoke_validation_failed"):
        setup.run(["pm", "tool", "query", "team-workload-overview"], target, failed)
    with pytest.raises(RuntimeError, match="initialization_failed"):
        setup.run(["pm", "init"], target, failed)
    with pytest.raises(RuntimeError, match="initialization_failed"):
        setup.run(
            ["python", str(target / "scripts/install-helper.py"), "--mode", "demo"],
            target,
            failed,
        )


def test_generated_setup_main_handles_malformed_marker_and_runner_oserror_as_json(
    tmp_path: Path,
) -> None:
    target, setup, _ = setup_modules(tmp_path)
    pm = target / ".venv/bin/pm"
    pm.parent.mkdir(parents=True)
    pm.write_text("", encoding="utf-8")
    for marker in ("[]", "{}"):
        (target / setup.MARKER).write_text(marker, encoding="utf-8")
        result = subprocess.run(
            [
                sys.executable,
                str(target / "scripts/setup.py"),
                "--bundle-root",
                str(target),
                "--preflight",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        assert result.returncode == 0
        assert result.stderr == ""
        lines = result.stdout.splitlines()
        assert len(lines) == 1
        assert json.loads(lines[0])["state"] == "partial_install"

    state, detail = setup.install(
        target,
        "demo",
        runner=lambda command, cwd: (_ for _ in ()).throw(OSError("private path")),
        repair=True,
        version=(3, 12),
    )
    assert state == "partial_install"
    assert detail["code"] == "command_execution_failed"
    assert "private" not in json.dumps(detail)


def test_stage_bundle_tree_is_single_lean_workspace(tmp_path: Path) -> None:
    target = stage(tmp_path)
    assert {item.name for item in target.iterdir()} == bundle.ROOT_ALLOWLIST
    assert (target / "README.md").is_file()
    assert (target / "scripts/setup.py").is_file()
    assert (target / "scripts/install-helper.py").is_file()
    assert (target / "src/runtime-requirements.lock").is_file()
    assert not (target / "src/README.md").exists()
    assert (target / "workbook/WORKBOOK_GUIDE.md").is_file()
    assert parse_bundle_workbook(
        target / "workbook/team_project_capacity_workbook_template.xlsx"
    )
    assert parse_bundle_workbook(
        target / "workbook/team_project_capacity_workbook_sample.xlsx"
    )
    assert (target / "sources/SOURCES_GUIDE.md").is_file()
    assert (target / "sources/project_profiles_template.xlsx").is_file()
    assert (target / "sources/project_profiles_sample.xlsx").is_file()
    assert (target / "sources/jira_board_registry_template.csv").is_file()
    assert (target / "sources/jira_board_configs.sample.csv").is_file()
    assert (target / "sources/confluence_page_registry_template.csv").is_file()
    assert (target / "sources/confluence_pages.sample.csv").is_file()
    for absent in (
        "artifacts",
        "wheelhouse",
        "src 2",
        ".venv",
        "src/tests",
        "src/sample-data",
        "src/configs",
        ".github/prompts/dm-workload.prompt.md",
    ):
        assert not (target / absent).exists()
    manifest = json.loads((target / bundle.BUNDLE_MANIFEST).read_text(encoding="utf-8"))
    assert manifest["dependency_mode"] == "online_locked"
    assert manifest["python_requirement"] == "3.12"
    assert manifest["demo_db_source"] == bundle.DEMO_DB_SOURCE
    assert manifest["source_identity"]["revision"]
    assert isinstance(manifest["source_identity"]["dirty"], bool)
    assert "README.md" in {item["path"] for item in manifest["files"]}


def test_generated_agent_has_setup_memory_readonly_and_registry_contract(
    tmp_path: Path,
) -> None:
    target = stage(tmp_path)
    agent = (target / ".github/agents/delivery-manager.agent.md").read_text(
        encoding="utf-8"
    )
    assert "--preflight" in agent
    assert "explicit request" in agent
    assert "partial_install" in agent
    assert "interaction memory" in agent
    assert "delivery-attention-center" in agent
    assert "resource-capacity-heatmap" in agent
    assert "jira-board-registry-csv" in agent
    assert "confluence-page-registry-csv" in agent
    assert "Do not open or summarize raw CSV" in agent
    assert bundle.PAGES in agent
    assert "<workspace-pm>" in agent
    assert ".venv/bin/pm" in agent
    assert ".venv\\Scripts\\pm.exe" in agent
    assert "--install --mode demo|local" in agent
    assert "--repair" in agent
    assert "src/.venv/bin/pm" not in agent
    assert "onboarding export-workbook" in agent
    assert "onboarding export-source" in agent
    assert "sources/SOURCES_GUIDE.md" in agent
    assert "switch from demo to local data" in agent
    assert "never open or quote workbook cells" in agent


def test_generated_setup_install_switches_demo_to_local_without_demo_queries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target, setup, installer = setup_modules(tmp_path)
    runner, _ = successful_runner(target)
    (target / "src/.env").write_text(
        "LOG_LEVEL=INFO\nDATABASE_PATH=.dm-demo/sample_pm.db\n", encoding="utf-8"
    )
    demo = target / "src/.dm-demo/sample_pm.db"
    demo.parent.mkdir(parents=True)
    demo.write_bytes(b"demo-bytes")
    demo_hash = setup.digest(demo)
    pm = target / ".venv/bin/pm"
    pm.parent.mkdir(parents=True)
    pm.write_text("", encoding="utf-8")
    (target / setup.MARKER).write_text(
        json.dumps({"lock_sha256": setup.digest(target / "src/runtime-requirements.lock"), "mode": "demo"}) + "\n",
        encoding="utf-8",
    )

    def no_demo_health(*args: object, **kwargs: object) -> bool:
        pytest.fail("demo-to-local install must not call healthy()")

    monkeypatch.setattr(setup, "healthy", no_demo_health)
    calls: list[list[str]] = []

    def guarded_runner(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        if command[1:] in [
            ["init"],
            ["config", "validate"],
            ["tool", "query", "team-workload-overview"],
            ["tool", "query", "project-health-review"],
        ]:
            assert "DATABASE_PATH=data/pm.db" in (target / "src/.env").read_text(
                encoding="utf-8"
            )
        return runner(command, cwd)

    state, detail = setup.install(
        target,
        "local",
        runner=guarded_runner,
        version=(3, 12),
        initializer=lambda root, python, mode, command_runner: installer.configure(root, mode),
    )

    assert (state, detail) == ("already_installed", {"mode": "local"})
    assert "DATABASE_PATH=data/pm.db" in (target / "src/.env").read_text(encoding="utf-8")
    assert (target / "src/data/pm.db").is_file()
    assert setup.digest(demo) == demo_hash
    assert json.loads((target / setup.MARKER).read_text(encoding="utf-8"))["mode"] == "local"
    assert installer.configure(target, "local").startswith("SETUP_LOCAL_SELECTOR_READY")
    assert [command[1:] for command in calls] == [
        ["init"],
        ["config", "validate"],
        ["tool", "query", "team-workload-overview"],
        ["tool", "query", "project-health-review"],
    ]


def test_generated_setup_command_switch_skips_demo_preflight_health_probe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target, setup, _ = setup_modules(tmp_path)
    (target / "src/.env").write_text(
        "DATABASE_PATH=.dm-demo/sample_pm.db\n", encoding="utf-8"
    )
    pm = target / ".venv/bin/pm"
    pm.parent.mkdir(parents=True)
    pm.write_text("", encoding="utf-8")
    (target / setup.MARKER).write_text(
        json.dumps(
            {"lock_sha256": setup.digest(target / "src/runtime-requirements.lock"), "mode": "demo"}
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        setup,
        "healthy",
        lambda *args, **kwargs: pytest.fail("command must not health-probe demo"),
    )
    monkeypatch.setattr(
        setup, "install", lambda root, mode, repair=False: ("already_installed", {"mode": mode})
    )

    assert setup.main(["--bundle-root", str(target), "--install", "--mode", "local"]) == 0


def test_generated_setup_command_rejects_local_to_demo_before_any_health_probe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    target, setup, _ = setup_modules(tmp_path)
    (target / "src/.env").write_text("DATABASE_PATH=data/pm.db\n", encoding="utf-8")
    monkeypatch.setattr(
        setup, "healthy", lambda *args, **kwargs: pytest.fail("must not query local DB")
    )

    assert setup.main(["--bundle-root", str(target), "--install", "--mode", "demo"]) == 0
    assert json.loads(capsys.readouterr().out) == {
        "code": "local_to_demo_unsupported", "state": "failed"
    }


def test_generated_setup_marker_failure_returns_structured_repair(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target, setup, installer = setup_modules(tmp_path)
    runner, _ = successful_runner(target)
    (target / "src/.env").write_text(
        "DATABASE_PATH=.dm-demo/sample_pm.db\n", encoding="utf-8"
    )
    pm = target / ".venv/bin/pm"
    pm.parent.mkdir(parents=True)
    pm.write_text("", encoding="utf-8")
    (target / setup.MARKER).write_text(
        json.dumps({"lock_sha256": setup.digest(target / "src/runtime-requirements.lock"), "mode": "demo"}) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(setup, "write_marker", lambda *args, **kwargs: (_ for _ in ()).throw(OSError()))

    assert setup.install(
        target, "local", runner=runner, version=(3, 12),
        initializer=lambda root, python, mode, command_runner: installer.configure(root, mode),
    ) == ("partial_install", {"code": "setup_marker_write_failed", "repair": "request explicit repair"})


def test_validate_bundle_tree_rejects_unknown_root_and_metadata(tmp_path: Path) -> None:
    target = stage(tmp_path)
    (target / "src 2").mkdir()
    with pytest.raises(RuntimeError, match="BUNDLE_UNKNOWN_ROOT:src 2"):
        bundle.validate_bundle_tree(target)
    (target / "src 2").rmdir()
    (target / "src/.DS_Store").write_bytes(b"")
    with pytest.raises(RuntimeError, match="BUNDLE_METADATA_LEAK"):
        bundle.validate_bundle_tree(target)


def test_setup_preflight_is_read_only_for_unsupported_python(tmp_path: Path) -> None:
    target = stage(tmp_path)
    result = subprocess.run(
        [
            sys.executable,
            str(target / "scripts/setup.py"),
            "--bundle-root",
            str(target),
            "--preflight",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    if sys.version_info[:2] == (3, 12):
        assert payload["state"] == "ready_to_install"
    else:
        assert payload["state"] == "python_unsupported"
    assert not (target / ".venv").exists()
    assert not (target / ".dm-setup-state.json").exists()


def test_generated_setup_contract_covers_health_repair_and_sanitized_failures(
    tmp_path: Path,
) -> None:
    target = stage(tmp_path)
    setup = (target / "scripts/setup.py").read_text(encoding="utf-8")
    installer = (target / "scripts/install-helper.py").read_text(encoding="utf-8")
    for token in (
        "lock_sha256",
        "configuration_validation_failed",
        "initialization_failed",
        "smoke_validation_failed",
        "package_index_unavailable",
        "os.replace",
        "demo_selector_missing_target",
    ):
        assert token in setup
    for token in (
        "SETUP_DEMO_HASH_INVALID",
        "SETUP_DEMO_INTEGRITY_INVALID",
        "os.replace",
    ):
        assert token in installer
    guide = (target / "workbook/WORKBOOK_GUIDE.md").read_text(encoding="utf-8")
    for constraint in ("exactly one of member_key or hiref_id", "LTFTE or STFTE", "level is 5-10", "priority is 1-5", "total no more than 1"):
        assert constraint in guide


def test_builder_fails_closed_for_named_legacy_output(tmp_path: Path) -> None:
    (tmp_path / "delivery-manager-usage-macos-arm64-py312-v0.2.0rc1.zip").write_bytes(
        b""
    )
    args = type("Args", (), {"output_dir": tmp_path, "skip_archive": True})()
    with pytest.raises(RuntimeError, match="BUNDLE_LEGACY_CANDIDATES_PRESENT"):
        bundle.build_bundles(args)
