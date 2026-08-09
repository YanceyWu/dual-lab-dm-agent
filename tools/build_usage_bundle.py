#!/usr/bin/env python3
"""Build the lean, Copilot-first Delivery Manager distribution bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sqlite3
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from openpyxl import Workbook

from validate_release import REPO_ROOT, package_version

sys.path.insert(0, str(REPO_ROOT / "src"))
from pm_agent.dashboard.surface_manifest import (
    PHASE1_LEGACY_DASHBOARD_TRIAL,
    visible_tab_labels,
)  # noqa: E402

DEFAULT_OUTPUT_DIR = REPO_ROOT / "dist" / "dm-usage-bundles"
BUNDLE_NAME = "delivery-manager-usage-lean"
BUNDLE_MANIFEST = "bundle-manifest.json"
DEMO_DB_SOURCE = "generated_from_synthetic_loader"
ROOT_ALLOWLIST = {
    "README.md",
    ".gitignore",
    ".github",
    "demo",
    "scripts",
    "sources",
    "src",
    "workbook",
    BUNDLE_MANIFEST,
}
SRC_FILES = (
    Path("src/pyproject.toml"),
    Path("src/.env.example"),
    Path("src/runtime-requirements.lock"),
)
SRC_DIRECTORIES = (Path("src/pm_agent"), Path("src/scripts"))
EXCLUDED_SCRIPT_NAMES = {"load_sample_data.py", "seed.py", "seed_demo_evidence.py"}
IGNORED_PARTS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".venv"}
PAGES = ", ".join(visible_tab_labels(PHASE1_LEGACY_DASHBOARD_TRIAL))


@dataclass(frozen=True)
class BundleArtifacts:
    demo_db: Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a lean Delivery Manager usage bundle."
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--skip-archive", action="store_true")
    return parser.parse_args()


def ensure_clean_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)


def copy_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def ignored(path: Path) -> bool:
    return (
        path.name == ".DS_Store"
        or path.name.startswith("._")
        or any(part in IGNORED_PARTS for part in path.parts)
        or path.suffix in {".pyc", ".pyo", ".db", ".sqlite", ".sqlite3"}
    )


def copy_directory(source: Path, destination: Path) -> None:
    for path in source.rglob("*"):
        if ignored(path):
            continue
        target = destination / path.relative_to(source)
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        elif not (source.name == "scripts" and path.name in EXCLUDED_SCRIPT_NAMES):
            copy_file(path, target)


def copy_bundle_pyproject(destination: Path) -> None:
    """Remove the development README metadata because lean bundles ship one root README."""
    source = (REPO_ROOT / "src/pyproject.toml").read_text(encoding="utf-8")
    write_text(
        destination, re.sub(r'^readme = "README\.md"\n', "", source, flags=re.MULTILINE)
    )


def text(lines: list[str]) -> str:
    return "\n".join(lines) + "\n"


def build_readme() -> str:
    return text(
        [
            "# Delivery Manager",
            "",
            "Open this extracted folder in VS Code, open Copilot Chat, select the workspace agent **Delivery Manager**, and say **安装并初始化**.",
            "The agent checks Python 3.12, explains the planned local installation, and runs it only after your explicit request.",
            "Dependencies download through existing user pip configuration; this lean bundle contains no Python runtime or wheelhouse.",
            "",
            "After installation, choose **Try demo** for supplied synthetic data or **Use local data** to scaffold an empty local workspace.",
            "For workbook onboarding, start with `workbook/WORKBOOK_GUIDE.md`; it links the preparation template and synthetic sample.",
            "For project profiles and local JIRA/Confluence mappings, use `sources/SOURCES_GUIDE.md`; it includes exact templates and synthetic samples.",
            f"The supported Dashboard UI is limited to: {PAGES}.",
            "",
            "Do not run setup scripts manually unless Copilot directs a recovery action. Installation never accesses connectors or real data.",
        ]
    )


def build_gitignore() -> str:
    return text(
        [
            ".venv/",
            ".dm-setup-state.json",
            "*.db",
            "*.db-journal",
            "*.db-shm",
            "*.db-wal",
            "src/.env",
            "src/.auth/",
            "src/backups/",
            "src/data/",
            "src/.dm-demo/",
            "src/data-feed/",
            "src/exports/",
            "src/logs/",
            "src/__pycache__/",
        ]
    )


def build_workbook_guide() -> str:
    return text(
        [
            "# Team/Project + Capacity workbook",
            "",
            "Prepare a local workbook from `team_project_capacity_workbook_template.xlsx`. `team_project_capacity_workbook_sample.xlsx` is a synthetic valid example only; do not replace its anonymous IDs with real data in a shared bundle.",
            "",
            "Use these exact sheets and headers: Setup (`plan_version_name`, `as_of_date`, `start_month`, `end_month`); Members (`member_key`, `display_name`, `fte_type`, `status`, `current_hiref_id`, `hiref_end_date`, `role`, `level`, `effective_start`, `effective_end`, `next_hiref_id`); Projects (`project_key`, `display_name`, `status`, `priority`, `start_date`, `target_end`); Allocations (`member_key`, `project_key`, `month`, `allocation`, `hiref_id`); Capacity (`member_key`, `month`, `leave_fraction`, `bau_fraction`, `non_project_fraction`). `HIREF Requests` is optional and has `hiref_id`, `project_key`, `request_type`, `start_date`, `end_date`, `notes`.",
            "",
            "Required fields: Setup needs plan_version_name/start_month/end_month (as_of_date optional); Members need member_key/display_name/fte_type/status (role, level, dates and HIREF fields optional except STFTE needs current_hiref_id plus hiref_end_date); Projects need project_key/display_name/status/priority (dates optional); Allocations need project_key/month/allocation and exactly one of member_key or hiref_id; Capacity needs every listed field; each HIREF Request needs hiref_id/project_key/request_type/start_date/end_date (notes optional). Use stable anonymous identifiers for member/project keys. Dates use `YYYY-MM-DD`; months use `YYYY-MM`; fractions are decimals from 0 to 1 (for example 0.5, not 50%). Members are `active` or `inactive`; projects are `planning`, `active`, or `done`; fte_type is LTFTE or STFTE; level is 5-10 when supplied; priority is 1-5. Allocation/capacity months must be inside Setup and member effective ranges; effective starts are month-first and ends month-last; allocation and each fraction are 0-1; the three Capacity fractions total no more than 1. Do not add columns or rename sheets/headers.",
            "",
            "Copilot-first flow: ask Copilot to switch to local data first if you tried demo; then save a workbook profile, preview it, inspect the returned JSON, and explicitly confirm only after you approve the preview. Example route: `<workspace-pm> onboarding profile save --profile-key local-plan --source-type workbook --file <local-workbook-path>`, then `<workspace-pm> onboarding preview --profile-key local-plan`, then `<workspace-pm> onboarding confirm --run-id <run-id>`.",
            "",
            "To export a complete current planning snapshot, ask Copilot to run `<workspace-pm> onboarding export-workbook --output <explicit-local-xlsx-path>`. It reports path, hash, counts, plan, warnings, and evidence metadata only; it never opens or quotes workbook contents. Existing output paths are protected unless `--overwrite` is explicitly requested.",
            "If export returns `WORKBOOK_EXPORT_STFTE_HIREF_REQUIRED`, do not invent a HIREF or change the member type. Ask Copilot to help identify the local STFTE source row, then update its maintained current HIREF ID, HIREF end date, and matching HIREF Request through the normal preview/confirm flow before retrying export.",
        ]
    )


def build_sources_guide() -> str:
    return text(
        [
            "# Auxiliary source files",
            "",
            "These files are editable user source facts, not a database backup. Do not add connector snapshots, health results, freshness values, audit history, credentials, or raw connector content.",
            "",
            "`project_profiles_template.xlsx` and `project_profiles_sample.xlsx` use worksheet `Project Profiles`; retain the first four rows and exact headers. `Team Size` is accepted by the existing format but is not exported because it is not a maintained project-profile fact. Fill `Project ID` with an existing stable project ID. Milestones use one `date | name` item per line; risks use one `risk | high|medium|low` item per line; stakeholders are comma-separated.",
            "",
            "`jira_board_registry_template.csv` and `jira_board_configs.sample.csv` use `id,name,project_key,base_jql` plus the documented optional local mapping fields. `board_url` is preserved only when it is already a maintained local mapping. Never place credentials in this CSV.",
            "",
            "`confluence_page_registry_template.csv` and `confluence_pages.sample.csv` use `id,board_id` plus optional title/page type fields. Keep `last_synced`, `last_modified`, and `content_summary` blank in locally prepared files; they are not reusable source facts.",
            "",
            "Copilot-first flow: ask Copilot to export with `<workspace-pm> onboarding export-source --source-type <project-profile-workbook|jira-board-registry-csv|confluence-page-registry-csv> --output <explicit-local-path>`. To import an edited file, use profile save, preview, inspect the returned JSON, then explicit confirm. Exports never overwrite an existing path unless `--overwrite` is explicitly requested.",
        ]
    )


def write_project_profile_template(path: Path) -> None:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Project Profiles"
    worksheet.append(["Project profiles"])
    worksheet.append(["Header-only user-source template"])
    worksheet.append([None] * 12)
    worksheet.append(
        [
            "Project Name", "Team Size", "Phase", "Phase Detail", "Priority",
            "Focus", "Objective", "Milestones", "Risks", "Stakeholders",
            "Special Rules", "Project ID",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(path)


def write_registry_templates(source_dir: Path) -> None:
    write_text(
        source_dir / "jira_board_registry_template.csv",
        "id,name,project_key,base_jql,version_name_pattern,board_id,board_url,pm_project_id,active,issues_use_base_jql,notes\n",
    )
    write_text(
        source_dir / "confluence_page_registry_template.csv",
        "id,board_id,title,page_type,last_synced,last_modified,content_summary\n",
    )


def build_instructions() -> str:
    return text(
        [
            "# Delivery Manager usage workspace instructions",
            "",
            "Use the workspace `Delivery Manager` agent. This is an operator bundle, not a development checkout.",
            "Before setup, follow that agent's guidance; do not attempt business queries, interaction-memory commands, SQLite access, or source edits.",
            "After setup, use only structured commands and returned JSON as the factual basis. Do not inspect configuration, credentials, raw exports, or connector payloads.",
            "Live connector probes require an explicit user request and writes retain propose, preview, explicit confirmation, then persist.",
        ]
    )


def build_agent() -> str:
    setup_gate = text(
        [
            "## Bundle setup gate",
            "",
            f"The visible Dashboard remains the six legacy pages: {PAGES}.",
            "Before the workspace-local executable exists, do not pre-read interaction memory or run a business command.",
            "Discover Python 3.12 without hardcoding python3: Windows tries `py -3.12` then `python`; macOS/Linux tries `python3.12`, `python3`, then `python`, validating major/minor.",
            "Reuse the selected interpreter for all `scripts/setup.py --bundle-root .` calls. Report `python_missing` when no candidate exists and `python_unsupported` only after detecting a non-3.12 candidate.",
            "For `python_missing` or `python_unsupported`, provide only user-reviewable Python 3.12 installation guidance. Never automatically invoke brew, winget, choco, apt, or another system package manager; never request admin/sudo, modify machine-wide Python, or install global packages.",
            "Run `<selected-python> scripts/setup.py --bundle-root . --preflight` first. Explain online locked dependency installation and wait for an explicit request to install; `partial_install` requires explicit repair.",
            "Ask the user to choose demo or local. Only after an explicit request to install and authorization run `<selected-python> scripts/setup.py --bundle-root . --install --mode demo|local`; only after explicit repair authorization run the same command with `--repair`.",
            "For an explicit request to switch from demo to local data, run `<selected-python> scripts/setup.py --bundle-root . --install --mode local`; do this before any onboarding preview or confirm. Local-to-demo switching is unsupported.",
            "After setup, `<workspace-pm>` means exactly the selected workspace executable: `.venv\\Scripts\\pm.exe` on Windows or `.venv/bin/pm` on macOS/Linux. If it is absent, stop and return setup guidance; never use a PATH fallback.",
            "For normal commands, POSIX may run `.venv/bin/pm ...`; PowerShell may run `& .\\.venv\\Scripts\\pm.exe ...`. Every `<workspace-pm> ...` example below is an abstract template, not a bare executable fallback.",
            "After setup, use the workspace-local executable and preserve all maintained interaction-memory stdin safety, read-only routes, and controlled preview/confirm/token boundaries below.",
            "For explicit JIRA/Confluence registry onboarding, ask only for local file path and anonymous profile key. Do not open or summarize raw CSV. Use `jira-board-registry-csv` or `confluence-page-registry-csv` profile save, preview, then exact explicit confirm; never sync implicitly.",
            "For workbook preparation, direct users to `workbook/WORKBOOK_GUIDE.md`, `workbook/team_project_capacity_workbook_template.xlsx`, and the synthetic sample. For a requested current-state export, run `<workspace-pm> onboarding export-workbook --output <explicit-local-xlsx-path>` and report returned metadata only; never open or quote workbook cells. If it returns `WORKBOOK_EXPORT_STFTE_HIREF_REQUIRED`, explain that the maintained STFTE source is incomplete; guide the user to preview/confirm a factual current HIREF ID, end date, and matching HIREF Request, then retry. Never invent a HIREF or silently change the resource type.",
            "For editable project profiles or JIRA/Confluence mappings, use `sources/SOURCES_GUIDE.md`. For an explicit source export, run `<workspace-pm> onboarding export-source --source-type <exact-supported-source-type> --output <explicit-local-path>`; report metadata only, then use the existing profile save → preview → explicit confirm route after the user edits the file.",
            "",
        ]
    )
    maintained = (REPO_ROOT / ".github/agents/delivery-manager.agent.md").read_text(
        encoding="utf-8"
    )
    pre_read_start = maintained.index("## Interaction-memory pre-read")
    pre_read_end = maintained.index("## Direct routing")
    pre_read = text(
        [
            "## Interaction-memory pre-read",
            "",
            "After setup, pre-read `interaction-memory-context` for each natural-language request using `<workspace-pm>`. This local aid remains non-authoritative and must not trigger writes.",
            "",
            "On macOS/Linux, use the POSIX executable and pass the exact user turn only through standard input:",
            "",
            "```bash",
            "cat <<'EOF' | .venv/bin/pm tool query interaction-memory-context --param-stdin message",
            "<exact user turn>",
            "EOF",
            "```",
            "",
            "On Windows PowerShell, use `& .\\.venv\\Scripts\\pm.exe`. Do not place raw user text in a command, command history, or a `--param` argument. Copilot must invoke that executable through a Python `subprocess.run(..., input=<user turn>, text=True)` call or terminal automation that supplies stdin directly; the command-line arguments contain only `tool query interaction-memory-context --param-stdin message`.",
            "",
            "Add `--param project_id=<exact-project-id>` only when that project ID is already known from the current request or prior approved result context. Do not invent `project_id` or `repo_root`.",
            "",
            "Use the returned interaction-memory result only as a local chat aid:",
            "",
            "1. `working_context.answer_preferences` may shape answer language and answer order;",
            "2. `working_context.routing_hints` may break ties only among routes already supported by the explicit user request;",
            "3. `working_context.follow_up_hints` may surface one directly relevant reminder;",
            "4. `working_context.strategy_flags` may reduce repetitive clarification only when existing context already answers it.",
            "",
            "Interaction memory must not change the authoritative business path. Do not let it override a clear business intent, invent parameters, IDs, time periods, teams, or connector names, treat memory rows as business facts/evidence/freshness, or trigger propose/preview/confirm/persist without the user's explicit request.",
            "",
            "If the selected workspace executable is absent, stop and return setup guidance. If the result is empty, disabled, scope-unknown, unknown, unavailable, invalid, or failed, continue with baseline routing.",
            "",
        ]
    )
    maintained = maintained[:pre_read_start] + pre_read + maintained[pre_read_end:]
    maintained = maintained.replace("src/.venv/bin/pm", "<workspace-pm>")
    maintained = maintained.replace(
        "otherwise use `pm`", "otherwise stop and return setup guidance"
    )
    maintained = maintained.replace("`pm ", "`<workspace-pm> ")
    maintained = maintained.replace("`pm`", "`<workspace-pm>`")
    maintained = re.sub(r"(?m)^pm (?=\w)", "<workspace-pm> ", maintained)
    maintained = maintained.replace(
        "When executing the CLI in this repository, prefer",
        "When executing the CLI in this bundle, use `<workspace-pm>`; do not fall back to another executable.",
    )
    return maintained.replace(
        "# Delivery Manager operating agent",
        "# Delivery Manager operating agent\n\n" + setup_gate,
        1,
    )


def build_install_helper() -> str:
    return r"""#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import sqlite3
from pathlib import Path


def sha256(path):
    return hashlib.sha256(path.read_bytes()).digest()


def verify_sqlite(path, connect=sqlite3.connect):
    with connect(path) as connection:
        if connection.execute("PRAGMA integrity_check").fetchone() != ("ok",):
            raise RuntimeError("SETUP_DEMO_INTEGRITY_INVALID")


def configure_demo(root, copier=shutil.copyfile, replace=os.replace, connect=sqlite3.connect):
    source, target = root / "demo/sample_pm.db", root / "src/.dm-demo/sample_pm.db"
    if not source.is_file():
        raise RuntimeError("SETUP_DEMO_SOURCE_MISSING")
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        temporary = target.with_name(target.name + ".tmp")
        try:
            copier(source, temporary)
            if sha256(source) != sha256(temporary):
                raise RuntimeError("SETUP_DEMO_HASH_INVALID")
            verify_sqlite(temporary, connect)
            replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)
    verify_sqlite(target, connect)


def configure(root, mode, **dependencies):
    env = root / "src/.env"
    if not env.is_file():
        raise RuntimeError("SETUP_ENV_MISSING")
    if mode == "local":
        lines = env.read_text(encoding="utf-8").splitlines()
        matches = [i for i, line in enumerate(lines) if line.strip().startswith("DATABASE_PATH=")]
        if len(matches) != 1:
            raise RuntimeError("SETUP_DATABASE_PATH_INVALID")
        lines[matches[0]] = "DATABASE_PATH=data/pm.db"
        write_env_selector(env, lines, dependencies.get("replace", os.replace))
        return "SETUP_LOCAL_SELECTOR_READY: local database selected; no connector or source file was read."
    configure_demo(root, **dependencies)
    lines = env.read_text(encoding="utf-8").splitlines()
    matches = [i for i, line in enumerate(lines) if line.strip().startswith("DATABASE_PATH=")]
    if len(matches) != 1:
        raise RuntimeError("SETUP_DATABASE_PATH_INVALID")
    lines[matches[0]] = "DATABASE_PATH=.dm-demo/sample_pm.db"
    write_env_selector(env, lines, dependencies.get("replace", os.replace))
    return "SETUP_DEMO_READY: synthetic demo selected."


def write_env_selector(env, lines, replace=os.replace):
    temporary = env.with_name(env.name + ".tmp")
    try:
        temporary.write_text("\n".join(lines) + "\n", encoding="utf-8")
        replace(temporary, env)
    finally:
        temporary.unlink(missing_ok=True)


def parse_args(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle-root", required=True)
    parser.add_argument("--mode", choices=("demo", "local"), required=True)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    try:
        print(configure(Path(args.bundle_root).resolve(), args.mode))
    except RuntimeError as error:
        raise SystemExit(str(error))


if __name__ == "__main__":
    main()
"""


def build_setup_helper() -> str:
    return r"""#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

MARKER = ".dm-setup-state.json"
SMOKE_COMMANDS = (
    ("version",),
    ("config", "validate"),
    ("tool", "query", "team-workload-overview"),
    ("tool", "query", "project-health-review"),
)


def emit(state, **extra):
    print(json.dumps({"state": state, **extra}, sort_keys=True))


def pm_path(root):
    return root / ".venv" / ("Scripts/pm.exe" if sys.platform == "win32" else "bin/pm")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def command_result(command, root):
    return subprocess.run(command, cwd=root, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)


def healthy(root, runner=command_result):
    marker, lock, pm = root / MARKER, root / "src/runtime-requirements.lock", pm_path(root)
    if not (marker.is_file() and lock.is_file() and pm.is_file()):
        return False
    try:
        state = json.loads(marker.read_text(encoding="utf-8"))
        assert state["lock_sha256"] == digest(lock)
        assert state["mode"] in {"demo", "local"}
    except (OSError, TypeError, ValueError, KeyError, AssertionError):
        return False
    try:
        return all(runner([str(pm), *command], root).returncode == 0 for command in SMOKE_COMMANDS)
    except OSError:
        return False


def installed_mode(root):
    # Read a coherent selector without executing runtime smoke commands.
    marker, lock, pm, env = root / MARKER, root / "src/runtime-requirements.lock", pm_path(root), root / "src/.env"
    if not (marker.is_file() and lock.is_file() and pm.is_file() and env.is_file()):
        return None
    try:
        state = json.loads(marker.read_text(encoding="utf-8"))
        mode = state["mode"]
        if mode not in {"demo", "local"} or state["lock_sha256"] != digest(lock):
            return None
        selector = next((line.strip() for line in env.read_text(encoding="utf-8").splitlines() if line.strip().startswith("DATABASE_PATH=")), "")
        expected = ".dm-demo/sample_pm.db" if mode == "demo" else "data/pm.db"
        return mode if selector == f"DATABASE_PATH={expected}" else None
    except (OSError, TypeError, ValueError, KeyError):
        return None


def selected_mode(root):
    # Return the configured mode without starting the runtime.
    env = root / "src/.env"
    try:
        selectors = [line.strip() for line in env.read_text(encoding="utf-8").splitlines() if line.strip().startswith("DATABASE_PATH=")]
    except OSError:
        return None
    if selectors == ["DATABASE_PATH=data/pm.db"]:
        return "local"
    if selectors == ["DATABASE_PATH=.dm-demo/sample_pm.db"]:
        return "demo"
    return None


def preflight(root, runner=command_result, version=None, skip_runtime_smoke=False):
    version = sys.version_info[:2] if version is None else version
    if tuple(version) != (3, 12):
        return ("python_unsupported", {"required": "3.12", "detected": f"{version[0]}.{version[1]}"})
    try:
        probe = root / ".dm-write-probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
    except OSError:
        return ("failed", {"code": "workspace_not_writable"})
    # An explicit demo-to-local switch must not run the normal health probes
    # while ``.env`` still selects the writable demo database.  Those queries
    # record execution traces, so they are writes in practice.  The marker and
    # selector check below is deliberately read-only and is enough to identify
    # the requested transition; ``install`` then initializes and smokes local.
    if skip_runtime_smoke:
        existing_mode = installed_mode(root)
        if existing_mode is not None:
            return ("already_installed", {"mode": existing_mode})
    if healthy(root, runner):
        marker_mode = json.loads((root / MARKER).read_text(encoding="utf-8"))["mode"]
        selector = (root / "src/.env").read_text(encoding="utf-8") if (root / "src/.env").is_file() else ""
        expected = ".dm-demo/sample_pm.db" if marker_mode == "demo" else "data/pm.db"
        if f"DATABASE_PATH={expected}" != next((line.strip() for line in selector.splitlines() if line.strip().startswith("DATABASE_PATH=")), ""):
            return ("partial_install", {"code": "mode_selector_mismatch", "repair": "request explicit repair"})
        return ("already_installed", {"mode": marker_mode})
    env, demo = root / "src/.env", root / "src/.dm-demo/sample_pm.db"
    if env.is_file() and ".dm-demo/sample_pm.db" in env.read_text(encoding="utf-8") and not demo.is_file():
        return ("partial_install", {"code": "demo_selector_missing_target", "repair": "request explicit repair"})
    if (root / MARKER).exists() or (root / ".venv").exists():
        return ("partial_install", {"repair": "request explicit repair"})
    return ("ready_to_install", {})


def run(command, root, runner=command_result):
    try:
        result = runner(command, root)
    except OSError:
        raise RuntimeError("command_execution_failed") from None
    if result.returncode:
        detail = (getattr(result, "stderr", "") or "").lower()
        if "config" in command:
            raise RuntimeError("configuration_validation_failed")
        if "tool" in command:
            raise RuntimeError("smoke_validation_failed")
        if any(Path(str(part)).name == "install-helper.py" for part in command) or "init" in command:
            raise RuntimeError("initialization_failed")
        if "pip" in command and "install" in command and ("name resolution" in detail or "connection" in detail or "network" in detail):
            raise RuntimeError("package_index_unavailable")
        raise RuntimeError("dependency_install_failed")


def initialize_mode(root, python, mode, runner=command_result):
    run([str(python), str(root / "scripts/install-helper.py"), "--bundle-root", str(root), "--mode", mode], root, runner)


def verify_local_database(root):
    env = root / "src/.env"
    selector = next((line.strip() for line in env.read_text(encoding="utf-8").splitlines() if line.strip().startswith("DATABASE_PATH=")), "")
    if selector != "DATABASE_PATH=data/pm.db":
        raise RuntimeError("local_database_selector_invalid")
    database = root / "src/data/pm.db"
    if not database.is_file():
        raise RuntimeError("local_database_missing")
    with sqlite3.connect(database) as connection:
        if connection.execute("PRAGMA integrity_check").fetchone() != ("ok",):
            raise RuntimeError("local_database_integrity_invalid")
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if not {"employees", "projects", "plan_versions", "monthly_allocations"}.issubset(tables):
        raise RuntimeError("local_database_schema_incomplete")


def remove_partial(root, remover=shutil.rmtree):
    remover(root / ".venv", ignore_errors=True)
    (root / MARKER).unlink(missing_ok=True)


def write_marker(root, mode, replace=os.replace):
    state = {"python": "3.12", "mode": mode, "lock_sha256": digest(root / "src/runtime-requirements.lock")}
    temporary = root / (MARKER + ".tmp")
    try:
        temporary.write_text(json.dumps(state) + "\n", encoding="utf-8")
        replace(temporary, root / MARKER)
    finally:
        temporary.unlink(missing_ok=True)


def restore_env(root, replace=os.replace):
    env, example = root / "src/.env", root / "src/.env.example"
    temporary = env.with_name(env.name + ".tmp")
    try:
        temporary.write_text(example.read_text(encoding="utf-8"), encoding="utf-8")
        replace(temporary, env)
    finally:
        temporary.unlink(missing_ok=True)


def valid_env(root):
    env = root / "src/.env"
    return env.is_file() and sum(line.strip().startswith("DATABASE_PATH=") for line in env.read_text(encoding="utf-8").splitlines()) == 1


def install(root, mode, runner=command_result, initializer=initialize_mode, repair=False, version=None):
    if selected_mode(root) == "local" and mode == "demo":
        return ("failed", {"code": "local_to_demo_unsupported"})
    existing_mode = installed_mode(root)
    if existing_mode == "local" and mode == "demo":
        return ("failed", {"code": "local_to_demo_unsupported"})
    if existing_mode == "demo" and mode == "local":
        # Do not call ``healthy`` here: its read-only-looking tool queries can
        # append execution traces to the currently selected demo database.
        try:
            python = root / ".venv" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
            initializer(root, python, mode, runner)
            run([str(pm_path(root)), "init"], root, runner)
            verify_local_database(root)
            for command in SMOKE_COMMANDS[1:]:
                run([str(pm_path(root)), *command], root, runner)
        except RuntimeError as error:
            return ("partial_install", {"code": str(error), "repair": "request explicit repair"})
        try:
            write_marker(root, mode)
        except OSError:
            return ("partial_install", {"code": "setup_marker_write_failed", "repair": "request explicit repair"})
        return ("already_installed", {"mode": mode})
    state, detail = preflight(root, runner, version=version)
    if state == "already_installed":
        validated_mode = detail.get("mode")
        if validated_mode == mode:
            return ("already_installed", {"mode": mode})
    if state == "partial_install" and not repair:
        return (state, detail)
    if state not in ("ready_to_install", "partial_install"):
        return (state, detail)
    if repair:
        remove_partial(root)
        if not valid_env(root):
            restore_env(root)
    try:
        run([sys.executable, "-m", "venv", str(root / ".venv")], root, runner)
        python = root / ".venv" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
        run([str(python), "-m", "pip", "install", "--disable-pip-version-check", "-r", str(root / "src/runtime-requirements.lock")], root, runner)
        run([str(python), "-m", "pip", "install", "--no-deps", "--no-build-isolation", "--editable", str(root / "src")], root, runner)
        run([str(pm_path(root)), "version"], root, runner)
        if not (root / "src/.env").exists():
            run([str(pm_path(root)), "init", "--skip-db"], root, runner)
        initializer(root, python, mode, runner)
        if mode == "local":
            run([str(pm_path(root)), "init"], root, runner)
            verify_local_database(root)
        for command in SMOKE_COMMANDS[1:]:
            run([str(pm_path(root)), *command], root, runner)
    except RuntimeError as error:
        return ("partial_install", {"code": str(error), "repair": "request explicit repair"})
    try:
        write_marker(root, mode)
    except OSError:
        return ("partial_install", {"code": "setup_marker_write_failed", "repair": "request explicit repair"})
    return ("already_installed", {"mode": mode})


def parse_args(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle-root", required=True)
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--install", action="store_true")
    parser.add_argument("--repair", action="store_true")
    parser.add_argument("--mode", choices=("demo", "local"))
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    root = Path(args.bundle_root).resolve()
    if args.install and args.mode == "demo" and selected_mode(root) == "local":
        emit("failed", code="local_to_demo_unsupported")
        return 0
    # This is the only command-path exception to normal health validation.
    # It prevents the demo-selected runtime from being queried before the
    # local selector is atomically installed by ``install``.
    switching_demo_to_local = (
        args.install and args.mode == "local" and installed_mode(root) == "demo"
    )
    state, detail = preflight(root, skip_runtime_smoke=switching_demo_to_local)
    if args.preflight or not args.install:
        emit(state, **detail)
        return 0
    if state == "partial_install" and not args.repair:
        emit(state, **detail)
        return 0
    if state == "already_installed":
        state, detail = install(root, args.mode, repair=args.repair)
        emit(state, **detail)
        return 0
    if state != "ready_to_install" and not (state == "partial_install" and args.repair):
        emit(state, **detail)
        return 0
    if not args.mode:
        emit("failed", code="initialization_mode_required")
        return 0
    state, detail = install(root, args.mode, repair=args.repair)
    emit(state, **detail)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
"""


def write_text(path: Path, content: str, executable: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    if executable:
        path.chmod(0o755)


def make_read_only(path: Path) -> None:
    path.chmod(path.stat().st_mode & ~0o222)


def build_artifacts(directory: Path) -> BundleArtifacts:
    directory.mkdir(parents=True, exist_ok=True)
    demo_db = directory / "sample_pm.db"
    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "src/scripts/load_sample_data.py"),
            "--db",
            str(demo_db),
            "--force",
        ],
        cwd=REPO_ROOT,
        check=True,
    )
    with sqlite3.connect(demo_db) as connection:
        if connection.execute("PRAGMA integrity_check;").fetchone() != ("ok",):
            raise RuntimeError("BUNDLE_DEMO_DB_INTEGRITY_FAILED")
    return BundleArtifacts(demo_db=demo_db)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def records(bundle_dir: Path) -> list[dict[str, str]]:
    return [
        {"path": item.relative_to(bundle_dir).as_posix(), "sha256": sha256(item)}
        for item in sorted(bundle_dir.rglob("*"))
        if item.is_file() and item.name != BUNDLE_MANIFEST
    ]


def validate_bundle_tree(bundle_dir: Path) -> None:
    unknown = {item.name for item in bundle_dir.iterdir()} - ROOT_ALLOWLIST
    if unknown:
        raise RuntimeError(f"BUNDLE_UNKNOWN_ROOT:{','.join(sorted(unknown))}")
    required = {
        "README.md",
        ".gitignore",
        ".github/agents/delivery-manager.agent.md",
        ".github/copilot-instructions.md",
        "demo/sample_pm.db",
        "workbook/team_project_capacity_workbook_template.xlsx",
        "workbook/team_project_capacity_workbook_sample.xlsx",
        "workbook/WORKBOOK_GUIDE.md",
        "sources/SOURCES_GUIDE.md",
        "sources/project_profiles_template.xlsx",
        "sources/project_profiles_sample.xlsx",
        "sources/jira_board_registry_template.csv",
        "sources/jira_board_configs.sample.csv",
        "sources/confluence_page_registry_template.csv",
        "sources/confluence_pages.sample.csv",
        "scripts/setup.py",
        "scripts/install-helper.py",
        "src/pyproject.toml",
        "src/.env.example",
        "src/runtime-requirements.lock",
        "src/pm_agent",
        "src/scripts",
    }
    missing = [entry for entry in sorted(required) if not (bundle_dir / entry).exists()]
    if missing:
        raise RuntimeError(f"BUNDLE_MISSING_FILES:{','.join(missing)}")
    for item in bundle_dir.rglob("*"):
        if (
            item.name == ".DS_Store"
            or item.name.startswith("._")
            or any(part in IGNORED_PARTS for part in item.parts)
        ):
            raise RuntimeError(f"BUNDLE_METADATA_LEAK:{item.relative_to(bundle_dir)}")
    for entry in (
        "src/README.md",
        "artifacts",
        "wheelhouse",
        "src/tests",
        "src/sample-data",
        "src/configs",
        ".github/prompts/dm-workload.prompt.md",
    ):
        if (bundle_dir / entry).exists():
            raise RuntimeError(f"BUNDLE_FORBIDDEN_ENTRY:{entry}")


def write_manifest(bundle_dir: Path) -> None:
    source_identity = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    dirty = (
        subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        != ""
    )
    payload = {
        "bundle_name": bundle_dir.name,
        "product_version": package_version(),
        "python_requirement": "3.12",
        "dependency_mode": "online_locked",
        "demo_db_source": DEMO_DB_SOURCE,
        "copilot_agent": "Delivery Manager",
        "source_identity": {"revision": source_identity, "dirty": dirty},
        "files": records(bundle_dir),
    }
    write_text(
        bundle_dir / BUNDLE_MANIFEST,
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
    )


def stage_bundle_tree(bundle_dir: Path, artifacts: BundleArtifacts) -> None:
    ensure_clean_dir(bundle_dir)
    for source in SRC_FILES:
        if source.name == "pyproject.toml":
            copy_bundle_pyproject(bundle_dir / source)
        else:
            copy_file(REPO_ROOT / source, bundle_dir / source)
    for source in SRC_DIRECTORIES:
        copy_directory(REPO_ROOT / source, bundle_dir / source)
    write_text(bundle_dir / "README.md", build_readme())
    write_text(bundle_dir / ".gitignore", build_gitignore())
    write_text(bundle_dir / ".github/agents/delivery-manager.agent.md", build_agent())
    write_text(bundle_dir / ".github/copilot-instructions.md", build_instructions())
    copy_file(
        REPO_ROOT / "templates/team_project_capacity_workbook_template.xlsx",
        bundle_dir / "workbook/team_project_capacity_workbook_template.xlsx",
    )
    copy_file(
        REPO_ROOT / "src/sample-data/excel/team_project_capacity_workbook_hiref_sample.xlsx",
        bundle_dir / "workbook/team_project_capacity_workbook_sample.xlsx",
    )
    write_text(bundle_dir / "workbook/WORKBOOK_GUIDE.md", build_workbook_guide())
    source_dir = bundle_dir / "sources"
    write_text(source_dir / "SOURCES_GUIDE.md", build_sources_guide())
    write_project_profile_template(source_dir / "project_profiles_template.xlsx")
    copy_file(
        REPO_ROOT / "src/sample-data/excel/project_profiles_sample.xlsx",
        source_dir / "project_profiles_sample.xlsx",
    )
    write_registry_templates(source_dir)
    copy_file(
        REPO_ROOT / "src/sample-data/csv/jira_board_configs.sample.csv",
        source_dir / "jira_board_configs.sample.csv",
    )
    copy_file(
        REPO_ROOT / "src/sample-data/csv/confluence_pages.sample.csv",
        source_dir / "confluence_pages.sample.csv",
    )
    copy_file(artifacts.demo_db, bundle_dir / "demo/sample_pm.db")
    make_read_only(bundle_dir / "demo/sample_pm.db")
    write_text(bundle_dir / "scripts/setup.py", build_setup_helper(), executable=True)
    write_text(
        bundle_dir / "scripts/install-helper.py",
        build_install_helper(),
        executable=True,
    )
    validate_bundle_tree(bundle_dir)
    write_manifest(bundle_dir)


def archive_bundle(bundle_dir: Path) -> Path:
    return Path(
        shutil.make_archive(
            str(bundle_dir.parent / bundle_dir.name),
            "zip",
            root_dir=bundle_dir.parent,
            base_dir=bundle_dir.name,
        )
    )


def build_bundles(args: argparse.Namespace) -> list[Path]:
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    legacy_candidates = [
        item.name
        for item in output.iterdir()
        if item.name.startswith(
            ("delivery-manager-usage-macos-", "delivery-manager-usage-windows-")
        )
    ]
    if legacy_candidates:
        raise RuntimeError(
            "BUNDLE_LEGACY_CANDIDATES_PRESENT:" + ",".join(sorted(legacy_candidates))
        )
    work = output / ".build-artifacts"
    ensure_clean_dir(work)
    try:
        bundle = output / f"{BUNDLE_NAME}-v{package_version()}"
        stage_bundle_tree(bundle, build_artifacts(work))
        if args.skip_archive:
            return []
        archive = archive_bundle(bundle)
        print(
            f"archive={archive} sha256={sha256(archive)} bytes={archive.stat().st_size}"
        )
        return [archive]
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    build_bundles(parse_args())
