from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from pm_agent.config import settings
from pm_agent.rules.identity import slugify_text

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TAG_PREFIX = "backup-"


class BackupError(RuntimeError):
    pass


@dataclass
class BackupPoint:
    tag_name: str
    commit_hash: str
    branch: str
    created_at: str
    db_snapshot_path: str | None
    manifest_path: str
    dirty_worktree: bool
    label: str
    note: str
    status_lines: list[str]
    git_repo_present: bool


def _run_git(args: list[str], check: bool = True) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )
    stdout = proc.stdout.strip()
    stderr = proc.stderr.strip()
    if check and proc.returncode != 0:
        raise BackupError(stderr or stdout or f"git {' '.join(args)} failed")
    return stdout


def _database_path() -> Path:
    db_path = Path(settings.database_path)
    if not db_path.is_absolute():
        db_path = PROJECT_ROOT / db_path
    return db_path


def _backup_root() -> Path:
    return PROJECT_ROOT.parent / f"{PROJECT_ROOT.name}-backups"


def _db_snapshot_dir() -> Path:
    return _backup_root() / "db-snapshots"


def _manifest_dir() -> Path:
    return _backup_root() / "backup-manifests"


def _git_repo_present() -> bool:
    if not (PROJECT_ROOT / ".git").exists():
        return False
    proc = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )
    return proc.returncode == 0


def _tag_exists(tag_name: str) -> bool:
    proc = subprocess.run(
        ["git", "rev-parse", "-q", "--verify", f"refs/tags/{tag_name}"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )
    return proc.returncode == 0


def create_backup_point(
    label: str = "",
    note: str = "",
    include_db_snapshot: bool = True,
    allow_dirty: bool = False,
) -> BackupPoint:
    git_repo_present = _git_repo_present()

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    label_slug = slugify_text(label)[:40]
    suffix = f"-{label_slug}" if label_slug else ""
    tag_name = f"{TAG_PREFIX}{timestamp}{suffix}"
    if git_repo_present and _tag_exists(tag_name):
        raise BackupError(f"Tag {tag_name} already exists")

    if git_repo_present:
        status_output = _run_git(["status", "--short"])
        status_lines = [line for line in status_output.splitlines() if line.strip()]
        dirty_worktree = bool(status_lines)
        if dirty_worktree and not allow_dirty:
            raise BackupError(
                "Git working tree has uncommitted changes. Commit/stash them first, "
                "or rerun with --allow-dirty if you intentionally want a tag on HEAD only."
            )
        commit_hash = _run_git(["rev-parse", "HEAD"])
        branch = _run_git(["rev-parse", "--abbrev-ref", "HEAD"])
    else:
        status_lines = []
        dirty_worktree = False
        commit_hash = "NO_GIT_WORKSPACE"
        branch = "bundle-workspace"
    created_at = datetime.now().isoformat(timespec="seconds")
    db_snapshot_path: Path | None = None
    tag_created = False

    try:
        if include_db_snapshot:
            db_path = _database_path()
            if db_path.exists():
                snapshot_dir = _db_snapshot_dir()
                snapshot_dir.mkdir(parents=True, exist_ok=True)
                db_snapshot_path = snapshot_dir / f"{db_path.stem}-snapshot-{timestamp}{suffix}{db_path.suffix}"
                shutil.copy2(db_path, db_snapshot_path)
            else:
                raise BackupError(f"Database file does not exist: {db_path}")

        if git_repo_present:
            subject = f"Backup point {tag_name}"
            body_lines = [
                f"Branch: {branch}",
                f"Commit: {commit_hash}",
            ]
            if label:
                body_lines.append(f"Label: {label}")
            if note:
                body_lines.append(f"Note: {note}")
            if db_snapshot_path:
                body_lines.append(f"DB snapshot: {db_snapshot_path}")
            if dirty_worktree:
                body_lines.append(
                    "Warning: uncommitted working tree changes were present; "
                    "this tag only captures the current HEAD commit."
                )
            tag_args = ["tag", "-a", tag_name, "-m", subject]
            if body_lines:
                tag_args.extend(["-m", "\n".join(body_lines)])
            _run_git(tag_args)
            tag_created = True

        manifest_dir = _manifest_dir()
        manifest_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = manifest_dir / f"backup-manifest-{timestamp}{suffix}.json"
        manifest = {
            "tag_name": tag_name,
            "branch": branch,
            "commit_hash": commit_hash,
            "created_at": created_at,
            "label": label,
            "note": note,
            "dirty_worktree": dirty_worktree,
            "status_lines": status_lines,
            "git_repo_present": git_repo_present,
            "database_path": str(_database_path()),
            "db_snapshot_path": str(db_snapshot_path) if db_snapshot_path else None,
            "project_root": str(PROJECT_ROOT),
        }
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        return BackupPoint(
            tag_name=tag_name,
            commit_hash=commit_hash,
            branch=branch,
            created_at=created_at,
            db_snapshot_path=str(db_snapshot_path) if db_snapshot_path else None,
            manifest_path=str(manifest_path),
            dirty_worktree=dirty_worktree,
            label=label,
            note=note,
            status_lines=status_lines,
            git_repo_present=git_repo_present,
        )
    except Exception:
        if tag_created:
            subprocess.run(
                ["git", "tag", "-d", tag_name],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
            )
        if db_snapshot_path and db_snapshot_path.exists():
            db_snapshot_path.unlink()
        raise


def list_backup_points(limit: int = 10) -> list[dict[str, Any]]:
    points: list[dict[str, Any]] = []
    manifest_dir = _manifest_dir()
    if manifest_dir.exists():
        files = sorted(
            manifest_dir.glob("backup-manifest-*.json"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        for path in files[:limit]:
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            payload["manifest_path"] = str(path)
            points.append(payload)
    return points
