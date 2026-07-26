#!/usr/bin/env python3
"""Validate that portable sample files use the synthetic-data contract."""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Sequence
from urllib.parse import urlparse
from xml.etree import ElementTree


MARKER = "SYNTHETIC_DATASET_V1"
ALLOWED_EMAIL_DOMAIN = "example.invalid"
ALLOWED_URL_SUFFIX = ".example.invalid"
ID_PATTERN = re.compile(r"(?<![A-Z0-9])(\d{6,7})(?![A-Z0-9])", re.IGNORECASE)
EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@([A-Z0-9.-]+)\b", re.IGNORECASE)
URL_PATTERN = re.compile(r"https?://[^\s,\"'<>]+", re.IGNORECASE)
SUPPORTED_TEXT_SUFFIXES = {".csv", ".json", ".md"}


@dataclass(frozen=True)
class Finding:
    path: str
    reason: str


def validate_text(text: str, path: str, *, marker_required: bool = True) -> list[Finding]:
    findings: list[Finding] = []
    if marker_required and MARKER not in text:
        findings.append(Finding(path, "missing synthetic dataset marker"))

    for match in EMAIL_PATTERN.finditer(text):
        if match.group(1).lower() != ALLOWED_EMAIL_DOMAIN:
            findings.append(Finding(path, "email domain is not the reserved synthetic domain"))
            break

    for match in URL_PATTERN.finditer(text):
        hostname = (urlparse(match.group(0)).hostname or "").lower()
        if hostname != "example.invalid" and not hostname.endswith(ALLOWED_URL_SUFFIX):
            findings.append(Finding(path, "URL host is not under the reserved synthetic domain"))
            break

    for match in ID_PATTERN.finditer(text):
        if not match.group(1).startswith("99"):
            findings.append(Finding(path, "employee/project-style numeric ID is outside the synthetic range"))
            break

    return findings


def xlsx_text(path: Path) -> str:
    fragments: list[str] = []
    with zipfile.ZipFile(path) as archive:
        xml_names = [
            name
            for name in archive.namelist()
            if name == "xl/sharedStrings.xml" or name.startswith("xl/worksheets/sheet")
        ]
        for name in xml_names:
            root = ElementTree.fromstring(archive.read(name))
            fragments.extend(value for value in root.itertext() if value)
    return "\n".join(fragments)


def sqlite_text(path: Path) -> str:
    """Read text only from the expected generated sample DB."""
    if path.name != "sample_pm.db" or path.parent.name != "demo":
        raise ValueError("only sample-data/demo/sample_pm.db may be inspected")

    fragments: list[str] = []
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        tables = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
        for (table_name,) in tables:
            escaped = table_name.replace('"', '""')
            for row in connection.execute(f'SELECT * FROM "{escaped}"'):
                fragments.extend(str(value) for value in row if isinstance(value, str))
    finally:
        connection.close()
    return "\n".join(fragments)


def iter_sample_files(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*")):
        if path.is_file() and not path.name.startswith("."):
            yield path


def validate_sample_tree(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for path in iter_sample_files(root):
        relative = path.relative_to(root).as_posix()
        try:
            if path.suffix.lower() in SUPPORTED_TEXT_SUFFIXES:
                text = path.read_text(encoding="utf-8")
                findings.extend(validate_text(text, relative))
            elif path.suffix.lower() == ".xlsx":
                findings.extend(validate_text(xlsx_text(path), relative))
            elif path.suffix.lower() == ".db":
                findings.extend(validate_text(sqlite_text(path), relative))
            else:
                findings.append(Finding(relative, "unsupported sample artifact type"))
        except (OSError, ValueError, zipfile.BadZipFile, sqlite3.Error, ElementTree.ParseError):
            findings.append(Finding(relative, "sample artifact could not be safely inspected"))
    return findings


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("src/sample-data"))
    parser.add_argument("--json", action="store_true")
    options = parser.parse_args(argv)

    findings = validate_sample_tree(options.root.resolve())
    if options.json:
        print(json.dumps({"status": "fail" if findings else "pass", "findings": [asdict(item) for item in findings]}, indent=2))
    elif findings:
        print("Synthetic sample check FAILED:")
        for finding in findings:
            print(f"- {finding.path}: {finding.reason}")
    else:
        print("Synthetic sample check PASSED. All inspected artifacts satisfy the portable sample contract.")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
