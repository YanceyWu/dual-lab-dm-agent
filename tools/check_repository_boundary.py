#!/usr/bin/env python3
"""Fail when private local state is visible to Git.

The check only inspects repository paths reported by Git. It never opens or
parses a database, export, credential file, or any other candidate artifact.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import PurePosixPath
from typing import Iterable, Sequence


PROTECTED_PREFIXES = (
    "src/data/",
    "src/data-feed/",
    "src/.auth/",
    "src/.venv/",
    "src/backups/",
    "src/exports/",
    "src/logs/",
    "src/configs/company/",
    "src/docs/history/",
    "secrets/",
    "company-source/",
    "company-data/",
    "screenshots/",
    "raw-exports/",
)

PROTECTED_DATABASE_SUFFIXES = (
    ".db",
    ".db-journal",
    ".db-shm",
    ".db-wal",
    ".sqlite",
    ".sqlite3",
)

ALLOWED_SAMPLE_PREFIX = "src/sample-data/"
QUARANTINED_TRANSFER_PREFIXES: tuple[str, ...] = ()
QUARANTINE_EXCEPTIONS: tuple[str, ...] = ()


@dataclass(frozen=True)
class Violation:
    path: str
    source: str
    reason: str


def normalize_path(path: str) -> str:
    """Return a stable repository-relative path without reading the target."""
    normalized = path.strip().replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return PurePosixPath(normalized).as_posix()


def private_reason(path: str) -> str | None:
    """Describe why a repository path is private, or return None."""
    normalized = normalize_path(path)
    lowered = normalized.lower()

    if lowered.startswith(ALLOWED_SAMPLE_PREFIX):
        return None

    for prefix in PROTECTED_PREFIXES:
        if lowered.startswith(prefix):
            return f"protected local-state path: {prefix}"

    name = PurePosixPath(lowered).name
    if lowered.startswith("src/docs/current/") and "uat" in name:
        return "internal validation artifact"

    if name != ".env.example" and (name == ".env" or name.startswith(".env.")):
        return "environment or credential file"

    if name.endswith(PROTECTED_DATABASE_SUFFIXES):
        return "database file outside the sanitized sample-data boundary"

    if name.endswith(".log"):
        return "runtime log file"

    return None


def repository_reason(path: str, source: str) -> str | None:
    """Apply privacy rules plus any active public-transfer quarantine."""
    normalized = normalize_path(path)
    lowered = normalized.lower()

    if source in {"tracked", "staged"}:
        is_exception = any(lowered.startswith(prefix) for prefix in QUARANTINE_EXCEPTIONS)
        if not is_exception:
            for prefix in QUARANTINED_TRANSFER_PREFIXES:
                if lowered.startswith(prefix):
                    return "runtime source is quarantined pending portability review"

    return private_reason(normalized)


def scan_paths(paths: Iterable[str], source: str) -> list[Violation]:
    violations: list[Violation] = []
    for path in paths:
        normalized = normalize_path(path)
        if reason := repository_reason(normalized, source):
            violations.append(Violation(normalized, source, reason))
    return violations


def git_paths(args: Sequence[str]) -> list[str]:
    result = subprocess.run(
        ["git", *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=False,
    )
    return [item.decode("utf-8", errors="replace") for item in result.stdout.split(b"\0") if item]


def collect_violations() -> list[Violation]:
    inventories = (
        ("tracked", ("ls-files", "-z")),
        ("staged", ("diff", "--cached", "--name-only", "-z", "--diff-filter=ACMR")),
        ("untracked-and-not-ignored", ("ls-files", "--others", "--exclude-standard", "-z")),
    )

    found: dict[tuple[str, str], Violation] = {}
    for source, args in inventories:
        for violation in scan_paths(git_paths(args), source):
            found[(violation.path, violation.source)] = violation
    return sorted(found.values(), key=lambda item: (item.path, item.source))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit machine-readable output")
    options = parser.parse_args(argv)

    try:
        violations = collect_violations()
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"repository-boundary check could not inspect Git metadata: {exc}", file=sys.stderr)
        return 2

    if options.json:
        print(json.dumps({"status": "fail" if violations else "pass", "violations": [asdict(v) for v in violations]}, indent=2))
    elif violations:
        print("Repository boundary check FAILED. Private local state is visible to Git:")
        for violation in violations:
            print(f"- {violation.path} [{violation.source}]: {violation.reason}")
    else:
        print("Repository boundary check PASSED. No private local-state paths are visible to Git.")

    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
