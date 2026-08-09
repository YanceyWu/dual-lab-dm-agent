"""JIRA board-registry owner logic shared by scripts and onboarding wrappers."""

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

REQUIRED_COLUMNS = ("id", "name", "project_key", "base_jql")
OPTIONAL_COLUMNS = (
    "version_name_pattern",
    "board_id",
    "board_url",
    "pm_project_id",
    "active",
    "issues_use_base_jql",
    "notes",
)
EVIDENCE_LOCAL_CONFIG_KEYS = {
    "field_mappings",
    "supported_link_types",
    "bootstrap_days",
    "overlap_seconds",
    "page_size",
    "max_pages",
    "max_issues",
}


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
    counts = _counts(normalized_rows)
    return {
        "status": (
            "already_completed"
            if _matches_current_state(normalized_rows, db_path=db_path)
            else "previewed"
        ),
        "blockers": [],
        "warnings": [],
        "conflicts": [],
        "counts": counts,
        "payload": {
            "registry_fingerprint": _fingerprint(normalized_rows),
            "publication_id": _publication_id(normalized_rows),
            "board_ids": [row["id"] for row in normalized_rows],
            "project_keys": sorted({str(row["project_key"]) for row in normalized_rows}),
        },
        "report": {
            "coverage": {
                "state": "complete",
                "registry_rows": counts["registry_rows"],
                "active_boards": counts["active_boards"],
                "inactive_boards": counts["inactive_boards"],
                "project_keys": counts["project_keys"],
                "managed_data_sources": counts["managed_data_sources"],
            },
            "reconciliation_mode": "full_sync",
            "cleanup_scope": [
                "jira_board_configs",
                "jira_stream_versions",
                "jira_issues",
                "jira_sprints",
                "jira_health_snapshots",
                "csv_import_project_key_facts",
            ],
            "preserved_semantics": {
                "carry_forward_evidence_local_config": True,
                "preserve_issue_event_history": True,
                "preserve_evidence_cursors": True,
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
    counts = _counts(normalized_rows)
    if dry_run:
        return {
            "loaded_rows": len(normalized_rows),
            "counts": counts,
            "dry_run_rows": [
                {
                    "id": row["id"],
                    "project_key": row["project_key"],
                    "version_name_pattern": row["version_name_pattern"]
                    or "(no version filter)",
                }
                for row in normalized_rows[:5]
            ],
            "merge_only": merge_only,
        }

    connection = sqlite3.connect(_db_path(db_path))
    imported = 0
    removed = 0
    try:
        if not merge_only:
            incoming_board_ids = [str(row["id"]) for row in normalized_rows]
            if incoming_board_ids:
                stale_board_ids = [
                    row[0]
                    for row in connection.execute(
                        (
                            "SELECT id FROM jira_board_configs "
                            f"WHERE id NOT IN ({','.join('?' for _ in incoming_board_ids)})"
                        ),
                        incoming_board_ids,
                    ).fetchall()
                ]
            else:
                stale_board_ids = [
                    row[0]
                    for row in connection.execute(
                        "SELECT id FROM jira_board_configs"
                    ).fetchall()
                ]
            _delete_board_family(connection, stale_board_ids)
            removed = len(stale_board_ids)

        for row in normalized_rows:
            connection.execute(
                """
                INSERT INTO jira_board_configs
                    (id, name, project_key, base_jql, version_name_pattern,
                     board_id, board_url, pm_project_id, active, notes, issues_use_base_jql)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    project_key = excluded.project_key,
                    base_jql = excluded.base_jql,
                    version_name_pattern = excluded.version_name_pattern,
                    board_id = excluded.board_id,
                    board_url = excluded.board_url,
                    pm_project_id = excluded.pm_project_id,
                    active = excluded.active,
                    notes = excluded.notes,
                    issues_use_base_jql = excluded.issues_use_base_jql,
                    updated_at = datetime('now')
                """,
                [
                    row["id"],
                    row["name"],
                    row["project_key"],
                    row["base_jql"],
                    row["version_name_pattern"],
                    row["board_id"],
                    row["board_url"],
                    row["pm_project_id"],
                    row["active"],
                    row["notes"],
                    row["issues_use_base_jql"],
                ],
            )
            connection.execute(
                """
                INSERT OR IGNORE INTO memory_facts (category, subject, fact, confidence, source)
                VALUES ('jira_project_key', ?, 'JIRA project key registered for sync', 1.0, 'csv-import')
                """,
                [row["project_key"]],
            )
            _upsert_data_source(
                connection,
                {
                    "id": f"jira-release-{row['id']}",
                    "source_type": "jira",
                    "source_name": f"JIRA Release Sync — {row['name']}",
                    "ingestion_mode": "api",
                    "refresh_sla_hours": 24,
                    "active": bool(row["active"]),
                    "config": _release_config(row),
                    "notes": "Per-board JIRA release/version sync.",
                },
            )
            _upsert_data_source(
                connection,
                {
                    "id": f"jira-health-{row['id']}",
                    "source_type": "jira",
                    "source_name": f"JIRA Health Sync — {row['name']}",
                    "ingestion_mode": "api",
                    "refresh_sla_hours": 24,
                    "active": bool(row["active"]),
                    "config": _health_config(row),
                    "notes": "Per-board JIRA sprint/health sync.",
                },
            )
            _upsert_data_source(
                connection,
                {
                    "id": f"jira-evidence-{row['id']}",
                    "source_type": "jira",
                    "source_name": f"JIRA Incremental Evidence — {row['name']}",
                    "ingestion_mode": "api",
                    "refresh_sla_hours": 24,
                    "active": bool(row["active"]),
                    "config": _merge_evidence_config(
                        connection,
                        f"jira-evidence-{row['id']}",
                        _evidence_config(row),
                    ),
                    "notes": (
                        "Phase 3 incremental Issue history and Issue Link evidence. "
                        "Connector-local field mappings require explicit local configuration."
                    ),
                },
            )
            imported += 1

        if not merge_only:
            _cleanup_project_key_facts(connection)
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
        "removed_rows": removed,
        "counts": counts,
        "payload": {
            "registry_fingerprint": _fingerprint(normalized_rows),
            "publication_id": _publication_id(normalized_rows),
            "board_ids": [row["id"] for row in normalized_rows],
            "project_keys": sorted({str(row["project_key"]) for row in normalized_rows}),
        },
        "report": {
            "coverage": {
                "state": "complete",
                "registry_rows": counts["registry_rows"],
                "active_boards": counts["active_boards"],
                "inactive_boards": counts["inactive_boards"],
                "project_keys": counts["project_keys"],
                "managed_data_sources": counts["managed_data_sources"],
            },
            "reconciliation_mode": "full_sync" if not merge_only else "merge_only",
            "result": {
                "imported_rows": imported,
                "removed_board_families": removed,
            },
            "preserved_semantics": {
                "carry_forward_evidence_local_config": True,
                "preserve_issue_event_history": True,
                "preserve_evidence_cursors": True,
            },
        },
    }


def export_registry_csv(
    output: str | Path,
    *,
    overwrite: bool = False,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    """Export editable board mapping facts in the exact registry CSV contract."""

    source_type = "jira-board-registry-csv"
    connection = sqlite3.connect(_db_path(db_path))
    try:
        rows = connection.execute(
            """
            SELECT id, name, project_key, base_jql, version_name_pattern,
                   board_id, board_url, pm_project_id, active,
                   issues_use_base_jql, notes
            FROM jira_board_configs
            ORDER BY id
            """
        ).fetchall()
    except sqlite3.OperationalError:
        return failed_export(source_type, "JIRA_BOARD_REGISTRY_EXPORT_SOURCE_UNAVAILABLE")
    finally:
        connection.close()

    try:
        expected_rows = [_exportable_registry_row(row) for row in rows]
    except ValueError:
        return failed_export(source_type, "JIRA_BOARD_REGISTRY_EXPORT_SOURCE_UNREPRESENTABLE")

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
        ):
            raise SourceExportError("JIRA_BOARD_REGISTRY_EXPORT_SOURCE_UNREPRESENTABLE")

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
    keys = (*REQUIRED_COLUMNS, *OPTIONAL_COLUMNS)
    source = dict(zip(keys, row, strict=True))
    for key in REQUIRED_COLUMNS:
        if not _canonical_required_text(source[key]):
            raise ValueError("unrepresentable required value")
    if source["project_key"] != source["project_key"].upper():
        raise ValueError("parser would normalize project key")
    for key in ("version_name_pattern", "board_id", "board_url", "pm_project_id", "notes"):
        if not _canonical_optional_text(source[key]):
            raise ValueError("parser would normalize optional value")
    for key in ("active", "issues_use_base_jql"):
        if not isinstance(source[key], int) or isinstance(source[key], bool) or source[key] not in {0, 1}:
            raise ValueError("noncanonical boolean")
    return source


def _canonical_required_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip()) and value == value.strip()


def _canonical_optional_text(value: object) -> bool:
    return value is None or (
        isinstance(value, str) and bool(value) and value == value.strip()
    )


def _registry_csv_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        key: "" if row[key] is None else row[key]
        for key in (*REQUIRED_COLUMNS, *OPTIONAL_COLUMNS)
    }


def _parse_rows(fieldnames: list[str], rows: list[dict[str, str]]) -> dict[str, Any]:
    missing_columns = sorted(column for column in REQUIRED_COLUMNS if column not in fieldnames)
    if missing_columns:
        return _rejected(
            code="JIRA_BOARD_REGISTRY_CSV_COLUMNS_INVALID",
            message=(
                "JIRA board registry CSV is missing required columns: "
                f"{', '.join(missing_columns)}."
            ),
            location="source_locator",
        )
    normalized_rows: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=2):
        board_key = (row.get("id") or "").strip()
        name = (row.get("name") or "").strip()
        project_key = (row.get("project_key") or "").strip().upper()
        base_jql = (row.get("base_jql") or "").strip()
        if not board_key or not name or not project_key or not base_jql:
            return _rejected(
                code="JIRA_BOARD_REGISTRY_ROW_INVALID",
                message=(
                    f"Row {index} must include id, name, project_key, and base_jql."
                ),
                location=f"row:{index}",
            )
        normalized_rows.append(
            {
                "id": board_key,
                "name": name,
                "project_key": project_key,
                "base_jql": base_jql,
                "version_name_pattern": _optional_text(row.get("version_name_pattern")),
                "board_id": _optional_text(row.get("board_id")),
                "board_url": _optional_text(row.get("board_url")),
                "pm_project_id": _optional_text(row.get("pm_project_id")),
                "active": _to_bool(row.get("active"), default=True),
                "issues_use_base_jql": _to_bool(
                    row.get("issues_use_base_jql"), default=False
                ),
                "notes": (row.get("notes") or "").strip(),
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


def _optional_text(value: str | None) -> str | None:
    text = (value or "").strip()
    return text or None


def _to_bool(value: str | None, *, default: bool = False) -> int:
    if value is None or value == "":
        return 1 if default else 0
    return 1 if value.strip().lower() in {"1", "true", "yes", "y"} else 0


def _counts(rows: list[dict[str, Any]]) -> dict[str, Any]:
    active_boards = sum(int(row["active"]) == 1 for row in rows)
    return {
        "registry_rows": len(rows),
        "active_boards": active_boards,
        "inactive_boards": len(rows) - active_boards,
        "project_keys": len({str(row["project_key"]) for row in rows}),
        "managed_data_sources": len(rows) * 3,
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
    return f"jira-board-registry:{_fingerprint(rows)}"


def _release_config(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "board_id": row["id"],
        "jira_board_id": row["board_id"] or "",
        "project_key": row["project_key"],
        "version_name_pattern": row["version_name_pattern"] or "",
        "board_url": row["board_url"] or "",
        "pm_project_id": row["pm_project_id"] or "",
        "issues_use_base_jql": bool(row["issues_use_base_jql"]),
    }


def _health_config(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "board_id": row["id"],
        "jira_board_id": row["board_id"] or "",
        "project_key": row["project_key"],
        "version_name_pattern": row["version_name_pattern"] or "",
        "board_url": row["board_url"] or "",
        "pm_project_id": row["pm_project_id"] or "",
    }


def _evidence_config(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "board_id": row["id"],
        "project_key": row["project_key"],
        "bootstrap_days": 90,
        "overlap_seconds": 300,
        "field_mappings": {},
    }


def _db_path(db_path: str | Path | None) -> Path:
    return Path(db_path or settings.database_path)


def _upsert_data_source(connection: sqlite3.Connection, payload: dict[str, Any]) -> None:
    connection.execute(
        """
        INSERT INTO data_sources
            (id, source_type, source_name, ingestion_mode, refresh_sla_hours,
             active, config_json, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            source_type = excluded.source_type,
            source_name = excluded.source_name,
            ingestion_mode = excluded.ingestion_mode,
            refresh_sla_hours = excluded.refresh_sla_hours,
            active = excluded.active,
            config_json = excluded.config_json,
            notes = excluded.notes,
            updated_at = datetime('now')
        """,
        [
            payload["id"],
            payload["source_type"],
            payload["source_name"],
            payload.get("ingestion_mode", "manual"),
            payload.get("refresh_sla_hours", 24),
            1 if payload.get("active", True) else 0,
            json.dumps(payload.get("config", {}), ensure_ascii=False),
            payload.get("notes", ""),
        ],
    )


def _merge_evidence_config(
    connection: sqlite3.Connection,
    source_id: str,
    registry_config: dict[str, Any],
) -> dict[str, Any]:
    row = connection.execute(
        "SELECT config_json FROM data_sources WHERE id = ?",
        [source_id],
    ).fetchone()
    if not row:
        return registry_config
    try:
        existing = json.loads(row[0] or "{}")
    except json.JSONDecodeError:
        existing = {}
    if not isinstance(existing, dict):
        existing = {}
    merged = dict(registry_config)
    for key in EVIDENCE_LOCAL_CONFIG_KEYS:
        if key in existing:
            merged[key] = existing[key]
    return merged


def _delete_board_family(connection: sqlite3.Connection, board_ids: list[str]) -> None:
    if not board_ids:
        return
    placeholders = ",".join("?" for _ in board_ids)
    connection.execute(
        f"DELETE FROM jira_health_snapshots WHERE board_id IN ({placeholders})",
        board_ids,
    )
    connection.execute(
        f"DELETE FROM jira_sprints WHERE board_id IN ({placeholders})",
        board_ids,
    )
    connection.execute(
        f"DELETE FROM jira_issues WHERE board_id IN ({placeholders})",
        board_ids,
    )
    connection.execute(
        f"DELETE FROM jira_stream_versions WHERE board_id IN ({placeholders})",
        board_ids,
    )
    connection.execute(
        f"DELETE FROM jira_board_configs WHERE id IN ({placeholders})",
        board_ids,
    )
    data_source_ids: list[str] = []
    for board_id in board_ids:
        data_source_ids.extend(
            [
                f"jira-release-{board_id}",
                f"jira-health-{board_id}",
                f"jira-evidence-{board_id}",
            ]
        )
    if data_source_ids:
        ds_placeholders = ",".join("?" for _ in data_source_ids)
        connection.execute(
            f"DELETE FROM data_sources WHERE id IN ({ds_placeholders})",
            data_source_ids,
        )


def _cleanup_project_key_facts(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        DELETE FROM memory_facts
        WHERE category = 'jira_project_key'
          AND source = 'csv-import'
          AND subject NOT IN (
              SELECT DISTINCT project_key
              FROM jira_board_configs
          )
        """
    )


def _matches_current_state(
    rows: list[dict[str, Any]],
    *,
    db_path: str | Path | None = None,
) -> bool:
    try:
        connection = sqlite3.connect(_db_path(db_path))
        desired_board_ids = {str(row["id"]) for row in rows}
        current_board_ids = {
            str(row[0])
            for row in connection.execute("SELECT id FROM jira_board_configs").fetchall()
        }
        if current_board_ids != desired_board_ids:
            return False

        for row in rows:
            board_row = connection.execute(
                """
                SELECT id, name, project_key, base_jql, version_name_pattern,
                       board_id, board_url, pm_project_id, active, notes, issues_use_base_jql
                FROM jira_board_configs
                WHERE id = ?
                """,
                [row["id"]],
            ).fetchone()
            if board_row is None or _board_state(board_row) != row:
                return False
            if not _data_source_matches(
                connection,
                source_id=f"jira-release-{row['id']}",
                expected_name=f"JIRA Release Sync — {row['name']}",
                expected_active=bool(row["active"]),
                expected_config=_release_config(row),
                expected_notes="Per-board JIRA release/version sync.",
            ):
                return False
            if not _data_source_matches(
                connection,
                source_id=f"jira-health-{row['id']}",
                expected_name=f"JIRA Health Sync — {row['name']}",
                expected_active=bool(row["active"]),
                expected_config=_health_config(row),
                expected_notes="Per-board JIRA sprint/health sync.",
            ):
                return False
            if not _data_source_matches(
                connection,
                source_id=f"jira-evidence-{row['id']}",
                expected_name=f"JIRA Incremental Evidence — {row['name']}",
                expected_active=bool(row["active"]),
                expected_config=_merge_evidence_config(
                    connection,
                    f"jira-evidence-{row['id']}",
                    _evidence_config(row),
                ),
                expected_notes=(
                    "Phase 3 incremental Issue history and Issue Link evidence. "
                    "Connector-local field mappings require explicit local configuration."
                ),
            ):
                return False

        existing_fact_keys = {
            str(row[0])
            for row in connection.execute(
                """
                SELECT subject
                FROM memory_facts
                WHERE category = 'jira_project_key' AND source = 'csv-import'
                """
            ).fetchall()
        }
        if existing_fact_keys != {str(row["project_key"]) for row in rows}:
            return False

        expected_data_source_ids = {
            f"jira-release-{row['id']}" for row in rows
        } | {f"jira-health-{row['id']}" for row in rows} | {
            f"jira-evidence-{row['id']}" for row in rows
        }
        actual_data_source_ids = {
            str(row[0])
            for row in connection.execute(
                """
                SELECT id
                FROM data_sources
                WHERE id LIKE 'jira-release-%'
                   OR id LIKE 'jira-health-%'
                   OR id LIKE 'jira-evidence-%'
                """
            ).fetchall()
        }
        if actual_data_source_ids != expected_data_source_ids:
            return False

        if _has_stale_board_cache_rows(connection, desired_board_ids):
            return False
        return True
    except sqlite3.OperationalError:
        return False
    finally:
        try:
            connection.close()
        except Exception:
            pass


def _board_state(row: sqlite3.Row | tuple[Any, ...]) -> dict[str, Any]:
    return {
        "id": row[0],
        "name": row[1],
        "project_key": row[2],
        "base_jql": row[3],
        "version_name_pattern": row[4],
        "board_id": row[5],
        "board_url": row[6],
        "pm_project_id": row[7],
        "active": int(row[8]),
        "notes": row[9] or "",
        "issues_use_base_jql": int(row[10]),
    }


def _data_source_matches(
    connection: sqlite3.Connection,
    *,
    source_id: str,
    expected_name: str,
    expected_active: bool,
    expected_config: dict[str, Any],
    expected_notes: str,
) -> bool:
    row = connection.execute(
        """
        SELECT source_type, source_name, ingestion_mode, refresh_sla_hours,
               active, config_json, notes
        FROM data_sources
        WHERE id = ?
        """,
        [source_id],
    ).fetchone()
    if row is None:
        return False
    try:
        config = json.loads(row[5] or "{}")
    except json.JSONDecodeError:
        return False
    return (
        str(row[0]) == "jira"
        and str(row[1]) == expected_name
        and str(row[2]) == "api"
        and int(row[3]) == 24
        and int(row[4]) == (1 if expected_active else 0)
        and config == expected_config
        and str(row[6] or "") == expected_notes
    )


def _has_stale_board_cache_rows(
    connection: sqlite3.Connection,
    desired_board_ids: set[str],
) -> bool:
    if desired_board_ids:
        placeholders = ",".join("?" for _ in desired_board_ids)
        conditions = f"board_id NOT IN ({placeholders})"
        params = list(desired_board_ids)
    else:
        conditions = "1=1"
        params = []
    for table in (
        "jira_stream_versions",
        "jira_issues",
        "jira_sprints",
        "jira_health_snapshots",
    ):
        row = connection.execute(
            f"SELECT 1 FROM {table} WHERE {conditions} LIMIT 1",
            params,
        ).fetchone()
        if row is not None:
            return True
    return False
