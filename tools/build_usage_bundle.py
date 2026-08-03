#!/usr/bin/env python3
"""Build platform-specific Delivery Manager usage bundles."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from validate_release import REPO_ROOT, build_package, package_version

DEFAULT_OUTPUT_DIR = REPO_ROOT / "dist" / "dm-usage-bundles"
BUNDLE_MANIFEST = "bundle-manifest.json"

ROOT_SOURCE_FILES = (
    Path(".github/agents/delivery-manager.agent.md"),
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
    return f"""# Delivery Manager Usage Bundle ({target.platform_label})

This package is the **end-user local workspace** for Delivery Managers. It is
trimmed for operation, not for development: no tests, architecture packs, or
developer tooling are included.

## Included

- the `Delivery Manager` Copilot workspace agent and instructions;
- the `src/` runtime workspace and starter configuration templates;
- an offline `wheelhouse/` for **{target.platform_label} + Python {target.python_version}**;
- one-click install and VS Code open scripts for this platform.

## Before first use

1. Install **Python {target.python_version}** for **{target.platform_label}**.
2. Install **VS Code** plus **GitHub Copilot / Copilot Chat**.
3. If you want the open script to work, make sure the `code` command is available.

## Install locally

Run:

```text
{target.install_script}
```

The script creates `.venv`, performs an **offline** install from `wheelhouse/`,
and runs `pm init` to scaffold local runtime files.

## Open in VS Code

Run:

```text
{target.open_script}
```

After VS Code opens this folder, open Copilot Chat and select the workspace
agent named `Delivery Manager`.

## Normal operator flow

1. `pm config validate`
2. `pm connector validate --portable`
3. Ask Copilot business questions through the `Delivery Manager` agent.

Example prompts:

- “下个月哪些同事还有容量？”
- “项目 Atlas 当前有哪些需要管理层关注的问题？”
- “未来 90 天有哪些 STFTE 的 HIREF 需要处理？”
- “生成本周 DM brief。”

## Boundary

- Keep real configuration, credentials, local databases, exports, and logs only
  on the approved work computer.
- Do not develop new features inside this bundle workspace. Source changes
  belong in the development repository.
"""


def build_bundle_runtime_readme(target: BundleTarget) -> str:
    return f"""# Local Delivery Manager Runtime

This is the trimmed runtime workspace included in the {target.platform_label}
Delivery Manager usage bundle. It is intended for **local operation**, not
feature development.

## Install from the bundle root

Run the bundle install script instead of manual package commands:

```text
../{target.install_script}
```

The install script creates a local virtual environment, installs dependencies
offline from `../wheelhouse/`, installs this runtime in editable mode, and runs
`pm init`.

## Operator commands

```bash
pm version
pm init
pm config validate
pm connector validate --portable
pm tool list
pm weekly-brief query
pm dashboard serve
```

Read-only and controlled-write behavior is still governed by the workspace
Copilot instructions and the `Delivery Manager` custom agent.

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
src/data-feed/
src/exports/
src/logs/
src/.venv/
src/__pycache__/
src/pm_agent/__pycache__/
src/pm_agent/**/*.pyc
"""


def build_bundle_copilot_instructions() -> str:
    return """# Delivery Manager usage workspace instructions

Use the workspace `Delivery Manager` custom agent for normal Delivery Manager
operations. This bundle is an operator workspace, not a development repository.

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
"$ROOT/.venv/bin/pm" init

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
"%ROOT%\\.venv\\Scripts\\pm.exe" init || exit /b 1

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


def build_artifacts(artifact_dir: Path) -> tuple[Path, Path]:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    return build_package(artifact_dir)


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
        Path(target.install_script),
        Path(target.open_script),
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
    if "--editable" not in install_script or "wheelhouse" not in install_script:
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
    artifacts: tuple[Path, Path],
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
        bundle_dir / ".github/copilot-instructions.md",
        build_bundle_copilot_instructions(),
    )
    write_text(
        bundle_dir / "src/README.md",
        build_bundle_runtime_readme(target),
    )
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
    (bundle_dir / "wheelhouse").mkdir(parents=True, exist_ok=True)

    artifact_dir = bundle_dir / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    for artifact in artifacts:
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
                artifacts[0],
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
