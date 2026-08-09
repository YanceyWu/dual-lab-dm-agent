"""Atomic export helpers for user-maintained onboarding source artifacts."""

from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path
from typing import Any, Callable


class SourceExportError(RuntimeError):
    """A stable, operator-safe failure raised while materialising an export."""


def write_atomically(
    output: str | Path,
    *,
    overwrite: bool,
    write: Callable[[Path], None],
) -> tuple[Path, str]:
    """Write an artifact beside its destination without implicit replacement.

    ``os.link`` gives the no-overwrite path create-if-absent semantics even if
    another process creates the requested name after the initial check.
    """

    target = Path(output).expanduser().resolve(strict=False)
    if not target.parent.is_dir():
        raise SourceExportError("DATA_ONBOARDING_EXPORT_DIRECTORY_NOT_FOUND")
    if target.exists() and not overwrite:
        raise SourceExportError("DATA_ONBOARDING_EXPORT_OUTPUT_EXISTS")

    descriptor, temporary_name = tempfile.mkstemp(
        # Workbook parsers dispatch on the suffix, so an XLSX temporary must
        # retain `.xlsx` while still living beside its final destination.
        prefix=f".{target.stem}.", suffix=f".tmp{target.suffix}", dir=target.parent
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        write(temporary)
        if not temporary.is_file():
            raise SourceExportError("DATA_ONBOARDING_EXPORT_WRITE_FAILED")
        if overwrite:
            os.replace(temporary, target)
        else:
            try:
                os.link(temporary, target)
            except FileExistsError as exc:
                raise SourceExportError("DATA_ONBOARDING_EXPORT_OUTPUT_EXISTS") from exc
            temporary.unlink()
        return target, _sha256(target)
    except SourceExportError:
        raise
    except OSError as exc:
        raise SourceExportError("DATA_ONBOARDING_EXPORT_WRITE_FAILED") from exc
    finally:
        temporary.unlink(missing_ok=True)


def failed_export(source_type: str, code: str) -> dict[str, object]:
    return {
        "status": "failed",
        "source_type": source_type,
        "warnings": [code],
    }


def export_source(
    source_type: str,
    output: str | Path,
    *,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Dispatch the three supported editable-source exports.

    Imports are deliberately local: each source owner may use the shared atomic
    writer without creating an import cycle through this thin CLI adapter.
    """

    suffixes = {
        "project-profile-workbook": ".xlsx",
        "jira-board-registry-csv": ".csv",
        "confluence-page-registry-csv": ".csv",
    }
    if source_type not in suffixes:
        return failed_export(source_type, "DATA_ONBOARDING_EXPORT_SOURCE_TYPE_UNSUPPORTED")
    if Path(output).suffix.lower() != suffixes[source_type]:
        return failed_export(source_type, "DATA_ONBOARDING_EXPORT_OUTPUT_SUFFIX_INVALID")
    if source_type == "project-profile-workbook":
        from pm_agent.project_profile_import import export_project_profile_workbook

        return export_project_profile_workbook(output, overwrite=overwrite)
    if source_type == "jira-board-registry-csv":
        from pm_agent.connectors.jira.board_registry import export_registry_csv

        return export_registry_csv(output, overwrite=overwrite)
    from pm_agent.connectors.confluence.page_registry import export_registry_csv

    return export_registry_csv(output, overwrite=overwrite)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
