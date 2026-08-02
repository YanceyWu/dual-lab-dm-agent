from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_package_and_runtime_versions_match() -> None:
    pyproject = (ROOT / "src/pyproject.toml").read_text(encoding="utf-8")
    runtime = (ROOT / "src/pm_agent/_version.py").read_text(encoding="utf-8")

    package_version = re.search(
        r'(?m)^version\s*=\s*"([^"]+)"',
        pyproject,
    )
    runtime_version = re.search(
        r'(?m)^__version__\s*=\s*"([^"]+)"',
        runtime,
    )

    assert package_version is not None
    assert runtime_version is not None
    assert package_version.group(1) == runtime_version.group(1)
    assert package_version.group(1) == "0.2.0rc1"


def test_unified_validation_and_ci_contract_are_present() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    validator = (ROOT / "tools/validate_release.py").read_text(encoding="utf-8")
    workflow = (ROOT / ".github/workflows/validate.yml").read_text(
        encoding="utf-8"
    )

    assert "validate:" in makefile
    assert "rehearse-release:" in makefile
    for required_step in (
        "repository-boundary",
        "synthetic-samples",
        "documented-use-cases",
        "runtime-tests",
        "repository-tool-tests",
        "ruff",
        "compile",
        "diff-check",
        "package-build",
    ):
        assert required_step in validator
    assert "make validate PYTHON=python" in workflow
    assert "make rehearse-release PYTHON=python" in workflow
    assert "contents: read" in workflow


def test_validation_dependencies_and_lint_rules_are_pinned() -> None:
    requirements = (
        ROOT / "tools/validation-requirements.txt"
    ).read_text(encoding="utf-8").splitlines()
    pyproject = (ROOT / "src/pyproject.toml").read_text(encoding="utf-8")
    workflow = (ROOT / ".github/workflows/validate.yml").read_text(
        encoding="utf-8"
    )

    assert requirements == [
        "build==1.5.0",
        "poetry-core==2.4.1",
        "pytest==9.1.1",
        "ruff==0.15.22",
    ]
    assert 'requires = ["poetry-core==2.4.1"]' in pyproject
    assert 'select = ["E4", "E7", "E9", "F"]' in pyproject
    assert "pip install -r tools/validation-requirements.txt" in workflow
