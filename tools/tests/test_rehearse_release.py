from __future__ import annotations

import io
import importlib.util
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "tools" / "rehearse_release.py"
sys.path.insert(0, str(ROOT / "tools"))
SPEC = importlib.util.spec_from_file_location("rehearse_release", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
rehearse_release = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(rehearse_release)


def _archive_with_file() -> tarfile.TarFile:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as archive:
        payload = b"portable test payload"
        info = tarfile.TarInfo("sample.txt")
        info.size = len(payload)
        archive.addfile(info, io.BytesIO(payload))
    buffer.seek(0)
    return tarfile.open(fileobj=buffer, mode="r")


def test_extract_git_archive_uses_filter_when_available(
    tmp_path: Path,
    monkeypatch,
) -> None:
    with _archive_with_file() as archive:
        calls: list[tuple[Path, str | None]] = []

        def fake_extractall(path=".", members=None, *, numeric_owner=False, filter=None):
            calls.append((Path(path), filter))

        monkeypatch.setattr(archive, "extractall", fake_extractall)
        rehearse_release._extract_git_archive(archive, tmp_path)

    assert calls == [(tmp_path, "data")]


def test_extract_git_archive_falls_back_without_filter(tmp_path: Path) -> None:
    with _archive_with_file() as archive:
        rehearse_release._extract_git_archive(archive, tmp_path)

    assert (tmp_path / "sample.txt").read_text(encoding="utf-8") == "portable test payload"
