"""Transactional Phase 3 B1 source-evidence staging and publication."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator

from pm_agent.config import settings

DATASETS = {"jira_issue_history", "jira_issue_links"}
COVERAGE_STATES = {"complete", "partial", "failed", "unavailable"}
EVENT_TYPES = {"field_changed", "issue_observed", "tombstone"}
LINK_STATES = {"active", "tombstone", "unsupported"}
LINK_DIRECTIONS = {"outward", "inward"}
NORMALIZED_FIELD_KEYS = {
    "blocked",
    "fix_versions",
    "issue_observed",
    "sprint",
    "status",
    "status_category",
    "tombstone",
    "updated",
}


@dataclass(frozen=True)
class IssueEvent:
    issue_ref: str
    event_type: str
    field_key: str
    source_updated_at: str
    observed_at: str
    from_value: object = ""
    to_value: object = ""
    source_event_ref: str = ""


@dataclass(frozen=True)
class IssueLink:
    issue_ref: str
    related_issue_ref: str
    link_type: str
    direction: str
    observation_state: str
    source_updated_at: str
    observed_at: str
    source_link_ref: str = ""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def _connection(
    db_path: str | Path | None = None,
) -> Iterator[sqlite3.Connection]:
    path = Path(db_path or settings.database_path)
    connection = sqlite3.connect(path, timeout=10, isolation_level=None)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 10000")
    try:
        yield connection
    finally:
        connection.close()


def _bounded_text(value: object, *, name: str, maximum: int = 500) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string")
    normalized = value.strip()
    if not normalized or len(normalized) > maximum:
        raise ValueError(f"{name} must contain between 1 and {maximum} characters")
    return normalized


def _normalized_timestamp(value: object, *, name: str) -> str:
    raw = _bounded_text(value, name=name, maximum=80)
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{name} must be a valid ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    parsed = parsed.astimezone(timezone.utc)
    timespec = "microseconds" if parsed.microsecond else "seconds"
    return parsed.isoformat(timespec=timespec)


def _safe_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, (str, int, float, bool)):
        result = str(value)
    elif isinstance(value, list) and all(
        item is None or isinstance(item, (str, int, float, bool)) for item in value
    ):
        result = json.dumps(value, sort_keys=True, separators=(",", ":"))
    else:
        raise ValueError("Evidence values must be scalar or a flat scalar list")
    if len(result) > 500:
        raise ValueError("Evidence values must not exceed 500 characters")
    return result


def _semantic_hash(*parts: str) -> str:
    payload = json.dumps(parts, ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _safe_field_coverage(value: dict | None) -> dict[str, object]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError("field_coverage must be an object")
    result: dict[str, object] = {}
    for key, item in value.items():
        if not isinstance(key, str) or not key.strip() or len(key) > 100:
            raise ValueError("field_coverage keys must be bounded non-empty strings")
        if not isinstance(item, (bool, int, float, str)) or (
            isinstance(item, str) and len(item) > 100
        ):
            raise ValueError("field_coverage values must be bounded scalars")
        result[key.strip()] = item
    return result


def _event_record(event: IssueEvent) -> dict[str, str]:
    issue_ref = _bounded_text(event.issue_ref, name="issue_ref", maximum=200)
    event_type = _bounded_text(event.event_type, name="event_type", maximum=40)
    field_key = _bounded_text(event.field_key, name="field_key", maximum=80)
    source_updated_at = _normalized_timestamp(
        event.source_updated_at, name="source_updated_at"
    )
    observed_at = _normalized_timestamp(event.observed_at, name="observed_at")
    if not isinstance(event.source_event_ref, str):
        raise ValueError("source_event_ref must be a string")
    source_event_ref = event.source_event_ref.strip()
    if len(source_event_ref) > 200:
        raise ValueError("source_event_ref must not exceed 200 characters")
    if event_type not in EVENT_TYPES:
        raise ValueError(f"Unsupported issue event type: {event_type}")
    if field_key not in NORMALIZED_FIELD_KEYS:
        raise ValueError(f"Unsupported normalized field key: {field_key}")
    from_value = _safe_value(event.from_value)
    to_value = _safe_value(event.to_value)
    dedup_key = (
        _semantic_hash(issue_ref, source_event_ref)
        if source_event_ref
        else _semantic_hash(
            issue_ref,
            event_type,
            field_key,
            from_value,
            to_value,
            source_updated_at,
        )
    )
    return {
        "dedup_key": dedup_key,
        "issue_ref": issue_ref,
        "source_event_ref": source_event_ref,
        "event_type": event_type,
        "field_key": field_key,
        "from_value": from_value,
        "to_value": to_value,
        "source_updated_at": source_updated_at,
        "observed_at": observed_at,
    }


def _link_record(link: IssueLink) -> dict[str, str]:
    issue_ref = _bounded_text(link.issue_ref, name="issue_ref", maximum=200)
    related_issue_ref = _bounded_text(
        link.related_issue_ref, name="related_issue_ref", maximum=200
    )
    link_type = _bounded_text(link.link_type, name="link_type", maximum=120)
    direction = _bounded_text(link.direction, name="direction", maximum=20)
    state = _bounded_text(link.observation_state, name="observation_state", maximum=20)
    source_updated_at = _normalized_timestamp(
        link.source_updated_at, name="source_updated_at"
    )
    observed_at = _normalized_timestamp(link.observed_at, name="observed_at")
    source_link_ref = _bounded_text(
        link.source_link_ref,
        name="source_link_ref",
        maximum=200,
    )
    if direction not in LINK_DIRECTIONS:
        raise ValueError(f"Unsupported link direction: {direction}")
    if state not in LINK_STATES:
        raise ValueError(f"Unsupported link observation state: {state}")
    dedup_key = _semantic_hash(
        source_link_ref,
        issue_ref,
        related_issue_ref,
        link_type,
        direction,
        state,
    )
    return {
        "dedup_key": dedup_key,
        "source_link_ref": source_link_ref,
        "issue_ref": issue_ref,
        "related_issue_ref": related_issue_ref,
        "link_type": link_type,
        "direction": direction,
        "observation_state": state,
        "source_updated_at": source_updated_at,
        "observed_at": observed_at,
    }


def get_cursor(
    source_id: str,
    board_id: str,
    dataset: str,
    *,
    db_path: str | Path | None = None,
) -> dict | None:
    if dataset not in DATASETS:
        raise ValueError(f"Unsupported evidence dataset: {dataset}")
    with _connection(db_path) as connection:
        row = connection.execute(
            """
            SELECT *
            FROM source_evidence_cursors
            WHERE source_id = ? AND board_id = ? AND dataset = ?
            """,
            [source_id, board_id, dataset],
        ).fetchone()
    return dict(row) if row else None


def start_run(
    source_id: str,
    board_id: str,
    dataset: str,
    *,
    overlap_seconds: int,
    db_path: str | Path | None = None,
    run_id: str | None = None,
) -> str:
    source_id = _bounded_text(source_id, name="source_id", maximum=200)
    board_id = _bounded_text(board_id, name="board_id", maximum=200)
    if dataset not in DATASETS:
        raise ValueError(f"Unsupported evidence dataset: {dataset}")
    if not isinstance(overlap_seconds, int) or not 0 <= overlap_seconds <= 86400:
        raise ValueError("overlap_seconds must be an integer between 0 and 86400")
    run_id = _bounded_text(
        run_id or f"evidence-{uuid.uuid4().hex}",
        name="run_id",
        maximum=200,
    )
    with _connection(db_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        cursor = connection.execute(
            """
            SELECT cursor_time, cursor_ref, published_run_id
            FROM source_evidence_cursors
            WHERE source_id = ? AND board_id = ? AND dataset = ?
            """,
            [source_id, board_id, dataset],
        ).fetchone()
        connection.execute(
            """
            INSERT INTO source_evidence_runs
                (run_id, source_id, board_id, dataset, prior_published_run_id,
                 requested_cursor_time, requested_cursor_ref, overlap_seconds, started_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                run_id,
                source_id,
                board_id,
                dataset,
                cursor["published_run_id"] if cursor else "",
                cursor["cursor_time"] if cursor else "",
                cursor["cursor_ref"] if cursor else "",
                overlap_seconds,
                _now(),
            ],
        )
        connection.commit()
    return run_id


def stage_issue_events(
    run_id: str,
    events: Iterable[IssueEvent],
    *,
    manifest_issue_refs: Iterable[str] = (),
    db_path: str | Path | None = None,
) -> tuple[int, int]:
    records = [_event_record(event) for event in events]
    manifest = {
        _bounded_text(item, name="manifest_issue_ref", maximum=200)
        for item in manifest_issue_refs
    }
    with _connection(db_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        run = _require_staged_run(connection, run_id, "jira_issue_history")
        accepted = 0
        duplicated = 0
        seen_keys: set[str] = set()
        for record in records:
            dedup_key = record["dedup_key"]
            if dedup_key in seen_keys or connection.execute(
                """
                SELECT 1 FROM jira_issue_event_stage
                WHERE run_id = ? AND dedup_key = ?
                """,
                [run_id, dedup_key],
            ).fetchone():
                duplicated += 1
                continue
            seen_keys.add(dedup_key)
            connection.execute(
                """
                INSERT INTO jira_issue_event_stage
                    (run_id, dedup_key, issue_ref, source_event_ref, event_type,
                     field_key, from_value, to_value, source_updated_at, observed_at)
                VALUES
                    (:run_id, :dedup_key, :issue_ref, :source_event_ref, :event_type,
                     :field_key, :from_value, :to_value, :source_updated_at, :observed_at)
                """,
                {"run_id": run["run_id"], **record},
            )
            if connection.execute(
                """
                SELECT 1 FROM jira_issue_events
                WHERE source_id = ? AND board_id = ? AND dedup_key = ?
                """,
                [run["source_id"], run["board_id"], dedup_key],
            ).fetchone():
                duplicated += 1
            else:
                accepted += 1
        for item_ref in manifest:
            connection.execute(
                """
                INSERT OR IGNORE INTO source_evidence_manifest_stage(run_id, item_ref)
                VALUES (?, ?)
                """,
                [run_id, item_ref],
            )
        connection.execute(
            """
            UPDATE source_evidence_runs
            SET rows_read = rows_read + ?,
                rows_accepted = rows_accepted + ?,
                rows_deduplicated = rows_deduplicated + ?
            WHERE run_id = ?
            """,
            [len(records), accepted, duplicated, run_id],
        )
        connection.commit()
    return accepted, duplicated


def stage_issue_links(
    run_id: str,
    links: Iterable[IssueLink],
    *,
    manifest_link_refs: Iterable[str] = (),
    db_path: str | Path | None = None,
) -> tuple[int, int]:
    records = [_link_record(link) for link in links]
    manifest = {
        _bounded_text(item, name="manifest_link_ref", maximum=200)
        for item in manifest_link_refs
    }
    with _connection(db_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        run = _require_staged_run(connection, run_id, "jira_issue_links")
        accepted = 0
        duplicated = 0
        seen_keys: set[str] = set()
        for record in records:
            dedup_key = record["dedup_key"]
            if dedup_key in seen_keys or connection.execute(
                """
                SELECT 1 FROM jira_issue_link_stage
                WHERE run_id = ? AND dedup_key = ?
                """,
                [run_id, dedup_key],
            ).fetchone():
                duplicated += 1
                continue
            seen_keys.add(dedup_key)
            connection.execute(
                """
                INSERT INTO jira_issue_link_stage
                    (run_id, dedup_key, source_link_ref, issue_ref, related_issue_ref,
                     link_type, direction, observation_state, source_updated_at, observed_at)
                VALUES
                    (:run_id, :dedup_key, :source_link_ref, :issue_ref, :related_issue_ref,
                     :link_type, :direction, :observation_state,
                     :source_updated_at, :observed_at)
                """,
                {"run_id": run["run_id"], **record},
            )
            if connection.execute(
                """
                SELECT 1 FROM jira_issue_links
                WHERE source_id = ? AND board_id = ? AND dedup_key = ?
                """,
                [run["source_id"], run["board_id"], dedup_key],
            ).fetchone():
                duplicated += 1
            else:
                accepted += 1
        for item_ref in manifest:
            connection.execute(
                """
                INSERT OR IGNORE INTO source_evidence_manifest_stage(run_id, item_ref)
                VALUES (?, ?)
                """,
                [run_id, item_ref],
            )
        connection.execute(
            """
            UPDATE source_evidence_runs
            SET rows_read = rows_read + ?,
                rows_accepted = rows_accepted + ?,
                rows_deduplicated = rows_deduplicated + ?
            WHERE run_id = ?
            """,
            [len(records), accepted, duplicated, run_id],
        )
        connection.commit()
    return accepted, duplicated


def finish_staging(
    run_id: str,
    *,
    coverage_status: str,
    pages_received: int,
    pages_expected: int | None,
    proposed_cursor_time: str = "",
    proposed_cursor_ref: str = "",
    authoritative_manifest: bool = False,
    field_coverage: dict | None = None,
    warning_codes: list[str] | None = None,
    error_code: str = "",
    rows_rejected: int = 0,
    db_path: str | Path | None = None,
) -> None:
    if coverage_status not in COVERAGE_STATES:
        raise ValueError(f"Unsupported coverage status: {coverage_status}")
    if (
        not isinstance(pages_received, int)
        or isinstance(pages_received, bool)
        or pages_received < 0
        or pages_expected is not None
        and (
            not isinstance(pages_expected, int)
            or isinstance(pages_expected, bool)
            or pages_expected < 0
        )
    ):
        raise ValueError("Page counts must not be negative")
    warnings = list(warning_codes or [])
    if not all(isinstance(code, str) and 0 < len(code) <= 100 for code in warnings):
        raise ValueError("warning_codes must contain bounded non-empty strings")
    if pages_expected is not None and pages_received != pages_expected:
        coverage_status = "partial"
        if "PAGE_COUNT_MISMATCH" not in warnings:
            warnings.append("PAGE_COUNT_MISMATCH")
    if not isinstance(proposed_cursor_time, str) or not isinstance(proposed_cursor_ref, str):
        raise ValueError("Proposed cursor values must be strings")
    proposed_cursor_time = proposed_cursor_time.strip()
    proposed_cursor_ref = proposed_cursor_ref.strip()
    if proposed_cursor_time:
        proposed_cursor_time = _normalized_timestamp(
            proposed_cursor_time,
            name="proposed_cursor_time",
        )
    if coverage_status == "complete" and (
        not proposed_cursor_time or not proposed_cursor_ref
    ):
        raise ValueError("Complete coverage requires a compound proposed cursor")
    with _connection(db_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        _require_staged_run(connection, run_id)
        connection.execute(
            """
            UPDATE source_evidence_runs
            SET coverage_status = ?,
                proposed_cursor_time = ?,
                proposed_cursor_ref = ?,
                authoritative_manifest = ?,
                pages_expected = ?,
                pages_received = ?,
                rows_rejected = rows_rejected + ?,
                field_coverage_json = ?,
                warning_codes_json = ?,
                error_code = ?,
                finished_at = ?
            WHERE run_id = ?
            """,
            [
                coverage_status,
                proposed_cursor_time,
                proposed_cursor_ref,
                1 if authoritative_manifest else 0,
                pages_expected,
                pages_received,
                rows_rejected,
                json.dumps(
                    _safe_field_coverage(field_coverage),
                    sort_keys=True,
                    separators=(",", ":"),
                ),
                json.dumps(warnings, sort_keys=True, separators=(",", ":")),
                error_code[:100],
                _now(),
                run_id,
            ],
        )
        connection.commit()


def publish_run(run_id: str, *, db_path: str | Path | None = None) -> int:
    with _connection(db_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        run = _require_staged_run(connection, run_id)
        if run["coverage_status"] != "complete":
            raise ValueError("Only a complete evidence run can be published")
        if run["pages_expected"] is not None and run["pages_expected"] != run["pages_received"]:
            raise ValueError("Incomplete pagination cannot be published")
        if not run["proposed_cursor_time"] or not run["proposed_cursor_ref"]:
            raise ValueError("A complete compound cursor is required for publication")
        current_cursor = connection.execute(
            """
            SELECT cursor_time, cursor_ref, published_run_id
            FROM source_evidence_cursors
            WHERE source_id = ? AND board_id = ? AND dataset = ?
            """,
            [run["source_id"], run["board_id"], run["dataset"]],
        ).fetchone()
        current_run_id = current_cursor["published_run_id"] if current_cursor else ""
        if current_run_id != run["prior_published_run_id"]:
            _reject_stale_run(connection, run_id, "STALE_PUBLISHED_RUN")
            connection.commit()
            raise ValueError("The evidence run is stale relative to the published cursor")
        if current_cursor and _cursor_key(
            run["proposed_cursor_time"],
            run["proposed_cursor_ref"],
        ) < _cursor_key(current_cursor["cursor_time"], current_cursor["cursor_ref"]):
            _reject_stale_run(connection, run_id, "CURSOR_REGRESSION")
            connection.commit()
            raise ValueError("The proposed evidence cursor would move backwards")

        if run["dataset"] == "jira_issue_history":
            published = _publish_issue_events(connection, run)
        else:
            published = _publish_issue_links(connection, run)
        if run["authoritative_manifest"]:
            _publish_manifest(connection, run)

        timestamp = _now()
        connection.execute(
            """
            INSERT INTO source_evidence_cursors
                (source_id, board_id, dataset, cursor_time, cursor_ref,
                 published_run_id, overlap_seconds, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source_id, board_id, dataset) DO UPDATE SET
                cursor_time = excluded.cursor_time,
                cursor_ref = excluded.cursor_ref,
                published_run_id = excluded.published_run_id,
                overlap_seconds = excluded.overlap_seconds,
                updated_at = excluded.updated_at
            """,
            [
                run["source_id"],
                run["board_id"],
                run["dataset"],
                run["proposed_cursor_time"],
                run["proposed_cursor_ref"],
                run_id,
                run["overlap_seconds"],
                timestamp,
            ],
        )
        connection.execute(
            """
            UPDATE source_evidence_runs
            SET publication_status = 'published',
                rows_published = ?,
                published_at = ?
            WHERE run_id = ?
            """,
            [published, timestamp, run_id],
        )
        connection.commit()
        board_id = run["board_id"]
    # C2 derived processing is deliberately after durable publication.
    from pm_agent.attention.phase3 import reconcile_after_evidence_publication

    try:
        reconcile_after_evidence_publication(board_id, db_path=db_path)
    except Exception:
        # Publication is already durable; C2 failure must not revoke its cursor.
        _record_post_publication_warning(run_id, db_path=db_path)
    return published


def _record_post_publication_warning(
    run_id: str,
    *,
    db_path: str | Path | None = None,
) -> None:
    """Leave durable, non-sensitive evidence that automatic C2 processing failed."""
    with _connection(db_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            "SELECT warning_codes_json FROM source_evidence_runs WHERE run_id = ?",
            [run_id],
        ).fetchone()
        if row is None:
            connection.rollback()
            return
        warnings = json.loads(row["warning_codes_json"])
        if "PHASE3_RECONCILIATION_FAILED" not in warnings:
            warnings.append("PHASE3_RECONCILIATION_FAILED")
            connection.execute(
                "UPDATE source_evidence_runs SET warning_codes_json = ? WHERE run_id = ?",
                [json.dumps(sorted(warnings), separators=(",", ":")), run_id],
            )
        connection.commit()


def reject_run(run_id: str, *, db_path: str | Path | None = None) -> None:
    with _connection(db_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        _require_staged_run(connection, run_id)
        connection.execute(
            """
            UPDATE source_evidence_runs
            SET publication_status = 'rejected',
                finished_at = CASE WHEN finished_at = '' THEN ? ELSE finished_at END
            WHERE run_id = ?
            """,
            [_now(), run_id],
        )
        connection.commit()


def fail_run(
    run_id: str,
    *,
    error_code: str,
    db_path: str | Path | None = None,
) -> None:
    with _connection(db_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            "SELECT publication_status FROM source_evidence_runs WHERE run_id = ?",
            [run_id],
        ).fetchone()
        if not row:
            raise ValueError(f"Unknown source evidence run: {run_id}")
        if row["publication_status"] == "staged":
            connection.execute(
                """
                UPDATE source_evidence_runs
                SET coverage_status = 'failed',
                    publication_status = 'rejected',
                    error_code = ?,
                    finished_at = ?
                WHERE run_id = ?
                """,
                [error_code[:100], _now(), run_id],
            )
        connection.commit()


def _cursor_key(cursor_time: str, cursor_ref: str) -> tuple[datetime, str]:
    return (
        datetime.fromisoformat(cursor_time.replace("Z", "+00:00")).astimezone(timezone.utc),
        cursor_ref,
    )


def _reject_stale_run(
    connection: sqlite3.Connection,
    run_id: str,
    error_code: str,
) -> None:
    connection.execute(
        """
        UPDATE source_evidence_runs
        SET publication_status = 'rejected',
            error_code = ?,
            finished_at = CASE WHEN finished_at = '' THEN ? ELSE finished_at END
        WHERE run_id = ?
        """,
        [error_code, _now(), run_id],
    )


def _require_staged_run(
    connection: sqlite3.Connection,
    run_id: str,
    dataset: str | None = None,
) -> sqlite3.Row:
    row = connection.execute(
        "SELECT * FROM source_evidence_runs WHERE run_id = ?",
        [run_id],
    ).fetchone()
    if not row:
        raise ValueError(f"Unknown source evidence run: {run_id}")
    if row["publication_status"] != "staged":
        raise ValueError("The source evidence run is no longer staged")
    if dataset and row["dataset"] != dataset:
        raise ValueError(f"Run dataset is {row['dataset']}, not {dataset}")
    return row


def _publish_issue_events(connection: sqlite3.Connection, run: sqlite3.Row) -> int:
    staged = connection.execute(
        "SELECT * FROM jira_issue_event_stage WHERE run_id = ? ORDER BY dedup_key",
        [run["run_id"]],
    ).fetchall()
    published = 0
    for row in staged:
        cursor = connection.execute(
            """
            INSERT OR IGNORE INTO jira_issue_events
                (source_id, board_id, dedup_key, issue_ref, source_event_ref,
                 event_type, field_key, from_value, to_value, source_updated_at,
                 observed_at, first_published_run_id, last_published_run_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                run["source_id"],
                run["board_id"],
                row["dedup_key"],
                row["issue_ref"],
                row["source_event_ref"],
                row["event_type"],
                row["field_key"],
                row["from_value"],
                row["to_value"],
                row["source_updated_at"],
                row["observed_at"],
                run["run_id"],
                run["run_id"],
            ],
        )
        published += cursor.rowcount
        if cursor.rowcount == 0:
            connection.execute(
                """
                UPDATE jira_issue_events
                SET last_published_run_id = ?
                WHERE source_id = ? AND board_id = ? AND dedup_key = ?
                """,
                [run["run_id"], run["source_id"], run["board_id"], row["dedup_key"]],
            )
    return published


def _publish_issue_links(connection: sqlite3.Connection, run: sqlite3.Row) -> int:
    staged = connection.execute(
        "SELECT * FROM jira_issue_link_stage WHERE run_id = ? ORDER BY dedup_key",
        [run["run_id"]],
    ).fetchall()
    published = 0
    for row in staged:
        cursor = connection.execute(
            """
            INSERT OR IGNORE INTO jira_issue_links
                (source_id, board_id, dedup_key, source_link_ref, issue_ref,
                 related_issue_ref, link_type, direction, observation_state,
                 source_updated_at, observed_at, first_published_run_id,
                 last_published_run_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                run["source_id"],
                run["board_id"],
                row["dedup_key"],
                row["source_link_ref"],
                row["issue_ref"],
                row["related_issue_ref"],
                row["link_type"],
                row["direction"],
                row["observation_state"],
                row["source_updated_at"],
                row["observed_at"],
                run["run_id"],
                run["run_id"],
            ],
        )
        published += cursor.rowcount
        if cursor.rowcount == 0:
            connection.execute(
                """
                UPDATE jira_issue_links
                SET last_published_run_id = ?
                WHERE source_id = ? AND board_id = ? AND dedup_key = ?
                """,
                [run["run_id"], run["source_id"], run["board_id"], row["dedup_key"]],
            )
    return published


def _publish_manifest(connection: sqlite3.Connection, run: sqlite3.Row) -> None:
    scope = [run["source_id"], run["board_id"], run["dataset"]]
    staged_refs = {
        row["item_ref"]
        for row in connection.execute(
            "SELECT item_ref FROM source_evidence_manifest_stage WHERE run_id = ?",
            [run["run_id"]],
        ).fetchall()
    }
    current_refs = {
        row["item_ref"]
        for row in connection.execute(
            """
            SELECT item_ref
            FROM source_evidence_published_items
            WHERE source_id = ? AND board_id = ? AND dataset = ? AND is_current = 1
            """,
            scope,
        ).fetchall()
    }
    removed = current_refs - staged_refs
    for item_ref in staged_refs:
        connection.execute(
            """
            INSERT INTO source_evidence_published_items
                (source_id, board_id, dataset, item_ref, is_current,
                 first_published_run_id, last_published_run_id, removed_run_id)
            VALUES (?, ?, ?, ?, 1, ?, ?, '')
            ON CONFLICT(source_id, board_id, dataset, item_ref) DO UPDATE SET
                is_current = 1,
                last_published_run_id = excluded.last_published_run_id,
                removed_run_id = ''
            """,
            [*scope, item_ref, run["run_id"], run["run_id"]],
        )
    for item_ref in removed:
        connection.execute(
            """
            UPDATE source_evidence_published_items
            SET is_current = 0, last_published_run_id = ?, removed_run_id = ?
            WHERE source_id = ? AND board_id = ? AND dataset = ? AND item_ref = ?
            """,
            [run["run_id"], run["run_id"], *scope, item_ref],
        )
        if run["dataset"] == "jira_issue_history":
            dedup_key = _semantic_hash(
                item_ref, "tombstone", run["proposed_cursor_time"], run["proposed_cursor_ref"]
            )
            connection.execute(
                """
                INSERT OR IGNORE INTO jira_issue_events
                    (source_id, board_id, dedup_key, issue_ref, event_type, field_key,
                     source_updated_at, observed_at, first_published_run_id,
                     last_published_run_id)
                VALUES (?, ?, ?, ?, 'tombstone', 'tombstone', ?, ?, ?, ?)
                """,
                [
                    run["source_id"],
                    run["board_id"],
                    dedup_key,
                    item_ref,
                    run["proposed_cursor_time"],
                    _now(),
                    run["run_id"],
                    run["run_id"],
                ],
            )
        else:
            previous = connection.execute(
                """
                SELECT *
                FROM jira_issue_links
                WHERE source_id = ? AND board_id = ? AND source_link_ref = ?
                  AND observation_state = 'active'
                ORDER BY source_updated_at DESC, dedup_key DESC
                LIMIT 1
                """,
                [run["source_id"], run["board_id"], item_ref],
            ).fetchone()
            if previous:
                dedup_key = _semantic_hash(
                    item_ref, "tombstone", run["proposed_cursor_time"], run["proposed_cursor_ref"]
                )
                connection.execute(
                    """
                    INSERT OR IGNORE INTO jira_issue_links
                        (source_id, board_id, dedup_key, source_link_ref, issue_ref,
                         related_issue_ref, link_type, direction, observation_state,
                         source_updated_at, observed_at, first_published_run_id,
                         last_published_run_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'tombstone', ?, ?, ?, ?)
                    """,
                    [
                        run["source_id"],
                        run["board_id"],
                        dedup_key,
                        item_ref,
                        previous["issue_ref"],
                        previous["related_issue_ref"],
                        previous["link_type"],
                        previous["direction"],
                        run["proposed_cursor_time"],
                        _now(),
                        run["run_id"],
                        run["run_id"],
                    ],
                )
