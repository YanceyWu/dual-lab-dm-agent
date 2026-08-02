#!/usr/bin/env python3
"""Run the complete portable release-candidate validation contract."""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
import zipfile
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPO_ROOT / "src"
PYPROJECT = PACKAGE_ROOT / "pyproject.toml"
PROJECT_NAME = "ai-pm-agent"
EXPECTED_TOOL_VERSIONS = {
    "build": "1.5.0",
    "poetry-core": "2.4.1",
    "pytest": "9.1.1",
    "ruff": "0.15.22",
}

VALIDATION_STEPS = (
    "repository-boundary",
    "synthetic-samples",
    "documented-use-cases",
    "runtime-tests",
    "repository-tool-tests",
    "ruff",
    "compile",
    "diff-check",
    "package-build",
)


def package_version() -> str:
    match = re.search(
        r'(?ms)^\[tool\.poetry\].*?^version\s*=\s*"([^"]+)"',
        PYPROJECT.read_text(encoding="utf-8"),
    )
    if not match:
        raise RuntimeError("PACKAGE_VERSION_NOT_FOUND")
    return match.group(1)


def source_identity() -> tuple[str, bool]:
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return commit, bool(status.strip())


def validate_tool_versions() -> None:
    mismatches = []
    for package, expected in EXPECTED_TOOL_VERSIONS.items():
        try:
            actual = version(package)
        except PackageNotFoundError:
            actual = "missing"
        if actual != expected:
            mismatches.append(f"{package}: expected {expected}, found {actual}")
    if mismatches:
        raise RuntimeError(
            "VALIDATION_TOOL_VERSION_MISMATCH: " + "; ".join(mismatches)
        )
    print(
        "Validation tools: "
        + ", ".join(
            f"{package}={expected}"
            for package, expected in EXPECTED_TOOL_VERSIONS.items()
        ),
        flush=True,
    )


def run_step(
    label: str,
    command: list[str],
    *,
    env: dict[str, str] | None = None,
) -> None:
    print(f"\n==> {label}", flush=True)
    subprocess.run(command, cwd=REPO_ROOT, env=env, check=True)


def build_package(output_dir: Path) -> tuple[Path, Path]:
    run_step(
        "package-build",
        [
            sys.executable,
            "-m",
            "build",
            "--no-isolation",
            "--sdist",
            "--wheel",
            "--outdir",
            str(output_dir),
            str(PACKAGE_ROOT),
        ],
    )
    wheels = sorted(output_dir.glob("*.whl"))
    sdists = sorted(output_dir.glob("*.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        raise RuntimeError("PACKAGE_ARTIFACT_SET_INVALID")

    expected_version = package_version()
    with zipfile.ZipFile(wheels[0]) as archive:
        metadata_files = [
            name for name in archive.namelist() if name.endswith(".dist-info/METADATA")
        ]
        if len(metadata_files) != 1:
            raise RuntimeError("PACKAGE_METADATA_INVALID")
        metadata = archive.read(metadata_files[0]).decode("utf-8")
        if f"Version: {expected_version}\n" not in metadata:
            raise RuntimeError("PACKAGE_VERSION_MISMATCH")
        if "pm_agent/dashboard/web/index.html" not in archive.namelist():
            raise RuntimeError("DASHBOARD_ASSET_MISSING")
    return wheels[0], sdists[0]


def validate() -> None:
    python = sys.executable
    commit, dirty = source_identity()
    source_state = "HEAD plus working-tree changes" if dirty else "clean commit"
    print(f"Source identity: {commit} ({source_state})", flush=True)
    validate_tool_versions()
    runtime_env = os.environ.copy()
    runtime_env["PYTHONPATH"] = str(PACKAGE_ROOT)

    steps = [
        (
            "repository-boundary",
            [python, "tools/check_repository_boundary.py"],
            None,
        ),
        (
            "synthetic-samples",
            [python, "tools/check_synthetic_samples.py"],
            None,
        ),
        (
            "documented-use-cases",
            [python, "tools/check_documented_use_cases.py"],
            None,
        ),
        (
            "runtime-tests",
            [python, "-m", "pytest", "-q", "src/tests"],
            runtime_env,
        ),
        (
            "repository-tool-tests",
            [python, "-m", "pytest", "-q", "tools/tests"],
            None,
        ),
        (
            "ruff",
            [
                python,
                "-m",
                "ruff",
                "check",
                "src/pm_agent",
                "src/tests",
                "tools",
            ],
            None,
        ),
        (
            "compile",
            [
                python,
                "-m",
                "compileall",
                "-q",
                "src/pm_agent",
                "src/tests",
                "tools",
            ],
            None,
        ),
        ("diff-check", ["git", "diff", "--check"], None),
    ]
    for label, command, env in steps:
        run_step(label, command, env=env)

    with tempfile.TemporaryDirectory(prefix="dm-release-build-") as temp_dir:
        wheel, sdist = build_package(Path(temp_dir))
        print(f"Built wheel: {wheel.name}")
        print(f"Built sdist: {sdist.name}")

    print(
        f"\nRelease validation PASSED: {PROJECT_NAME} {package_version()} "
        f"({len(VALIDATION_STEPS)} checks)"
    )


if __name__ == "__main__":
    try:
        validate()
    except (RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"\nRelease validation FAILED: {type(exc).__name__}", file=sys.stderr)
        raise SystemExit(1) from exc
