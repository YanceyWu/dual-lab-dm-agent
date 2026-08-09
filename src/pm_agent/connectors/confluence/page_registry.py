"""Confluence page-registry owner logic shared by scripts and onboarding wrappers."""

from __future__ import annotations

import csv
import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

from pm_agent.config import settings
from pm_agent.data_onboarding.source_export import (
    SourceExportError,
    failed_export,
    write_atomically,
)

REQUIRED_COLUMNS = ("id", "board_id")
OPTIONAL_COLUMNS = (
    "title",
    "page_type",
    "last_synced",
    "last_modified",
    "content_summary",
)


def load_registry_rows(file_path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with file_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        rows = [dict(row) for row in reader]
    return fieldnames, rows


def preview_registry_import(
    file_path: Path,
    *,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    fieldnames, rows = load_registry_rows(file_path)
    parsed = _parse_rows(fieldnames, rows)
    if parsed["status"] == "rejected":
        return parsed
    normalized_rows = parsed["rows"]
    desired_pages = _desired_pages(normalized_rows)
    counts = _counts(normalized_rows, desired_pages)
    return {
        "status": (
            "already_completed"
            if _matches_current_state(
                desired_pages,
                incoming_page_ids=[str(row["id"]) for row in normalized_rows],
                incoming_board_ids=[str(row["board_id"]) for row in normalized_rows],
                db_path=db_path,
            )
            else "previewed"
        ),
        "blockers": [],
        "warnings": [],
        "conflicts": [],
        "counts": counts,
        "payload": {
            "registry_fingerprint": _fingerprint(normalized_rows),
            "publication_id": _publication_id(normalized_rows),
            "page_ids": [row["id"] for row in normalized_rows],
            "board_ids": [row["board_id"] for row in desired_pages],
        },
        "report": {
            "coverage": {
                "state": "complete",
                "registry_rows": counts["registry_rows"],
                "managed_pages": counts["managed_pages"],
                "status_boards": counts["status_boards"],
                "recovery_pages": counts["recovery_pages"],
            },
            "reconciliation_mode": "full_sync",
            "cleanup_scope": [
                "confluence_pages_non_global",
                "confluence_status_snapshots",
                "action_tracker_for_removed_pages",
            ],
            "preserved_semantics": {
                "preserve_global_pages": True,
                "board_scoped_page_replacement": True,
            },
        },
    }


def apply_registry_import(
    file_path: Path,
    *,
    dry_run: bool = False,
    merge_only: bool = False,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    fieldnames, rows = load_registry_rows(file_path)
    parsed = _parse_rows(fieldnames, rows)
    if parsed["status"] == "rejected":
        blocker = parsed["blockers"][0]
        raise ValueError(str(blocker["message"]))
    normalized_rows = parsed["rows"]
    desired_pages = _desired_pages(normalized_rows)
    counts = _counts(normalized_rows, desired_pages)
    if dry_run:
        return {
            "loaded_rows": len(normalized_rows),
            "counts": counts,
            "dry_run_rows": [
                {
                    "board_id": row["board_id"],
                    "id": row["id"],
                    "page_type": row["page_type"] or "status_page",
                }
                for row in normalized_rows[:5]
            ],
            "merge_only": merge_only,
        }

    connection = sqlite3.connect(_db_path(db_path))
    removed_pages = 0
    removed_boards = 0
    imported = 0
    try:
        if not merge_only:
            removed_pages, removed_boards = _delete_stale_pages(
                connection,
                incoming_page_ids=[str(row["id"]) for row in normalized_rows],
                incoming_board_ids=[str(row["board_id"]) for row in normalized_rows],
            )
        for row in normalized_rows:
            connection.execute(
                "DELETE FROM confluence_pages WHERE board_id = ? AND id <> ?",
                [row["board_id"], row["id"]],
            )
            connection.execute(
                """
                INSERT INTO confluence_pages
                    (id, board_id, title, page_type, last_synced, last_modified, content_summary)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    board_id = excluded.board_id,
                    title = excluded.title,
                    page_type = excluded.page_type,
                    last_synced = excluded.last_synced,
                    last_modified = excluded.last_modified,
                    content_summary = excluded.content_summary
                """,
                [
                    row["id"],
                    row["board_id"],
                    row["title"],
                    row["page_type"],
                    row["last_synced"],
                    row["last_modified"],
                    row["content_summary"],
                ],
            )
            imported += 1
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

    return {
        "status": "completed",
        "loaded_rows": len(normalized_rows),
        "imported_rows": imported,
        "removed_pages": removed_pages,
        "removed_boards": removed_boards,
        "counts": counts,
        "payload": {
            "registry_fingerprint": _fingerprint(normalized_rows),
            "publication_id": _publication_id(normalized_rows),
            "page_ids": [row["id"] for row in normalized_rows],
            "board_ids": [row["board_id"] for row in desired_pages],
        },
        "report": {
            "coverage": {
                "state": "complete",
                "registry_rows": counts["registry_rows"],
                "managed_pages": counts["managed_pages"],
                "status_boards": counts["status_boards"],
                "recovery_pages": counts["recovery_pages"],
            },
            "reconciliation_mode": "full_sync" if not merge_only else "merge_only",
            "result": {
                "imported_rows": imported,
                "removed_pages": removed_pages,
                "removed_board_snapshots": removed_boards,
            },
            "preserved_semantics": {
                "preserve_global_pages": True,
                "board_scoped_page_replacement": True,
            },
        },
    }


def export_registry_csv(
    output: str | Path,
    *,
    overwrite: bool = False,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    """Export editable page mappings, never connector content or sync timestamps."""

    source_type = "confluence-page-registry-csv"
    connection = sqlite3.connect(_db_path(db_path))
    try:
        rows = connection.execute(
            """
            SELECT id, board_id, title, page_type
            FROM confluence_pages
            WHERE board_id != 'global'
            ORDER BY board_id, id
            """
        ).fetchall()
    except sqlite3.OperationalError:
        return failed_export(source_type, "CONFLUENCE_PAGE_REGISTRY_EXPORT_SOURCE_UNAVAILABLE")
    finally:
        connection.close()

    try:
        expected_rows = [_exportable_registry_row(row) for row in rows]
        if len({row["board_id"] for row in expected_rows}) != len(expected_rows):
            raise ValueError("multiple pages would collapse into one board mapping")
    except ValueError:
        return failed_export(source_type, "CONFLUENCE_PAGE_REGISTRY_EXPORT_SOURCE_UNREPRESENTABLE")

    fields = [*REQUIRED_COLUMNS, *OPTIONAL_COLUMNS]

    def write(path: Path) -> None:
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(_registry_csv_row(row) for row in expected_rows)
        fieldnames, exported_rows = load_registry_rows(path)
        parsed = _parse_rows(fieldnames, exported_rows)
        preview = preview_registry_import(path, db_path=db_path)
        if (
            parsed["status"] == "rejected"
            or preview["status"] == "rejected"
            or parsed["rows"] != expected_rows
            or len(_desired_pages(parsed["rows"])) != len(expected_rows)
        ):
            raise SourceExportError("CONFLUENCE_PAGE_REGISTRY_EXPORT_SOURCE_UNREPRESENTABLE")

    try:
        target, digest = write_atomically(output, overwrite=overwrite, write=write)
    except SourceExportError as exc:
        return failed_export(source_type, str(exc))
    return {
        "status": "exported", "source_type": source_type, "output_path": str(target),
        "sha256": digest, "counts": {"registry_rows": len(expected_rows)}, "warnings": [],
        "source_identity": {"kind": "local_sqlite", "source_type": source_type},
    }


def _exportable_registry_row(row: tuple[Any, ...]) -> dict[str, Any]:
    page_id, board_id, title, page_type = row
    if (
        not _canonical_required_text(page_id)
        or not _canonical_required_text(board_id)
        or board_id == "global"
        or not _canonical_optional_text(title)
        or not _canonical_required_text(page_type)
    ):
        raise ValueError("unrepresentable page mapping")
    return {
        "id": page_id,
        "board_id": board_id,
        "title": title or "",
        "page_type": page_type,
        # These optional import columns are intentionally emitted blank: they
        # are connector-derived content/timestamps, never re-import source facts.
        "last_synced": "",
        "last_modified": "",
        "content_summary": "",
    }


def _canonical_required_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip()) and value == value.strip()


def _canonical_optional_text(value: object) -> bool:
    return value is None or (
        isinstance(value, str) and bool(value) and value == value.strip()
    )


def _registry_csv_row(row: dict[str, Any]) -> dict[str, Any]:
    return {key: row[key] for key in (*REQUIRED_COLUMNS, *OPTIONAL_COLUMNS)}


def _parse_rows(fieldnames: list[str], rows: list[dict[str, str]]) -> dict[str, Any]:
    missing_columns = sorted(column for column in REQUIRED_COLUMNS if column not in fieldnames)
    if missing_columns:
        return _rejected(
            code="CONFLUENCE_PAGE_REGISTRY_CSV_COLUMNS_INVALID",
            message=(
                "Confluence page registry CSV is missing required columns: "
                f"{', '.join(missing_columns)}."
            ),
            location="source_locator",
        )
    normalized_rows: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=2):
        page_id = (row.get("id") or "").strip()
        board_id = (row.get("board_id") or "").strip()
        if not page_id or not board_id:
            return _rejected(
                code="CONFLUENCE_PAGE_REGISTRY_ROW_INVALID",
                message=f"Row {index} must include id and board_id.",
                location=f"row:{index}",
            )
        normalized_rows.append(
            {
                "id": page_id,
                "board_id": board_id,
                "title": (row.get("title") or "").strip(),
                "page_type": (row.get("page_type") or "").strip() or "status_page",
                "last_synced": (row.get("last_synced") or "").strip(),
                "last_modified": (row.get("last_modified") or "").strip(),
                "content_summary": (row.get("content_summary") or "").strip(),
            }
        )
    return {"status": "previewed", "rows": normalized_rows}


def _rejected(*, code: str, message: str, location: str) -> dict[str, Any]:
    return {
        "status": "rejected",
        "blockers": [
            {
                "severity": "blocker",
                "code": code,
                "message": message,
                "location": location,
            }
        ],
        "warnings": [],
        "conflicts": [],
        "counts": {},
        "payload": {},
        "report": {"coverage": {"state": "not_available"}},
    }


def _desired_pages(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    final_by_board: dict[str, dict[str, Any]] = {}
    for row in rows:
        final_by_board[str(row["board_id"])] = row
    return [final_by_board[key] for key in sorted(final_by_board)]


def _counts(
    rows: list[dict[str, Any]],
    desired_pages: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "registry_rows": len(rows),
        "managed_pages": len(desired_pages),
        "status_boards": sum(row["page_type"] == "status_page" for row in desired_pages),
        "recovery_pages": sum(row["page_type"] == "recovery_page" for row in desired_pages),
    }


def _fingerprint(rows: list[dict[str, Any]]) -> str:
    digest = hashlib.sha256()
    digest.update(
        json.dumps(rows, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
            "utf-8"
        )
    )
    return digest.hexdigest()


def _publication_id(rows: list[dict[str, Any]]) -> str:
    return f"confluence-page-registry:{_fingerprint(rows)}"


def _db_path(db_path: str | Path | None) -> Path:
    return Path(db_path or settings.database_path)


def _delete_stale_pages(
    connection: sqlite3.Connection,
    *,
    incoming_page_ids: list[str],
    incoming_board_ids: list[str],
) -> tuple[int, int]:
    stale_page_ids = (
        [
            row[0]
            for row in connection.execute(
                (
                    "SELECT id FROM confluence_pages WHERE board_id != 'global' "
                    f"AND id NOT IN ({','.join('?' for _ in incoming_page_ids)})"
                ),
                incoming_page_ids,
            ).fetchall()
        ]
        if incoming_page_ids
        else [
            row[0]
            for row in connection.execute(
                "SELECT id FROM confluence_pages WHERE board_id != 'global'"
            ).fetchall()
        ]
    )
    stale_board_ids = (
        [
            row[0]
            for row in connection.execute(
                (
                    "SELECT DISTINCT board_id FROM confluence_pages WHERE board_id != 'global' "
                    f"AND board_id NOT IN ({','.join('?' for _ in incoming_board_ids)})"
                ),
                incoming_board_ids,
            ).fetchall()
        ]
        if incoming_board_ids
        else [
            row[0]
            for row in connection.execute(
                "SELECT DISTINCT board_id FROM confluence_pages WHERE board_id != 'global'"
            ).fetchall()
        ]
    )
    if stale_page_ids:
        placeholders = ",".join("?" for _ in stale_page_ids)
        connection.execute(
            f"DELETE FROM action_tracker WHERE page_id IN ({placeholders})",
            stale_page_ids,
        )
        connection.execute(
            f"DELETE FROM confluence_pages WHERE id IN ({placeholders})",
            stale_page_ids,
        )
    if stale_board_ids:
        placeholders = ",".join("?" for _ in stale_board_ids)
        connection.execute(
            f"DELETE FROM confluence_status_snapshots WHERE board_id IN ({placeholders})",
            stale_board_ids,
        )
    return len(stale_page_ids), len(stale_board_ids)


def _matches_current_state(
    desired_pages: list[dict[str, Any]],
    *,
    incoming_page_ids: list[str],
    incoming_board_ids: list[str],
    db_path: str | Path | None = None,
) -> bool:
    try:
        connection = sqlite3.connect(_db_path(db_path))
        current_rows = connection.execute(
            """
            SELECT id, board_id, title, page_type, last_synced, last_modified, content_summary
            FROM confluence_pages
            WHERE board_id != 'global'
            ORDER BY board_id
            """
        ).fetchall()
        current_pages = [
            {
                "id": row[0],
                "board_id": row[1],
                "title": row[2] or "",
                "page_type": row[3] or "status_page",
                "last_synced": row[4] or "",
                "last_modified": row[5] or "",
                "content_summary": row[6] or "",
            }
            for row in current_rows
        ]
        if current_pages != desired_pages:
            return False
        if _has_stale_status_snapshots(connection, incoming_board_ids):
            return False
        if _has_stale_action_tracker_rows(connection):
            return False
        return True
    except sqlite3.OperationalError:
        return False
    finally:
        try:
            connection.close()
        except Exception:
            pass


def _has_stale_status_snapshots(
    connection: sqlite3.Connection,
    incoming_board_ids: list[str],
) -> bool:
    if incoming_board_ids:
        placeholders = ",".join("?" for _ in incoming_board_ids)
        row = connection.execute(
            (
                "SELECT 1 FROM confluence_status_snapshots "
                f"WHERE board_id NOT IN ({placeholders}) LIMIT 1"
            ),
            incoming_board_ids,
        ).fetchone()
    else:
        row = connection.execute(
            "SELECT 1 FROM confluence_status_snapshots LIMIT 1"
        ).fetchone()
    return row is not None


def _has_stale_action_tracker_rows(
    connection: sqlite3.Connection,
) -> bool:
    row = connection.execute(
        """
        SELECT 1
        FROM action_tracker
        WHERE page_id NOT IN (SELECT id FROM confluence_pages)
        LIMIT 1
        """
    ).fetchone()
    return row is not None
