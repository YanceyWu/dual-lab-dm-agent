#!/usr/bin/env python3
"""Build platform-specific Delivery Manager usage bundles."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from validate_release import REPO_ROOT, build_package, package_version

sys.path.insert(0, str(REPO_ROOT / "src"))

from pm_agent.dashboard.surface_manifest import (  # noqa: E402
    PHASE1_LEGACY_DASHBOARD_TRIAL,
    visible_tab_labels,
)

DEFAULT_OUTPUT_DIR = REPO_ROOT / "dist" / "dm-usage-bundles"
BUNDLE_MANIFEST = "bundle-manifest.json"
DEMO_DB_SOURCE = "generated_from_synthetic_loader"
SHIPPED_DEMO_DB = Path("demo/sample_pm.db")
WRITABLE_DEMO_DB = Path("src/.dm-demo/sample_pm.db")
ENV_PATH = Path("src/.env")
CANONICAL_DEMO_DATABASE_PATH = ".dm-demo/sample_pm.db"

ROOT_SOURCE_FILES = (
    Path(".github/prompts/dm-workload.prompt.md"),
)
SRC_SOURCE_FILES = (
    Path("src/pyproject.toml"),
    Path("src/.env.example"),
)
SRC_SOURCE_DIRECTORIES = (
    Path("src/pm_agent"),
    Path("src/configs"),
    Path("src/scripts"),
)
EXCLUDED_SCRIPT_NAMES = {
    "load_sample_data.py",
    "seed.py",
    "seed_demo_evidence.py",
}
PROHIBITED_ROOT_ENTRIES = {
    "AGENTS.md",
    "PROGRESS.md",
    "ROADMAP.md",
    "architecture",
    "docs",
    "implementation-packs",
    "implementation-reports",
    "prompts",
    "research-input",
    "standards",
    "templates",
    "tools",
}
PROHIBITED_SRC_ENTRIES = {
    "tests",
    "sample-data",
}
PHASE1_LEGACY_PAGES = visible_tab_labels(PHASE1_LEGACY_DASHBOARD_TRIAL)
PHASE1_LEGACY_PAGES_TEXT = ", ".join(PHASE1_LEGACY_PAGES)


@dataclass(frozen=True)
class BundleArtifacts:
    wheel: Path
    sdist: Path
    demo_db: Path


@dataclass(frozen=True)
class BundleTarget:
    key: str
    display_name: str
    pip_platform: str
    python_version: str
    abi: str
    install_script: str
    open_script: str

    @property
    def python_tag(self) -> str:
        return self.python_version.replace(".", "")

    @property
    def architecture(self) -> str:
        if "arm64" in self.pip_platform:
            return "arm64"
        if "x86_64" in self.pip_platform:
            return "x86_64"
        if "amd64" in self.pip_platform:
            return "amd64"
        return self.pip_platform.replace(".", "_")

    @property
    def platform_label(self) -> str:
        return f"{self.display_name} ({self.architecture})"

    @property
    def architecture_aliases(self) -> tuple[str, ...]:
        if self.architecture == "arm64":
            return ("arm64", "aarch64")
        if self.architecture == "x86_64":
            return ("x86_64", "amd64")
        if self.architecture == "amd64":
            return ("amd64", "x86_64")
        return (self.architecture,)

    @property
    def bundle_name(self) -> str:
        return (
            f"delivery-manager-usage-{self.key}-{self.architecture}-py{self.python_tag}"
            f"-v{package_version()}"
        )

    @property
    def archive_name(self) -> str:
        return f"{self.bundle_name}.zip"


def default_targets() -> dict[str, BundleTarget]:
    return {
        "macos": BundleTarget(
            key="macos",
            display_name="macOS",
            pip_platform="macosx_11_0_arm64",
            python_version="3.12",
            abi="cp312",
            install_script="scripts/install.command",
            open_script="scripts/open-in-vscode.command",
        ),
        "windows": BundleTarget(
            key="windows",
            display_name="Windows",
            pip_platform="win_amd64",
            python_version="3.12",
            abi="cp312",
            install_script="scripts/install.cmd",
            open_script="scripts/open-in-vscode.cmd",
        ),
    }


def parse_build_requirements() -> tuple[str, ...]:
    pyproject = (REPO_ROOT / "src/pyproject.toml").read_text(encoding="utf-8")
    match = re.search(
        r"(?ms)^\[build-system\].*?^requires\s*=\s*\[(.*?)\]",
        pyproject,
    )
    if not match:
        raise RuntimeError("BUILD_SYSTEM_REQUIRES_NOT_FOUND")
    return tuple(re.findall(r'"([^"]+)"', match.group(1)))


BUILD_REQUIREMENTS = parse_build_requirements()


def parse_args() -> argparse.Namespace:
    defaults = default_targets()
    parser = argparse.ArgumentParser(
        description="Build offline Delivery Manager usage bundles for local distribution."
    )
    parser.add_argument(
        "--platform",
        action="append",
        choices=tuple(defaults),
        dest="platforms",
        help="Platform bundle to build. Defaults to both macos and windows.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory that will receive the generated bundle folders and zips.",
    )
    parser.add_argument(
        "--macos-platform",
        default=defaults["macos"].pip_platform,
        help="pip target platform tag for the macOS bundle.",
    )
    parser.add_argument(
        "--macos-python-version",
        default=defaults["macos"].python_version,
        help="Target Python version for the macOS bundle, e.g. 3.12.",
    )
    parser.add_argument(
        "--macos-abi",
        default=defaults["macos"].abi,
        help="Target Python ABI for the macOS bundle, e.g. cp312.",
    )
    parser.add_argument(
        "--windows-platform",
        default=defaults["windows"].pip_platform,
        help="pip target platform tag for the Windows bundle.",
    )
    parser.add_argument(
        "--windows-python-version",
        default=defaults["windows"].python_version,
        help="Target Python version for the Windows bundle, e.g. 3.12.",
    )
    parser.add_argument(
        "--windows-abi",
        default=defaults["windows"].abi,
        help="Target Python ABI for the Windows bundle, e.g. cp312.",
    )
    parser.add_argument(
        "--skip-wheelhouse",
        action="store_true",
        help="Skip pip download. Useful for dry runs and repository tests.",
    )
    parser.add_argument(
        "--skip-archive",
        action="store_true",
        help="Leave the bundle folders unzipped.",
    )
    return parser.parse_args()


def configured_targets(args: argparse.Namespace) -> list[BundleTarget]:
    requested = args.platforms or ["macos", "windows"]
    defaults = default_targets()
    result: list[BundleTarget] = []
    for name in requested:
        if name == "macos":
            result.append(
                BundleTarget(
                    key="macos",
                    display_name="macOS",
                    pip_platform=args.macos_platform,
                    python_version=args.macos_python_version,
                    abi=args.macos_abi,
                    install_script=defaults["macos"].install_script,
                    open_script=defaults["macos"].open_script,
                )
            )
        else:
            result.append(
                BundleTarget(
                    key="windows",
                    display_name="Windows",
                    pip_platform=args.windows_platform,
                    python_version=args.windows_python_version,
                    abi=args.windows_abi,
                    install_script=defaults["windows"].install_script,
                    open_script=defaults["windows"].open_script,
                )
            )
    return result


def ensure_clean_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)


def copy_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def copy_directory(source: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for path in source.rglob("*"):
        if "__pycache__" in path.parts:
            continue
        relative = path.relative_to(source)
        target = destination / relative
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        if source.name == "scripts" and path.name in EXCLUDED_SCRIPT_NAMES:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)


def build_bundle_root_readme(target: BundleTarget) -> str:
    install_command = target.install_script
    open_command = target.open_script
    return f"""# Delivery Manager Trial Bundle ({target.platform_label})

This bundle is the **Phase 1 local Delivery Manager trial**: install it, open it
in VS Code, and use the `Delivery Manager` workspace agent. The supported
Dashboard UI in this bundle remains the legacy Phase 1 surface:
{PHASE1_LEGACY_PAGES_TEXT}.

## Before first use

1. Install **Python {target.python_version}** for **{target.platform_label}**.
2. Install **VS Code** plus **GitHub Copilot / Copilot Chat**.
3. If you want the open script to work, make sure the `code` command is
   available.

## Install locally

Run:

```text
{install_command}
```

The install script creates `.venv`, performs an **offline** install from
`wheelhouse/`, scaffolds `src/.env` on first install, and prepares the bundled
demo DB at `src/.dm-demo/sample_pm.db`.

## Open in VS Code

Run:

```text
{open_command}
```

After VS Code opens this folder, open Copilot Chat and select the workspace
agent named `Delivery Manager`.

## Choose your first run path

Choose **Try demo** for the fastest synthetic first run, or choose **Use local
data** when you are ready to point the runtime at an approved local database.

### Try demo

**When to choose it:** you want a working trial immediately with the bundled
synthetic database.

**Do this:** install the bundle, open it in VS Code, keep
`DATABASE_PATH=.dm-demo/sample_pm.db` in `src/.env`, and optionally run:

```bash
pm dashboard serve
```

**Then:** ask the `Delivery Manager` agent questions such as “当前哪些同事还有可用容量？”
or “未来 90 天哪些同事的 HIREF 即将到期？”. To reset demo mode while you are still
using it, delete `src/.dm-demo/sample_pm.db` and rerun `{install_command}`.

### Use local data

**When to choose it:** you want the trial workspace to use an approved local
database instead of the bundled synthetic demo.

**Do this:** edit `src/.env` so it says `DATABASE_PATH=data/pm.db`, then run:

```bash
pm init
pm config validate
pm connector validate --portable
```

**Then:** continue with the `Structured data onboarding` section in
`src/README.md`, use the approved `pm onboarding profile save → preview →
confirm` flow, and return to the `Delivery Manager` agent for runtime guidance.

## Boundary

- Keep real configuration, credentials, local databases, exports, and logs only
  on the approved work computer.
- Do not treat this bundle as a development repository; source, test, and
  release changes belong in the maintained development checkout.
"""


def build_bundle_runtime_readme(target: BundleTarget) -> str:
    return f"""# Local Delivery Manager Runtime

This is the trimmed runtime workspace included in the {target.platform_label}
Delivery Manager usage bundle. It is intended for **local operation**, not
feature development.

The default Dashboard trial surface is limited to the legacy pages:
{PHASE1_LEGACY_PAGES_TEXT}.

## Install from the bundle root

Run the bundle install script instead of manual package commands:

```text
../{target.install_script}
```

The install script creates a local virtual environment, installs dependencies
offline from `../wheelhouse/`, scaffolds `src/.env` on first install with
`pm init --skip-db`, copies the bundled read-only demo DB into
`src/.dm-demo/sample_pm.db`, and sets demo mode in `src/.env` as:

```dotenv
DATABASE_PATH={CANONICAL_DEMO_DATABASE_PATH}
```

Re-running install preserves an existing writable demo DB copy and never
silently switches a non-demo `DATABASE_PATH` back to demo mode.

## Switch from demo to local data

To stop using the bundled demo and move into approved local-data onboarding:

1. Edit `src/.env` so it contains `DATABASE_PATH=data/pm.db`.
2. Run `pm init`.
3. Run `pm config validate`.
4. Run `pm connector validate --portable`.
5. Continue with `Structured data onboarding` below.

## Operator commands

```bash
pm version
pm config validate
pm connector validate --portable
pm dashboard serve
```

Read-only and controlled-write behavior is still governed by the workspace
Copilot instructions and the `Delivery Manager` custom agent.

## Structured data onboarding

After you have switched `DATABASE_PATH` to `data/pm.db`, initialized it with
`pm init`, and passed `pm config validate` plus
`pm connector validate --portable`, onboard approved local sources through the
supported profile flow:

1. save an approved source file with `pm onboarding profile save ...`;
2. inspect it with `pm onboarding profile show --profile-key <profile-key>` when
   needed;
3. preview it with `pm onboarding preview --profile-key <profile-key>`;
4. confirm it with `pm onboarding confirm --run-id <run-id>`;
5. inspect the completed run with `pm onboarding run show --run-id <run-id>`.

Example commands:

```bash
pm onboarding profile save --profile-key fy26-q4 --source-type workbook --file /approved/path/team-project-capacity.xlsx
pm onboarding preview --profile-key fy26-q4
pm onboarding confirm --run-id <onboarding-run-id>
pm onboarding run show --run-id <onboarding-run-id>
```

## Runtime contents

- `pm_agent/` — CLI, use cases, deterministic rules, connectors, database, Dashboard
- `configs/` — starter configuration templates
- `scripts/` — supported local import and sync entrypoints

## Boundary

- Keep operational paths, endpoints, credentials, databases, exports, logs, and
  connector payloads in ignored local files only.
- Do not add tests, sample data, or development tooling back into this bundle.
"""


def build_bundle_gitignore() -> str:
    return """# Local runtime state
.venv/
*.db
*.db-journal
*.db-shm
*.db-wal
*.sqlite
*.sqlite3

# Local workspace secrets and runtime files
src/.env
src/.auth/
src/backups/
src/data/
src/.dm-demo/
src/data-feed/
src/exports/
src/logs/
src/.venv/
src/__pycache__/
src/pm_agent/__pycache__/
src/pm_agent/**/*.pyc
"""


def build_bundle_copilot_instructions() -> str:
    return f"""# Delivery Manager usage workspace instructions

Use the workspace `Delivery Manager` custom agent for normal Delivery Manager
operations. This bundle is an operator workspace, not a development repository.
The default operator entry is: install from the bundle root, open this workspace
in VS Code, and use the `Delivery Manager` agent. The bundled Phase 1 trial
surface is the legacy Dashboard pages only:
{PHASE1_LEGACY_PAGES_TEXT}.

For DM operations:

- use only the structured commands and routing defined in
  `.github/agents/delivery-manager.agent.md`;
- treat returned JSON, evidence, freshness, warnings, and execution metadata as
  the sole factual basis;
- never inspect SQLite, connector configuration, raw exports, or human-formatted
  legacy output;
- never infer missing facts as zero, healthy, available, valid, or safe;
- run live connector probes or syncs only after an explicit request;
- keep staffing writes within propose, preview, explicit confirmation, persist.

For repository or source-code changes:

- do not modify the runtime inside this bundle;
- escalate the change back to the maintained development repository instead of
  editing this workspace as if it were a dev checkout.
"""


def build_bundle_delivery_manager_agent() -> str:
    return f"""---
name: Delivery Manager
description: Operate the local Delivery Manager legacy Dashboard trial through approved deterministic commands.
argument-hint: Ask about team workload, project status, HIREF, or the legacy dashboard.
tools:
  - execute/runInTerminal
agents: []
user-invocable: true
disable-model-invocation: true
target: vscode
---

# Delivery Manager operating agent

Act as the user's Delivery Manager decision-support assistant after they install
this bundle, open it in VS Code, and select the bundled `Delivery Manager`
workspace agent.

The supported Phase 1 Dashboard UI in this bundle is the legacy Dashboard. It
currently exposes:
{PHASE1_LEGACY_PAGES_TEXT}.

Use the local `pm` commands as the authoritative source of facts. Deterministic
code owns filtering, calculations, validation, freshness, and persistence. Do
not inspect SQLite, configuration, credentials, raw exports, connector payloads,
or human-formatted legacy CLI output.

## Direct routing

Route known requests directly. Do not run `pm tool list` or `describe` first
when the mapping and required parameters are already clear.

| User intent | Approved command |
| --- | --- |
| Current workload, current team capacity, or who may have room | `pm tool query team-workload-overview [--team "<exact team>"]` |
| Legacy project status or project health | `pm tool query project-health-review [--project <exact-project-id>]` |
| HIREF expiry or continuity risk | `pm tool query contract-continuity-review [--days <1-365>]` |
| Validate bundle setup before using the dashboard | `pm config validate` then `pm connector validate --portable` |
| Start or reopen the legacy Dashboard trial UI | `pm dashboard serve` |

Ask only for missing decision-critical parameters. Do not invent an exact team,
project ID, or time period. If a safe unfiltered query is supported and useful,
run it instead of asking unnecessarily.

## Legacy Dashboard workflow

Use the dashboard itself as the primary operator surface for the full Phase 1
legacy experience. In particular:

- use the Overview, Projects, Team, HIREF, Monthly Plan, and Project Health
  pages for the supported trial workflow;
- if a user asks about the Projects list or Monthly Plan page specifically,
  direct them back to the legacy Dashboard rather than inventing a hidden CLI
  route;
- if the dashboard appears empty or stale, use `pm config validate`,
  `pm connector validate --portable`, and `pm dashboard serve` as the minimum
  troubleshooting path before discussing unsupported surfaces.

## Trial-surface boundary

The bundled trial surface does **not** promote experimental or later-phase
features. If the user asks about Management Attention, Action Follow-up, legacy
Weekly DM brief, Weekly Brief v2, Attention Center, capacity heatmaps,
execution review, layered health, connector review, or snapshots, state that
those surfaces are outside the current Phase 1 bundle scope and return to the
legacy Dashboard trial workflows.

## Result handling

Use the structured JSON result as the sole factual basis. State the conclusion
first, then cite the material evidence, freshness, assumptions, warnings, and
execution ID when returned.

If status is `partial`, `unknown`, `unavailable`, `invalid`, or `failed`, say so
plainly. Never reinterpret missing data as zero, healthy, available, or safe.
Do not calculate authoritative availability, HIREF coverage, rankings, or
health in prose.

This agent is for operating the bundled trial product. If the user asks to
modify source code, architecture, tests, or repository configuration, explain
that they should switch to the maintained development repository.
"""


def build_install_helper() -> str:
    return f"""#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

CANONICAL_DEMO_DATABASE_PATH = {CANONICAL_DEMO_DATABASE_PATH!r}
ENV_RELATIVE_PATH = {ENV_PATH.as_posix()!r}
SHIPPED_DEMO_DB = {SHIPPED_DEMO_DB.as_posix()!r}
WRITABLE_DEMO_DB = {WRITABLE_DEMO_DB.as_posix()!r}


class InstallHelperError(RuntimeError):
    pass


def _remove_path(path: Path) -> None:
    if not path.exists():
        return
    if path.is_dir():
        shutil.rmtree(path)
        return
    path.unlink()


def _normalize_database_path(raw_value: str) -> str:
    value = raw_value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {{'"', "'"}}:
        value = value[1:-1]
    return value.strip()


def _read_env(env_path: Path) -> tuple[str, list[str], int, str]:
    try:
        content = env_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise InstallHelperError(f"INSTALL_HELPER_ENV_READ_FAILED: {{env_path}}: {{exc}}") from exc

    lines = content.splitlines(keepends=True)
    matches: list[tuple[int, str]] = []
    for index, line in enumerate(lines):
        candidate = line.lstrip()
        if candidate.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() == "DATABASE_PATH":
            matches.append((index, value))
    if not matches:
        raise InstallHelperError(
            "INSTALL_HELPER_DATABASE_PATH_MISSING: src/.env must contain exactly one DATABASE_PATH entry."
        )
    if len(matches) != 1:
        raise InstallHelperError(
            "INSTALL_HELPER_DATABASE_PATH_DUPLICATE: src/.env contains duplicate DATABASE_PATH entries."
        )
    index, value = matches[0]
    return content, lines, index, value


def _resolve_database_path(src_root: Path, raw_value: str) -> Path:
    normalized = _normalize_database_path(raw_value)
    candidate = Path(normalized)
    if not candidate.is_absolute():
        candidate = src_root / candidate
    return candidate.resolve(strict=False)


def _copy_demo_db(source: Path, destination: Path) -> bool:
    if destination.exists():
        return False
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        temp_path = destination.with_name(destination.name + ".tmp")
        if temp_path.exists():
            _remove_path(temp_path)
        shutil.copyfile(source, temp_path)
        temp_path.replace(destination)
        return True
    except OSError as exc:
        temp_path = destination.with_name(destination.name + ".tmp")
        if temp_path.exists():
            _remove_path(temp_path)
        raise InstallHelperError(
            f"INSTALL_HELPER_DEMO_COPY_FAILED: could not copy {{source}} to {{destination}}: {{exc}}"
        ) from exc


def _write_env(env_path: Path, original_content: str, lines: list[str], line_index: int, new_value: str) -> None:
    line_ending = "\\r\\n" if "\\r\\n" in original_content else "\\n"
    updated_lines = list(lines)
    updated_lines[line_index] = f"DATABASE_PATH={{new_value}}{{line_ending}}"
    updated_content = "".join(updated_lines)
    if updated_content and not updated_content.endswith(("\\n", "\\r\\n")):
        updated_content += line_ending
    temp_path = env_path.with_name(env_path.name + ".tmp")
    try:
        temp_path.write_text(updated_content, encoding="utf-8")
        temp_path.replace(env_path)
    except OSError as exc:
        if temp_path.exists():
            _remove_path(temp_path)
        raise InstallHelperError(
            f"INSTALL_HELPER_ENV_WRITE_FAILED: could not update {{env_path}}: {{exc}}"
        ) from exc


def main() -> None:
    parser = argparse.ArgumentParser(description="Finalize Delivery Manager bundle install state.")
    parser.add_argument("--bundle-root", required=True, help="Absolute path to the installed bundle root.")
    parser.add_argument(
        "--first-install",
        action="store_true",
        help="Allow the helper to rewrite the freshly scaffolded starter DATABASE_PATH to demo mode.",
    )
    args = parser.parse_args()

    bundle_root = Path(args.bundle_root).resolve()
    env_path = bundle_root / ENV_RELATIVE_PATH
    shipped_demo_db = bundle_root / SHIPPED_DEMO_DB
    writable_demo_db = bundle_root / WRITABLE_DEMO_DB
    src_root = bundle_root / "src"

    if not shipped_demo_db.is_file():
        raise SystemExit(
            f"INSTALL_HELPER_DEMO_SOURCE_MISSING: bundled demo DB is missing at {{shipped_demo_db}}."
        )
    try:
        with shipped_demo_db.open("rb"):
            pass
    except OSError as exc:
        raise SystemExit(
            f"INSTALL_HELPER_DEMO_SOURCE_UNREADABLE: could not read {{shipped_demo_db}}: {{exc}}"
        )

    created_demo_copy = False
    try:
        original_content, lines, line_index, raw_database_path = _read_env(env_path)
        current_database_path = _resolve_database_path(src_root, raw_database_path)
        canonical_demo_path = writable_demo_db.resolve(strict=False)
        should_set_demo_mode = args.first_install or current_database_path == canonical_demo_path
        created_demo_copy = _copy_demo_db(shipped_demo_db, writable_demo_db)
        if should_set_demo_mode:
            _write_env(
                env_path,
                original_content,
                lines,
                line_index,
                CANONICAL_DEMO_DATABASE_PATH,
            )
            print(
                "Install helper: writable demo DB "
                f"{{'created' if created_demo_copy else 'preserved'}} at {{writable_demo_db}}."
            )
            print(
                f"Install helper: src/.env now uses DATABASE_PATH={{CANONICAL_DEMO_DATABASE_PATH}}."
            )
            return
        print(
            "Install helper: writable demo DB "
            f"{{'created' if created_demo_copy else 'preserved'}} at {{writable_demo_db}}."
        )
        print(
            "Install helper: preserved existing non-demo DATABASE_PATH in src/.env; "
            "the workspace stays in local-data mode."
        )
    except InstallHelperError as exc:
        if created_demo_copy and writable_demo_db.exists():
            writable_demo_db.unlink()
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
"""


def build_install_script(target: BundleTarget) -> str:
    if target.key == "macos":
        return f"""#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON_BIN="${{PYTHON_BIN:-python3}}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Python {target.python_version} was not found. Install it first."
  exit 1
fi

"$PYTHON_BIN" - <<'PY'
import platform
import sys
expected = "{target.python_version}"
actual = sys.version_info[:2]
required = tuple(int(part) for part in expected.split("."))
machine = platform.machine().lower()
allowed = {target.architecture_aliases!r}
if actual != required:
    raise SystemExit(
        f"This bundle expects Python {{expected}}, found "
        f"{{actual[0]}}.{{actual[1]}}."
    )
if machine not in allowed:
    raise SystemExit(
        "This bundle was built for {target.platform_label}, found architecture "
        f"{{machine}}."
    )
PY

"$PYTHON_BIN" -m venv "$ROOT/.venv"
"$ROOT/.venv/bin/python" -m pip install \
  --no-index \
  --find-links "$ROOT/wheelhouse" \
  {' '.join(BUILD_REQUIREMENTS)}
"$ROOT/.venv/bin/python" -m pip install \
  --no-index \
  --find-links "$ROOT/wheelhouse" \
  --no-build-isolation \
  --editable "$ROOT/src"

FIRST_INSTALL=0
if [ ! -f "$ROOT/src/.env" ]; then
  "$ROOT/.venv/bin/pm" init --skip-db
  FIRST_INSTALL=1
fi

HELPER_ARGS=(
  "$ROOT/scripts/install-helper.py"
  --bundle-root "$ROOT"
)
if [ "$FIRST_INSTALL" -eq 1 ]; then
  HELPER_ARGS+=(--first-install)
fi
"$ROOT/.venv/bin/python" "${{HELPER_ARGS[@]}}"

echo
echo "Installation complete."
echo "Next: run $ROOT/{target.open_script}"
"""
    windows_probe = (
        "import platform,sys; "
        f"raise SystemExit(0 if sys.version_info[:2] == ({target.python_version.replace('.', ', ')}) "
        f"and platform.machine().lower() in {target.architecture_aliases!r} else 1)"
    )
    windows_open_script = target.open_script.replace("/", "\\")
    return f"""@echo off
setlocal
set "ROOT=%~dp0.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"

where py >nul 2>nul
if errorlevel 1 goto :python_executable_check
py -{target.python_version} -c "{windows_probe}" >nul 2>nul
if not errorlevel 1 set "PYTHON=py -{target.python_version}" & goto :python_ready

:python_executable_check
where python >nul 2>nul
if errorlevel 1 goto :python_not_found
python -c "{windows_probe}" >nul 2>nul
if not errorlevel 1 set "PYTHON=python" & goto :python_ready

:python_not_found
echo Python {target.python_version} for {target.platform_label} was not found. Install it first.
exit /b 1

:python_ready
%PYTHON% -m venv "%ROOT%\\.venv" || exit /b 1
"%ROOT%\\.venv\\Scripts\\python.exe" -m pip install --no-index --find-links "%ROOT%\\wheelhouse" {' '.join(BUILD_REQUIREMENTS)} || exit /b 1
"%ROOT%\\.venv\\Scripts\\python.exe" -m pip install --no-index --find-links "%ROOT%\\wheelhouse" --no-build-isolation --editable "%ROOT%\\src" || exit /b 1
set "HELPER_FLAG="
if not exist "%ROOT%\\src\\.env" (
  "%ROOT%\\.venv\\Scripts\\pm.exe" init --skip-db || exit /b 1
  set "HELPER_FLAG=--first-install"
)
"%ROOT%\\.venv\\Scripts\\python.exe" "%ROOT%\\scripts\\install-helper.py" --bundle-root "%ROOT%" %HELPER_FLAG% || exit /b 1

echo.
echo Installation complete.
echo Next: run %ROOT%\\{windows_open_script}
"""


def build_open_script(target: BundleTarget) -> str:
    if target.key == "macos":
        return """#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if command -v code >/dev/null 2>&1; then
  code "$ROOT"
  exit 0
fi

if [ -d "/Applications/Visual Studio Code.app" ]; then
  open -a "Visual Studio Code" "$ROOT"
  exit 0
fi

echo "VS Code was not found. Open this folder manually in VS Code:"
echo "  $ROOT"
exit 1
"""
    return """@echo off
setlocal
set "ROOT=%~dp0.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"

where code >nul 2>nul
if %ERRORLEVEL%==0 (
  code "%ROOT%"
  exit /b 0
)

if exist "%LocalAppData%\\Programs\\Microsoft VS Code\\Code.exe" (
  start "" "%LocalAppData%\\Programs\\Microsoft VS Code\\Code.exe" "%ROOT%"
  exit /b 0
)

echo VS Code was not found. Open this folder manually in VS Code:
echo   %ROOT%
exit /b 1
"""


def write_text(path: Path, content: str, executable: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")
    if executable:
        path.chmod(0o755)


def make_read_only(path: Path) -> None:
    path.chmod(path.stat().st_mode & ~0o222)


def build_artifacts(artifact_dir: Path) -> BundleArtifacts:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    wheel, sdist = build_package(artifact_dir)
    demo_dir = artifact_dir / "demo-db"
    demo_dir.mkdir(parents=True, exist_ok=True)
    demo_db = demo_dir / "sample_pm.db"
    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "src" / "scripts" / "load_sample_data.py"),
            "--db",
            str(demo_db),
            "--force",
        ],
        cwd=REPO_ROOT,
        check=True,
    )
    if not demo_db.is_file():
        raise RuntimeError("BUNDLE_DEMO_DB_NOT_CREATED")
    with demo_db.open("rb") as handle:
        if handle.read(16) != b"SQLite format 3\x00":
            raise RuntimeError("BUNDLE_DEMO_DB_INVALID_HEADER")
    with sqlite3.connect(demo_db) as connection:
        integrity = connection.execute("PRAGMA integrity_check;").fetchone()
    if integrity != ("ok",):
        raise RuntimeError("BUNDLE_DEMO_DB_INTEGRITY_FAILED")
    return BundleArtifacts(wheel=wheel, sdist=sdist, demo_db=demo_db)


def download_wheelhouse(
    project_wheel: Path,
    wheelhouse_dir: Path,
    target: BundleTarget,
    build_requirements: Iterable[str],
) -> None:
    wheelhouse_dir.mkdir(parents=True, exist_ok=True)
    base_command = [
        sys.executable,
        "-m",
        "pip",
        "download",
        "--disable-pip-version-check",
        "--dest",
        str(wheelhouse_dir),
        "--only-binary=:all:",
        "--platform",
        target.pip_platform,
        "--implementation",
        "cp",
        "--python-version",
        target.python_tag,
        "--abi",
        target.abi,
    ]
    subprocess.run(
        [*base_command, str(project_wheel)],
        check=True,
        cwd=REPO_ROOT,
    )
    for requirement in build_requirements:
        subprocess.run(
            [*base_command, requirement],
            check=True,
            cwd=REPO_ROOT,
        )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def bundle_file_records(bundle_dir: Path) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    for path in sorted(bundle_dir.rglob("*"), key=lambda item: item.as_posix()):
        if not path.is_file() or path.name == BUNDLE_MANIFEST:
            continue
        records.append(
            {
                "path": path.relative_to(bundle_dir).as_posix(),
                "sha256": sha256(path),
            }
        )
    return records


def validate_bundle_tree(
    bundle_dir: Path,
    target: BundleTarget,
    *,
    require_wheelhouse: bool,
) -> None:
    required_files = {
        Path("README.md"),
        Path(".gitignore"),
        Path(".github/agents/delivery-manager.agent.md"),
        Path(".github/copilot-instructions.md"),
        Path(".github/prompts/dm-workload.prompt.md"),
        Path("src/README.md"),
        Path("src/pyproject.toml"),
        Path("src/.env.example"),
        Path("demo/sample_pm.db"),
        Path(target.install_script),
        Path(target.open_script),
        Path("scripts/install-helper.py"),
        Path("artifacts"),
        Path("src/pm_agent"),
        Path("src/configs"),
        Path("src/scripts"),
        Path("wheelhouse"),
    }
    missing = [
        item.as_posix()
        for item in sorted(required_files, key=lambda entry: entry.as_posix())
        if not (bundle_dir / item).exists()
    ]
    if missing:
        raise RuntimeError(f"BUNDLE_MISSING_FILES:{', '.join(missing)}")

    for entry in PROHIBITED_ROOT_ENTRIES:
        if (bundle_dir / entry).exists():
            raise RuntimeError(f"BUNDLE_CONTAINS_DEV_ENTRY:{entry}")
    for entry in PROHIBITED_SRC_ENTRIES:
        if (bundle_dir / "src" / entry).exists():
            raise RuntimeError(f"BUNDLE_CONTAINS_DEV_SRC_ENTRY:{entry}")

    for script_name in EXCLUDED_SCRIPT_NAMES:
        if (bundle_dir / "src" / "scripts" / script_name).exists():
            raise RuntimeError(f"BUNDLE_CONTAINS_SYNTHETIC_SCRIPT:{script_name}")

    wheelhouse_files = sorted((bundle_dir / "wheelhouse").glob("*.whl"))
    if require_wheelhouse and not wheelhouse_files:
        raise RuntimeError("BUNDLE_WHEELHOUSE_EMPTY")

    install_script = (bundle_dir / target.install_script).read_text(encoding="utf-8")
    if (
        "--editable" not in install_script
        or "wheelhouse" not in install_script
        or "install-helper.py" not in install_script
        or "--skip-db" not in install_script
    ):
        raise RuntimeError("BUNDLE_INSTALL_SCRIPT_INVALID")

    open_script = (bundle_dir / target.open_script).read_text(encoding="utf-8")
    if "VS Code" not in open_script and "code " not in open_script:
        raise RuntimeError("BUNDLE_OPEN_SCRIPT_INVALID")


def write_manifest(
    bundle_dir: Path,
    target: BundleTarget,
    *,
    offline_wheelhouse_included: bool,
) -> None:
    payload = {
        "bundle_name": bundle_dir.name,
        "product_version": package_version(),
        "demo_db_source": DEMO_DB_SOURCE,
        "platform": {
            "key": target.key,
            "display_name": target.display_name,
            "architecture": target.architecture,
            "pip_platform": target.pip_platform,
            "python_version": target.python_version,
            "abi": target.abi,
        },
        "copilot_agent": "Delivery Manager",
        "install_script": target.install_script,
        "open_script": target.open_script,
        "offline_wheelhouse_included": offline_wheelhouse_included,
        "files": bundle_file_records(bundle_dir),
    }
    write_text(bundle_dir / BUNDLE_MANIFEST, json.dumps(payload, indent=2, sort_keys=True))


def stage_bundle_tree(
    bundle_dir: Path,
    target: BundleTarget,
    artifacts: BundleArtifacts,
) -> None:
    ensure_clean_dir(bundle_dir)

    for relative in ROOT_SOURCE_FILES:
        copy_file(REPO_ROOT / relative, bundle_dir / relative)
    for relative in SRC_SOURCE_FILES:
        copy_file(REPO_ROOT / relative, bundle_dir / relative)
    for relative in SRC_SOURCE_DIRECTORIES:
        copy_directory(REPO_ROOT / relative, bundle_dir / relative)

    write_text(bundle_dir / "README.md", build_bundle_root_readme(target))
    write_text(bundle_dir / ".gitignore", build_bundle_gitignore())
    write_text(
        bundle_dir / ".github/agents/delivery-manager.agent.md",
        build_bundle_delivery_manager_agent(),
    )
    write_text(
        bundle_dir / ".github/copilot-instructions.md",
        build_bundle_copilot_instructions(),
    )
    write_text(
        bundle_dir / "src/README.md",
        build_bundle_runtime_readme(target),
    )
    copy_file(artifacts.demo_db, bundle_dir / SHIPPED_DEMO_DB)
    make_read_only(bundle_dir / SHIPPED_DEMO_DB)
    write_text(
        bundle_dir / target.install_script,
        build_install_script(target),
        executable=target.key == "macos",
    )
    write_text(
        bundle_dir / target.open_script,
        build_open_script(target),
        executable=target.key == "macos",
    )
    write_text(
        bundle_dir / "scripts/install-helper.py",
        build_install_helper(),
        executable=target.key == "macos",
    )
    (bundle_dir / "wheelhouse").mkdir(parents=True, exist_ok=True)

    artifact_dir = bundle_dir / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    for artifact in (artifacts.wheel, artifacts.sdist):
        copy_file(artifact, artifact_dir / artifact.name)

    validate_bundle_tree(
        bundle_dir,
        target,
        require_wheelhouse=False,
    )
    write_manifest(
        bundle_dir,
        target,
        offline_wheelhouse_included=False,
    )


def archive_bundle(bundle_dir: Path) -> Path:
    archive_base = bundle_dir.parent / bundle_dir.name
    archive_path = Path(
        shutil.make_archive(
            str(archive_base),
            "zip",
            root_dir=bundle_dir.parent,
            base_dir=bundle_dir.name,
        )
    )
    return archive_path


def build_bundles(args: argparse.Namespace) -> list[Path]:
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    artifact_cache = output_dir / ".build-artifacts"
    ensure_clean_dir(artifact_cache)
    artifacts = build_artifacts(artifact_cache)

    archives: list[Path] = []
    for target in configured_targets(args):
        bundle_dir = output_dir / target.bundle_name
        print(
            f"\n==> staging {target.platform_label} bundle "
            f"({target.pip_platform}, python {target.python_version}, {target.abi})",
            flush=True,
        )
        stage_bundle_tree(
            bundle_dir,
            target,
            artifacts,
        )
        if not args.skip_wheelhouse:
            print("   downloading offline wheelhouse", flush=True)
            download_wheelhouse(
                artifacts.wheel,
                bundle_dir / "wheelhouse",
                target,
                BUILD_REQUIREMENTS,
            )
            validate_bundle_tree(bundle_dir, target, require_wheelhouse=True)
            write_manifest(
                bundle_dir,
                target,
                offline_wheelhouse_included=True,
            )
        if not args.skip_archive:
            archive = archive_bundle(bundle_dir)
            archives.append(archive)
            print(f"   archived to {archive}", flush=True)
        else:
            print(f"   left unpacked at {bundle_dir}", flush=True)
    shutil.rmtree(artifact_cache)
    return archives


def main() -> None:
    build_bundles(parse_args())


if __name__ == "__main__":
    main()
