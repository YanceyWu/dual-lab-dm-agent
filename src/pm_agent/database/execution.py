"""Deterministic Phase 3 B2 canonical execution storage and derivation."""

from __future__ import annotations

import hashlib
import json
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator
from uuid import uuid4

from pm_agent.config import settings


RULE_VERSION = "execution-foundation-v1"
VALUE_STATES = {"known", "unknown", "unavailable", "conflicting"}
FRESHNESS_STATES = {"fresh", "stale", "partial", "failed", "never_observed"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _stable_id(prefix: str, *parts: str) -> str:
    payload = json.dumps(parts, ensure_ascii=True, separators=(",", ":"))
    return f"{prefix}-{hashlib.sha256(payload.encode()).hexdigest()[:24]}"


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


@contextmanager
def _connection(db_path: str | Path | None = None) -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(Path(db_path or settings.database_path), isolation_level=None)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 10000")
    try:
        yield connection
    finally:
        connection.close()


def _parse_list(value: str) -> list[str]:
    try:
        parsed = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return []
    return [item for item in parsed if isinstance(item, str) and item]


def _latest_run(connection: sqlite3.Connection, board_id: str, dataset: str) -> sqlite3.Row | None:
    return connection.execute(
        """
        SELECT * FROM source_evidence_runs
        WHERE board_id = ? AND dataset = ? AND publication_status = 'published'
        ORDER BY published_at DESC, run_id DESC LIMIT 1
        """,
        [board_id, dataset],
    ).fetchone()


def _board_project(connection: sqlite3.Connection, board_id: str) -> str:
    row = connection.execute(
        "SELECT pm_project_id FROM jira_board_configs WHERE id = ?", [board_id]
    ).fetchone()
    if not row or not row["pm_project_id"]:
        raise ValueError("Board must reference an existing stable project")
    project = connection.execute("SELECT 1 FROM projects WHERE id = ?", [row["pm_project_id"]]).fetchone()
    if not project:
        raise ValueError("Board project no longer exists")
    return str(row["pm_project_id"])


def _fact(
    connection: sqlite3.Connection,
    *,
    run_id: str,
    project_id: str,
    subject_kind: str,
    subject_id: str,
    fact_key: str,
    value: Any,
    value_state: str,
    freshness_state: str,
    evidence: dict[str, Any],
) -> None:
    connection.execute(
        """
        INSERT INTO execution_facts
            (fact_id, derivation_run_id, project_id, subject_kind, subject_id,
             fact_key, value_json, value_state, freshness_state, evidence_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            _stable_id("fact", run_id, subject_kind, subject_id, fact_key), run_id,
            project_id, subject_kind, subject_id, fact_key, _json(value), value_state,
            freshness_state, _json(evidence),
        ],
    )


def _upsert_work_item(
    connection: sqlite3.Connection,
    *,
    project_id: str,
    board_id: str,
    source_id: str,
    source_ref: str,
    fields: dict[str, str],
    observed_at: str,
    run_id: str,
    freshness: str,
) -> str:
    work_item_id = _stable_id("work", source_id, board_id, source_ref)
    story_points = fields.get("story_points")
    connection.execute(
        """
        INSERT INTO execution_work_items
            (work_item_id, project_id, board_id, source_id, source_ref, status_ref,
             status_category, sprint_source_ref, story_points, value_state,
             freshness_state, latest_evidence_run_id, observed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(source_id, board_id, source_ref) DO UPDATE SET
            status_ref=excluded.status_ref, status_category=excluded.status_category,
            sprint_source_ref=excluded.sprint_source_ref, story_points=excluded.story_points,
            value_state=excluded.value_state, freshness_state=excluded.freshness_state,
            latest_evidence_run_id=excluded.latest_evidence_run_id, observed_at=excluded.observed_at
        """,
        [
            work_item_id, project_id, board_id, source_id, source_ref,
            fields.get("status", ""), fields.get("status_category", ""),
            fields.get("sprint", ""), float(story_points) if story_points not in (None, "") else None,
            "known" if fields else "unknown", freshness, run_id, observed_at,
        ],
    )
    connection.execute(
        """
        INSERT INTO execution_source_identities
            (identity_id, subject_kind, subject_id, source_id, board_id, source_ref,
             first_observed_at, last_observed_at)
        VALUES (?, 'work_item', ?, ?, ?, ?, ?, ?)
        ON CONFLICT(subject_kind, source_id, board_id, source_ref) DO UPDATE SET
            subject_id=excluded.subject_id, last_observed_at=excluded.last_observed_at,
            active=1
        """,
        [
            _stable_id("source-identity", "work_item", source_id, board_id, source_ref),
            work_item_id, source_id, board_id, source_ref, observed_at, observed_at,
        ],
    )
    return work_item_id


def derive_board(board_id: str, *, db_path: str | Path | None = None) -> dict[str, Any]:
    """Canonicalize published evidence for one board without automatic triggering."""
    with _connection(db_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        project_id = _board_project(connection, board_id)
        history_run = _latest_run(connection, board_id, "jira_issue_history")
        links_run = _latest_run(connection, board_id, "jira_issue_links")
        inputs = [item["run_id"] for item in (history_run, links_run) if item]
        milestone_operations = [
            row[0] for row in connection.execute(
                """
                SELECT DISTINCT latest_operation_id FROM execution_milestones
                WHERE project_id = ? AND latest_operation_id != ''
                ORDER BY latest_operation_id
                """,
                [project_id],
            )
        ]
        fingerprint = hashlib.sha256(
            _json([board_id, RULE_VERSION, inputs, milestone_operations]).encode()
        ).hexdigest()
        existing = connection.execute(
            "SELECT * FROM execution_derivation_runs WHERE input_fingerprint = ?", [fingerprint]
        ).fetchone()
        if existing:
            fact_count = connection.execute(
                "SELECT COUNT(*) FROM execution_facts WHERE derivation_run_id = ?",
                [existing["derivation_run_id"]],
            ).fetchone()[0]
            connection.commit()
            return {
                "status": "derived", "derivation_run_id": existing["derivation_run_id"],
                "idempotent": True, "fact_count": fact_count,
            }

        complete = bool(history_run and history_run["coverage_status"] == "complete")
        authoritative = bool(complete and history_run["authoritative_manifest"])
        freshness = "fresh" if complete else "partial"
        warnings = [] if authoritative else ["SCOPE_MANIFEST_NOT_AUTHORITATIVE"]
        derivation_run_id = f"derivation-{uuid4().hex}"
        connection.execute(
            """
            INSERT INTO execution_derivation_runs
                (derivation_run_id, project_id, board_id, rule_version, input_fingerprint,
                 completeness_state, freshness_state, warning_codes_json, started_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [derivation_run_id, project_id, board_id, RULE_VERSION, fingerprint,
             "complete" if authoritative else "partial", freshness, _json(warnings), _now()],
        )
        for source_run_id in inputs:
            connection.execute(
                "INSERT INTO execution_derivation_inputs VALUES (?, 'source_evidence_run', ?)",
                [derivation_run_id, source_run_id],
            )
        for operation_id in milestone_operations:
            connection.execute(
                "INSERT INTO execution_derivation_inputs VALUES (?, 'milestone_operation', ?)",
                [derivation_run_id, operation_id],
            )

        source_id = history_run["source_id"] if history_run else f"jira-evidence-{board_id}"
        latest_fields: dict[str, dict[str, str]] = {}
        for row in connection.execute(
            """
            SELECT * FROM jira_issue_events WHERE board_id = ? AND event_type = 'issue_observed'
            ORDER BY source_updated_at, observed_at, dedup_key
            """,
            [board_id],
        ):
            latest_fields.setdefault(row["issue_ref"], {})[row["field_key"]] = row["to_value"]
        for issue in connection.execute(
            "SELECT * FROM jira_issues WHERE board_id = ?", [board_id]
        ):
            fields = latest_fields.setdefault(issue["id"], {})
            fields.setdefault("status", issue["status"] or "")
            fields.setdefault("status_category", issue["status_category"] or "")
            if issue["story_points"] is not None:
                fields.setdefault("story_points", str(issue["story_points"]))
            if issue["version_id"]:
                fields.setdefault("fix_versions", _json([issue["version_id"]]))

        work_items: dict[str, str] = {}
        observed_at = _now()
        for source_ref, fields in latest_fields.items():
            work_items[source_ref] = _upsert_work_item(
                connection, project_id=project_id, board_id=board_id, source_id=source_id,
                source_ref=source_ref, fields=fields, observed_at=observed_at,
                run_id=history_run["run_id"] if history_run else "", freshness=freshness,
            )
        for event in connection.execute(
            """
            SELECT * FROM jira_issue_events WHERE board_id = ?
              AND event_type IN ('field_changed', 'issue_observed')
            """,
            [board_id],
        ):
            work_item_id = work_items.get(event["issue_ref"])
            if not work_item_id:
                continue
            connection.execute(
                """
                INSERT OR IGNORE INTO execution_work_item_observations
                    (observation_id, work_item_id, field_key, from_value, to_value,
                     source_event_ref, source_updated_at, observed_at, source_run_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    _stable_id("work-observation", work_item_id, event["dedup_key"]),
                    work_item_id, event["field_key"], event["from_value"], event["to_value"],
                    event["source_event_ref"], event["source_updated_at"], event["observed_at"],
                    event["last_published_run_id"],
                ],
            )

        release_ids: dict[str, str] = {}
        for row in connection.execute("SELECT * FROM jira_stream_versions WHERE board_id = ?", [board_id]):
            release_id = _stable_id("release", board_id, row["id"])
            release_ids[row["id"]] = release_id
            target = row["release_date"] or ""
            connection.execute(
                """
                INSERT INTO execution_release_commitments
                    (release_id, project_id, board_id, source_ref, lifecycle_state,
                     source_target_date, actual_date, first_observed_target_date,
                     target_authority, observed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'unknown', ?)
                ON CONFLICT(board_id, source_ref) DO UPDATE SET
                    lifecycle_state=excluded.lifecycle_state, source_target_date=excluded.source_target_date,
                    actual_date=excluded.actual_date, observed_at=excluded.observed_at
                """,
                [release_id, project_id, board_id, row["id"], row["status"] or "unknown", target,
                 target if row["released"] else "", target, observed_at],
            )
            connection.execute(
                """
                INSERT OR IGNORE INTO execution_release_observations
                    (observation_id, release_id, source_target_date, actual_date,
                     lifecycle_state, target_authority, observed_at, source_input_id)
                VALUES (?, ?, ?, ?, ?, 'unknown', ?, ?)
                """,
                [
                    _stable_id("release-observation", release_id, target, row["status"] or "unknown", observed_at),
                    release_id, target, target if row["released"] else "", row["status"] or "unknown",
                    observed_at, history_run["run_id"] if history_run else "",
                ],
            )

        for row in connection.execute("SELECT * FROM jira_sprints WHERE board_id = ?", [board_id]):
            sprint_id = _stable_id("sprint", board_id, row["id"])
            connection.execute(
                """
                INSERT INTO execution_sprints
                    (sprint_id, project_id, board_id, source_ref, lifecycle_state, start_date, end_date, observed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(board_id, source_ref) DO UPDATE SET
                    lifecycle_state=excluded.lifecycle_state, start_date=excluded.start_date,
                    end_date=excluded.end_date, observed_at=excluded.observed_at
                """,
                [sprint_id, project_id, board_id, row["id"], row["state"] or "unknown",
                 row["start_date"] or "", row["end_date"] or "", observed_at],
            )

        for source_ref, work_item_id in work_items.items():
            fields = latest_fields[source_ref]
            for version_ref in _parse_list(fields.get("fix_versions", "[]")):
                release_id = release_ids.get(version_ref)
                if release_id:
                    connection.execute(
                        """
                        INSERT OR IGNORE INTO execution_scope_memberships
                            (membership_id, work_item_id, scope_kind, scope_id, valid_from,
                             boundary_basis, evidence_run_id)
                        VALUES (?, ?, 'release', ?, ?, ?, ?)
                        """,
                        [_stable_id("membership", work_item_id, "release", release_id, observed_at),
                         work_item_id, release_id, observed_at,
                         "authoritative_manifest" if authoritative else "incremental_observation",
                         history_run["run_id"] if history_run else ""],
                    )

        if authoritative and history_run:
            manifest_refs = {
                row[0] for row in connection.execute(
                    """
                    SELECT item_ref FROM source_evidence_published_items
                    WHERE source_id = ? AND board_id = ?
                      AND dataset = 'jira_issue_history' AND is_current = 1
                    """,
                    [source_id, board_id],
                )
            }
            if manifest_refs:
                placeholders = ", ".join("?" for _ in manifest_refs)
                connection.execute(
                    f"""
                    UPDATE execution_scope_memberships
                    SET state = 'closed', valid_to = ?
                    WHERE state = 'open'
                      AND work_item_id IN (
                          SELECT work_item_id FROM execution_work_items
                          WHERE board_id = ? AND source_id = ?
                            AND source_ref NOT IN ({placeholders})
                      )
                    """,
                    [observed_at, board_id, source_id, *sorted(manifest_refs)],
                )
            else:
                connection.execute(
                    """
                    UPDATE execution_scope_memberships
                    SET state = 'closed', valid_to = ?
                    WHERE state = 'open'
                      AND work_item_id IN (
                          SELECT work_item_id FROM execution_work_items
                          WHERE board_id = ? AND source_id = ?
                      )
                    """,
                    [observed_at, board_id, source_id],
                )

        for link in connection.execute(
            """
            SELECT * FROM jira_issue_links WHERE board_id = ? AND observation_state = 'active'
            """,
            [board_id],
        ):
            predecessor = work_items.get(link["issue_ref"])
            successor = work_items.get(link["related_issue_ref"])
            if not predecessor or not successor:
                continue
            dependency_id = _stable_id("dependency", project_id, link["source_link_ref"])
            connection.execute(
                """
                INSERT INTO execution_dependencies
                    (dependency_id, project_id, source_link_ref, predecessor_work_item_id,
                     successor_work_item_id, dependency_type, state, observed_at, evidence_run_id)
                VALUES (?, ?, ?, ?, ?, ?, 'active', ?, ?)
                ON CONFLICT(project_id, source_link_ref) DO UPDATE SET
                    predecessor_work_item_id=excluded.predecessor_work_item_id,
                    successor_work_item_id=excluded.successor_work_item_id,
                    dependency_type=excluded.dependency_type, state='active',
                    observed_at=excluded.observed_at, evidence_run_id=excluded.evidence_run_id
                """,
                [dependency_id, project_id, link["source_link_ref"], predecessor, successor,
                 link["link_type"], link["observed_at"], links_run["run_id"] if links_run else ""],
            )
            connection.execute(
                """
                INSERT OR IGNORE INTO execution_dependency_observations
                    (observation_id, dependency_id, state, observed_at, evidence_run_id)
                VALUES (?, ?, 'active', ?, ?)
                """,
                [
                    _stable_id(
                        "dependency-observation", dependency_id, link["observed_at"],
                        links_run["run_id"] if links_run else "",
                    ),
                    dependency_id, link["observed_at"], links_run["run_id"] if links_run else "",
                ],
            )

        fact_count = 0
        for release_ref, release_id in release_ids.items():
            members = connection.execute(
                """
                SELECT wi.status_category, wi.story_points FROM execution_scope_memberships sm
                JOIN execution_work_items wi ON wi.work_item_id = sm.work_item_id
                WHERE sm.scope_kind = 'release' AND sm.scope_id = ? AND sm.state = 'open'
                """,
                [release_id],
            ).fetchall()
            if not authoritative:
                _fact(connection, run_id=derivation_run_id, project_id=project_id,
                      subject_kind="release", subject_id=release_id, fact_key="release_scope_count",
                      value=None, value_state="unavailable", freshness_state=freshness,
                      evidence={"reason": "SCOPE_MANIFEST_NOT_AUTHORITATIVE", "release_ref": release_ref})
            else:
                done = sum(item["status_category"] == "done" for item in members)
                _fact(connection, run_id=derivation_run_id, project_id=project_id,
                      subject_kind="release", subject_id=release_id, fact_key="release_scope_count",
                      value={"total": len(members), "done": done}, value_state="known",
                      freshness_state="fresh", evidence={"release_ref": release_ref})
            fact_count += 1
            if not authoritative or any(item["story_points"] is None for item in members):
                state, value = "unavailable", None
            else:
                total = sum(float(item["story_points"]) for item in members)
                done_points = sum(float(item["story_points"]) for item in members if item["status_category"] == "done")
                state, value = "known", {"total": total, "done": done_points}
            _fact(connection, run_id=derivation_run_id, project_id=project_id,
                  subject_kind="release", subject_id=release_id, fact_key="release_story_point_coverage",
                  value=value, value_state=state, freshness_state=freshness,
                  evidence={"release_ref": release_ref})
            fact_count += 1
            observations = connection.execute(
                """
                SELECT source_target_date FROM execution_release_observations
                WHERE release_id = ? ORDER BY observed_at, observation_id
                """,
                [release_id],
            ).fetchall()
            targets = [item["source_target_date"] for item in observations if item["source_target_date"]]
            _fact(connection, run_id=derivation_run_id, project_id=project_id,
                  subject_kind="release", subject_id=release_id, fact_key="release_target_date_change",
                  value={"first": targets[0], "latest": targets[-1]} if targets else None,
                  value_state="known" if len(set(targets)) > 1 else "unknown",
                  freshness_state=freshness, evidence={"observation_count": len(targets)})
            fact_count += 1
        for sprint in connection.execute("SELECT * FROM execution_sprints WHERE board_id = ?", [board_id]):
            _fact(connection, run_id=derivation_run_id, project_id=project_id,
                  subject_kind="sprint", subject_id=sprint["sprint_id"], fact_key="sprint_scope_change",
                  value=None, value_state="unavailable", freshness_state=freshness,
                  evidence={"reason": "COMMITMENT_BOUNDARY_NOT_CAPTURED"})
            fact_count += 1
        for milestone in connection.execute(
            "SELECT * FROM execution_milestones WHERE project_id = ?", [project_id]
        ):
            planned = milestone["planned_date"]
            lifecycle = milestone["lifecycle_state"]
            actual = milestone["actual_date"]
            if not planned or milestone["authority"] in {"", "unknown"}:
                state, value = "unavailable", None
            elif lifecycle == "achieved" and actual:
                state = "known"
                value = "achieved_on_time" if actual <= planned else "achieved_late"
            elif lifecycle in {"cancelled", "unknown"}:
                state, value = "unknown", None
            elif planned < date.today().isoformat():
                state, value = "known", "overdue"
            else:
                state, value = "known", "on_track"
            _fact(connection, run_id=derivation_run_id, project_id=project_id,
                  subject_kind="milestone", subject_id=milestone["milestone_id"],
                  fact_key="milestone_adherence", value=value, value_state=state,
                  freshness_state="fresh" if state == "known" else freshness,
                  evidence={"planned_date": planned, "actual_date": actual, "authority": milestone["authority"]})
            fact_count += 1
        for dependency in connection.execute(
            "SELECT * FROM execution_dependencies WHERE project_id = ?", [project_id]
        ):
            _fact(connection, run_id=derivation_run_id, project_id=project_id,
                  subject_kind="dependency", subject_id=dependency["dependency_id"],
                  fact_key="dependency_readiness", value={"state": dependency["state"]},
                  value_state="known", freshness_state=freshness,
                  evidence={"source_link_ref": dependency["source_link_ref"]})
            fact_count += 1
        connection.execute(
            "UPDATE execution_derivation_runs SET fact_count = ?, finished_at = ? WHERE derivation_run_id = ?",
            [fact_count, _now(), derivation_run_id],
        )
        connection.commit()
    return {"status": "derived", "derivation_run_id": derivation_run_id, "idempotent": False, "fact_count": fact_count}


def _validate_milestones(payload: dict[str, Any]) -> list[dict[str, Any]]:
    records = payload.get("milestones") if isinstance(payload, dict) else None
    if not isinstance(records, list) or not records or len(records) > 100:
        raise ValueError("milestones must contain between 1 and 100 structured records")
    required = {"milestone_id", "project_id", "milestone_type", "criticality", "lifecycle_state", "authority", "completeness_state", "observed_at", "schema_version"}
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for record in records:
        if not isinstance(record, dict) or not required <= set(record):
            raise ValueError("Milestone record is missing required structured fields")
        item = {key: str(record.get(key, "")).strip() for key in required | {"planned_date", "source_target_date", "forecast_date", "actual_date"}}
        if any(not item[key] or len(item[key]) > 200 for key in required):
            raise ValueError("Milestone required fields must be bounded non-empty strings")
        if item["milestone_id"] in seen:
            raise ValueError("Milestone IDs must be unique within one import")
        if item["criticality"] not in {"critical", "high", "medium", "low", "unknown"}:
            raise ValueError("Milestone criticality is invalid")
        if item["lifecycle_state"] not in {"planned", "in_progress", "achieved", "cancelled", "unknown"}:
            raise ValueError("Milestone lifecycle state is invalid")
        if item["completeness_state"] not in VALUE_STATES:
            raise ValueError("Milestone completeness state is invalid")
        for key in ("planned_date", "source_target_date", "forecast_date", "actual_date"):
            if item[key]:
                try:
                    date.fromisoformat(item[key])
                except ValueError as exc:
                    raise ValueError(f"Milestone {key} must be an ISO date") from exc
        try:
            datetime.fromisoformat(item["observed_at"].replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("Milestone observed_at must be an ISO timestamp") from exc
        release_ids = record.get("release_ids", [])
        if not isinstance(release_ids, list) or len(release_ids) > 50 or not all(
            isinstance(value, str) and value.strip() and len(value.strip()) <= 200
            for value in release_ids
        ):
            raise ValueError("Milestone release_ids must be a bounded string list")
        item["release_ids"] = sorted(set(value.strip() for value in release_ids))
        seen.add(item["milestone_id"])
        normalized.append(item)
    return sorted(normalized, key=lambda item: item["milestone_id"])


def _milestone_state(connection: sqlite3.Connection, milestone_id: str) -> dict[str, Any]:
    row = connection.execute(
        "SELECT * FROM execution_milestones WHERE milestone_id = ?", [milestone_id]
    ).fetchone()
    release_ids = [
        item[0] for item in connection.execute(
            "SELECT release_id FROM execution_milestone_release_links WHERE milestone_id = ? ORDER BY release_id",
            [milestone_id],
        )
    ]
    return {"milestone": dict(row) if row else {}, "release_ids": release_ids}


def _validate_release_references(connection: sqlite3.Connection, release_ids: list[str]) -> None:
    for release_id in release_ids:
        if not connection.execute(
            "SELECT 1 FROM execution_release_commitments WHERE release_id = ?", [release_id]
        ).fetchone():
            raise ValueError("Milestone release reference does not exist")


def preview_milestone_import(payload: dict[str, Any], *, db_path: str | Path | None = None, ttl_minutes: int = 30) -> dict[str, Any]:
    records = _validate_milestones(payload)
    if not 1 <= ttl_minutes <= 60:
        raise ValueError("ttl_minutes must be between 1 and 60")
    with _connection(db_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        current = []
        for record in records:
            if not connection.execute("SELECT 1 FROM projects WHERE id = ?", [record["project_id"]]).fetchone():
                raise ValueError("Milestone project does not exist")
            _validate_release_references(connection, record["release_ids"])
            current.append(_milestone_state(connection, record["milestone_id"]))
        fingerprint = hashlib.sha256(_json({"records": records, "current": current}).encode()).hexdigest()
        changes = [
            record["milestone_id"] for record, existing in zip(records, current)
            if not existing["milestone"]
            or any(
                existing["milestone"].get(key, "") != record[key]
                for key in record if key != "release_ids"
            )
            or existing["release_ids"] != record["release_ids"]
        ]
        if not changes:
            connection.rollback()
            return {"status": "no_op", "changes": []}
        operation_id, token = f"milestone-op-{uuid4().hex}", secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)
        expires = now + timedelta(minutes=ttl_minutes)
        proposed = {"milestones": records, "changes": changes}
        connection.execute(
            """
            INSERT INTO milestone_import_operations
                (operation_id, status, token_hash, request_json, proposed_json, fingerprint, created_at, expires_at)
            VALUES (?, 'proposed', ?, ?, ?, ?, ?, ?)
            """,
            [operation_id, hashlib.sha256(token.encode()).hexdigest(), _json(payload), _json(proposed), fingerprint,
             now.isoformat(timespec="seconds"), expires.isoformat(timespec="seconds")],
        )
        connection.commit()
    return {"status": "proposed", "operation_id": operation_id, "confirmation_token": token, "expires_at": expires.isoformat(timespec="seconds"), "proposed": proposed}


def confirm_milestone_import(operation_id: str, confirmation_token: str, *, db_path: str | Path | None = None) -> dict[str, Any]:
    with _connection(db_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute("SELECT * FROM milestone_import_operations WHERE operation_id = ?", [operation_id]).fetchone()
        if not row:
            raise ValueError("Unknown Milestone import operation")
        operation = dict(row)
        supplied = hashlib.sha256(confirmation_token.encode()).hexdigest()
        if not secrets.compare_digest(operation["token_hash"], supplied):
            raise ValueError("Invalid confirmation token")
        if operation["status"] == "confirmed":
            connection.commit()
            result = json.loads(operation["result_json"] or "{}")
            return {
                **result,
                "status": "confirmed",
                "operation_id": operation_id,
                "idempotent": True,
            }
        if operation["status"] != "proposed":
            raise ValueError("Milestone import is not confirmable")
        if datetime.fromisoformat(operation["expires_at"]) <= datetime.now(timezone.utc):
            connection.execute("UPDATE milestone_import_operations SET status='expired' WHERE operation_id = ?", [operation_id])
            connection.commit()
            return {"status": "expired", "operation_id": operation_id}
        claimed = connection.execute("UPDATE milestone_import_operations SET status='claimed' WHERE operation_id = ? AND status = 'proposed'", [operation_id])
        if claimed.rowcount != 1:
            raise ValueError("Milestone import was already claimed")
        proposed = json.loads(operation["proposed_json"])
        records = proposed["milestones"]
        current = []
        for record in records:
            if not connection.execute("SELECT 1 FROM projects WHERE id = ?", [record["project_id"]]).fetchone():
                raise ValueError("Milestone project no longer exists")
            _validate_release_references(connection, record["release_ids"])
            current.append(_milestone_state(connection, record["milestone_id"]))
        fingerprint = hashlib.sha256(_json({"records": records, "current": current}).encode()).hexdigest()
        if fingerprint != operation["fingerprint"]:
            connection.execute("UPDATE milestone_import_operations SET status='rejected', failure_code='STALE_FINGERPRINT' WHERE operation_id = ?", [operation_id])
            connection.commit()
            return {"status": "rejected", "operation_id": operation_id, "reason": "STALE_FINGERPRINT"}
        for record in records:
            first_target = record["source_target_date"]
            existing = connection.execute("SELECT first_observed_target_date FROM execution_milestones WHERE milestone_id = ?", [record["milestone_id"]]).fetchone()
            if existing and existing["first_observed_target_date"]:
                first_target = existing["first_observed_target_date"]
            connection.execute(
                """
                INSERT INTO execution_milestones
                    (milestone_id, project_id, milestone_type, criticality, lifecycle_state,
                     planned_date, source_target_date, forecast_date, actual_date,
                     first_observed_target_date, authority, completeness_state, observed_at,
                     schema_version, latest_operation_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(milestone_id) DO UPDATE SET
                    project_id=excluded.project_id, milestone_type=excluded.milestone_type,
                    criticality=excluded.criticality, lifecycle_state=excluded.lifecycle_state,
                    planned_date=excluded.planned_date, source_target_date=excluded.source_target_date,
                    forecast_date=excluded.forecast_date, actual_date=excluded.actual_date,
                    authority=excluded.authority, completeness_state=excluded.completeness_state,
                    observed_at=excluded.observed_at, schema_version=excluded.schema_version,
                    latest_operation_id=excluded.latest_operation_id
                """,
                [record["milestone_id"], record["project_id"], record["milestone_type"], record["criticality"],
                 record["lifecycle_state"], record["planned_date"], record["source_target_date"],
                 record["forecast_date"], record["actual_date"], first_target, record["authority"],
                 record["completeness_state"], record["observed_at"], record["schema_version"], operation_id],
            )
            connection.execute(
                """
                INSERT OR IGNORE INTO execution_milestone_observations
                    (observation_id, milestone_id, planned_date, source_target_date, forecast_date,
                     actual_date, lifecycle_state, authority, completeness_state, observed_at, operation_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [_stable_id("milestone-observation", record["milestone_id"], record["observed_at"], operation_id),
                 record["milestone_id"], record["planned_date"], record["source_target_date"],
                 record["forecast_date"], record["actual_date"], record["lifecycle_state"], record["authority"],
                 record["completeness_state"], record["observed_at"], operation_id],
            )
            if record["release_ids"]:
                placeholders = ",".join("?" for _ in record["release_ids"])
                connection.execute(
                    f"DELETE FROM execution_milestone_release_links WHERE milestone_id = ? AND release_id NOT IN ({placeholders})",
                    [record["milestone_id"], *record["release_ids"]],
                )
            else:
                connection.execute(
                    "DELETE FROM execution_milestone_release_links WHERE milestone_id = ?",
                    [record["milestone_id"]],
                )
            for release_id in record["release_ids"]:
                connection.execute(
                    """
                    INSERT OR IGNORE INTO execution_milestone_release_links
                        (milestone_id, release_id, operation_id)
                    VALUES (?, ?, ?)
                    """,
                    [record["milestone_id"], release_id, operation_id],
                )
        result = {"status": "confirmed", "operation_id": operation_id, "milestone_count": len(records), "idempotent": False}
        connection.execute("UPDATE milestone_import_operations SET status='confirmed', confirmed_at=?, result_json=? WHERE operation_id = ?", [_now(), _json(result), operation_id])
        connection.commit()
    return result
