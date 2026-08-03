from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from pm_agent.repo_tools import backup


def test_create_backup_point_works_without_git_repo(tmp_path: Path, monkeypatch) -> None:
    project_root = tmp_path / "bundle" / "src"
    project_root.mkdir(parents=True)
    data_dir = project_root / "data"
    data_dir.mkdir()
    db_path = data_dir / "pm.db"
    sqlite3.connect(db_path).close()

    monkeypatch.setattr(backup, "PROJECT_ROOT", project_root)
    monkeypatch.setattr(backup.settings, "database_path", str(db_path))

    point = backup.create_backup_point(label="bundle-user")

    assert point.git_repo_present is False
    assert point.branch == "bundle-workspace"
    assert point.commit_hash == "NO_GIT_WORKSPACE"
    assert point.db_snapshot_path is not None

    manifest = json.loads(Path(point.manifest_path).read_text(encoding="utf-8"))
    assert manifest["git_repo_present"] is False
    assert manifest["db_snapshot_path"]
    assert manifest["project_root"] == str(project_root)


def test_list_backup_points_reads_dynamic_manifest_directory(
    tmp_path: Path,
    monkeypatch,
) -> None:
    project_root = tmp_path / "runtime" / "src"
    project_root.mkdir(parents=True)
    monkeypatch.setattr(backup, "PROJECT_ROOT", project_root)

    manifest_dir = project_root.parent / f"{project_root.name}-backups" / "backup-manifests"
    manifest_dir.mkdir(parents=True)
    payload = {
        "tag_name": "backup-20260802-test",
        "branch": "bundle-workspace",
        "commit_hash": "NO_GIT_WORKSPACE",
        "created_at": "2026-08-02T00:00:00",
        "git_repo_present": False,
    }
    (manifest_dir / "backup-manifest-test.json").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )

    points = backup.list_backup_points()

    assert len(points) == 1
    assert points[0]["tag_name"] == "backup-20260802-test"
    assert points[0]["git_repo_present"] is False
