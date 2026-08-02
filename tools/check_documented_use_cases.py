#!/usr/bin/env python3
"""Validate that the documented shared use-case inventory matches the registry."""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
USE_CASE_REGISTRY = REPO_ROOT / "src" / "pm_agent" / "use_cases" / "__init__.py"
PACKAGE_README = REPO_ROOT / "src" / "README.md"


def extract_registered_use_case_ids(text: str) -> list[str]:
    return re.findall(r'use_case_id="([^"]+)"', text)


def extract_documented_use_case_ids(text: str) -> list[str]:
    match = re.search(
        r"(?ms)^Registered use cases cover:\n\n((?:- `[^`]+`\n)+)",
        text,
    )
    if match is None:
        raise RuntimeError("DOCUMENTED_USE_CASE_SECTION_MISSING")
    return re.findall(r"- `([^`]+)`", match.group(1))


def format_mismatch(registered: list[str], documented: list[str]) -> str:
    missing = [use_case_id for use_case_id in registered if use_case_id not in documented]
    extra = [use_case_id for use_case_id in documented if use_case_id not in registered]
    if not missing and not extra and registered != documented:
        return "USE_CASE_DOCUMENTATION_ORDER_MISMATCH"

    parts: list[str] = []
    if missing:
        parts.append("missing=" + ",".join(missing))
    if extra:
        parts.append("extra=" + ",".join(extra))
    return "USE_CASE_DOCUMENTATION_MISMATCH: " + "; ".join(parts)


def validate_documented_use_cases() -> None:
    registered = extract_registered_use_case_ids(
        USE_CASE_REGISTRY.read_text(encoding="utf-8")
    )
    documented = extract_documented_use_case_ids(
        PACKAGE_README.read_text(encoding="utf-8")
    )
    if registered != documented:
        raise RuntimeError(format_mismatch(registered, documented))
    print(
        f"Documented use cases: {len(documented)} entries match the shared registry",
        flush=True,
    )


if __name__ == "__main__":
    try:
        validate_documented_use_cases()
    except RuntimeError as exc:
        print(f"Documented use case validation FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
