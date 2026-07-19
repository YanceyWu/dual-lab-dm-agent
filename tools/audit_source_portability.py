#!/usr/bin/env python3
"""Report source-portability blockers without printing matched values."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Sequence
from urllib.parse import urlparse


TEXT_SUFFIXES = {
    ".py",
    ".yaml",
    ".yml",
    ".json",
    ".md",
    ".txt",
    ".js",
    ".html",
    ".css",
    ".toml",
    ".sql",
    ".example",
}
SKIP_PARTS = {".venv", "__pycache__", ".pytest_cache", "data", "data-feed", "sample-data", "backups", "exports", "logs"}
URL_PATTERN = re.compile(r"https?://[^\s\"'<>]+", re.IGNORECASE)
EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@([A-Z0-9.-]+)\b", re.IGNORECASE)
QUOTED_ID_PATTERN = re.compile(r"[\"'](\d{6,10})[\"']")
ABSOLUTE_USER_PATH_PATTERN = re.compile(r"(?:/Users/|[A-Z]:\\Users\\)", re.IGNORECASE)
PUBLIC_VENDOR_HOSTS = {
    "api.atlassian.com",
    "auth.atlassian.com",
}


@dataclass(frozen=True)
class Finding:
    path: str
    category: str


def iter_source_files(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if any(part in SKIP_PARTS for part in path.relative_to(root).parts):
            continue
        yield path


def inspect_text(text: str, relative_path: str) -> set[Finding]:
    findings: set[Finding] = set()

    for match in URL_PATTERN.finditer(text):
        raw_url = match.group(0)
        if any(token in raw_url for token in ("[", "]", "{", "}")):
            continue
        try:
            hostname = (urlparse(raw_url).hostname or "").lower()
        except ValueError:
            findings.add(Finding(relative_path, "malformed-or-template-url"))
            break
        if (
            hostname not in PUBLIC_VENDOR_HOSTS
            and hostname != "example.invalid"
            and not hostname.endswith(".example.invalid")
        ):
            findings.add(Finding(relative_path, "concrete-url-in-portable-source"))
            break

    for match in EMAIL_PATTERN.finditer(text):
        if match.group(1).lower() != "example.invalid":
            findings.add(Finding(relative_path, "non-synthetic-email-domain"))
            break

    if ABSOLUTE_USER_PATH_PATTERN.search(text):
        findings.add(Finding(relative_path, "absolute-user-path"))

    for match in QUOTED_ID_PATTERN.finditer(text):
        identifier = match.group(1)
        if set(identifier) == {"0"}:
            continue
        if not identifier.startswith("99"):
            findings.add(Finding(relative_path, "hard-coded-numeric-identifier"))
            break

    return findings


def _internal_unit_category(relative_path: str) -> str | None:
    if relative_path.startswith("configs/company/"):
        return "company-configuration-unit"
    if relative_path.startswith("docs/history/"):
        return "historical-documentation-unit"
    if relative_path.startswith("docs/current/") and "UAT" in Path(relative_path).name.upper():
        return "internal-validation-artifact"
    return None


def audit(root: Path, include_internal: bool = True) -> list[Finding]:
    findings: set[Finding] = set()
    for path in iter_source_files(root):
        relative = path.relative_to(root).as_posix()
        internal_category = _internal_unit_category(relative)
        if internal_category:
            if include_internal:
                findings.add(Finding(relative, internal_category))
            else:
                continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            findings.add(Finding(relative, "unreadable-text-artifact"))
            continue
        findings.update(inspect_text(text, relative))
    return sorted(findings, key=lambda item: (item.path, item.category))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("src"))
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--portable-only",
        action="store_true",
        help="exclude units permanently classified as internal-only",
    )
    options = parser.parse_args(argv)

    findings = audit(options.root.resolve(), include_internal=not options.portable_only)
    counts = Counter(item.category for item in findings)
    if options.json:
        print(
            json.dumps(
                {
                    "status": "blocked" if findings else "pass",
                    "counts": dict(sorted(counts.items())),
                    "findings": [asdict(item) for item in findings],
                },
                indent=2,
            )
        )
    elif findings:
        print("Source portability audit BLOCKED.")
        print("Category counts:")
        for category, count in sorted(counts.items()):
            print(f"- {category}: {count}")
        print("Affected paths (matched values are intentionally suppressed):")
        for finding in findings:
            print(f"- {finding.path}: {finding.category}")
    else:
        print("Source portability audit PASSED for the inspected text units.")

    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
