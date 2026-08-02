from __future__ import annotations

from pathlib import Path

from tools.check_documented_use_cases import (
    extract_documented_use_case_ids,
    extract_registered_use_case_ids,
    validate_documented_use_cases,
)

ROOT = Path(__file__).resolve().parents[2]


def test_extract_registered_use_case_ids_preserves_registry_order() -> None:
    text = '''
use_case_id="alpha"
use_case_id="beta"
use_case_id="gamma"
'''
    assert extract_registered_use_case_ids(text) == ["alpha", "beta", "gamma"]


def test_extract_documented_use_case_ids_reads_markdown_section() -> None:
    text = """
Registered use cases cover:

- `alpha`
- `beta`
- `gamma`
"""
    assert extract_documented_use_case_ids(text) == ["alpha", "beta", "gamma"]


def test_documented_use_case_inventory_matches_repository() -> None:
    validate_documented_use_cases()


def test_documented_use_case_section_exists_in_package_readme() -> None:
    package_readme = (ROOT / "src/README.md").read_text(encoding="utf-8")
    assert "Registered use cases cover:" in package_readme
