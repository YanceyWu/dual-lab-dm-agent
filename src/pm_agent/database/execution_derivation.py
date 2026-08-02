"""Deterministic derivation owner for Phase 3 execution facts."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import date
from pathlib import Path
from typing import Any
from uuid import uuid4

from pm_agent.database.execution_common import (
    RULE_VERSION,
    connection_scope,
    json_dumps,
    now_utc,
    stable_id,
)


def _parse_list(value: str) -> list[str]:
    try:
        parsed = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return []
    return [item for item in parsed if isinstance(item, str) and item]


def _parse_refs(value: str) -> list[str]:
    parsed = _parse_list(value)
    if parsed:
        return parsed
    return [value] if value else []


def _legacy_snapshot_input(connection: sqlite3.Connection, board_id: str) -> str:
    """Return a stable revision for every mutable legacy snapshot B2 reads."""
    snapshots = {
        "issues": [
            tuple(row) for row in connection.execute(
                """
                SELECT id, version_id, status, status_category, story_points, synced_at
                FROM jira_issues WHERE board_id = ? ORDER BY id
                """,
                [board_id],
            )
        ],
        "releases": [
            tuple(row) for row in connection.execute(
                """
                SELECT id, release_date, status, released, synced_at
                FROM jira_stream_versions WHERE board_id = ? ORDER BY id
                """,
                [board_id],
            )
        ],
        "sprints": [
            tuple(row) for row in connection.execute(
                """
                SELECT id, state, start_date, end_date, synced_at
                FROM jira_sprints WHERE board_id = ? ORDER BY id
                """,
                [board_id],
            )
        ],
    }
    return f"legacy-snapshot-{hashlib.sha256(json_dumps(snapshots).encode()).hexdigest()}"


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
            stable_id("fact", run_id, subject_kind, subject_id, fact_key), run_id,
            project_id, subject_kind, subject_id, fact_key, json_dumps(value), value_state,
            freshness_state, json_dumps(evidence),
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
    work_item_id = stable_id("work", source_id, board_id, source_ref)
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
            stable_id("source-identity", "work_item", source_id, board_id, source_ref),
            work_item_id, source_id, board_id, source_ref, observed_at, observed_at,
        ],
    )
    return work_item_id


def derive_board(board_id: str, *, db_path: str | Path | None = None) -> dict[str, Any]:
    """Canonicalize published evidence for one board without automatic triggering."""
    with connection_scope(db_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        project_id = _board_project(connection, board_id)
        history_run = _latest_run(connection, board_id, "jira_issue_history")
        links_run = _latest_run(connection, board_id, "jira_issue_links")
        source_run_ids = [item["run_id"] for item in (history_run, links_run) if item]
        legacy_snapshot_id = _legacy_snapshot_input(connection, board_id)
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
            json_dumps([board_id, RULE_VERSION, source_run_ids, legacy_snapshot_id, milestone_operations]).encode()
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
             "complete" if authoritative else "partial", freshness, json_dumps(warnings), now_utc()],
        )
        for source_run_id in source_run_ids:
            connection.execute(
                "INSERT INTO execution_derivation_inputs VALUES (?, 'source_evidence_run', ?)",
                [derivation_run_id, source_run_id],
            )
        connection.execute(
            "INSERT INTO execution_derivation_inputs VALUES (?, 'legacy_sync', ?)",
            [derivation_run_id, legacy_snapshot_id],
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
                fields.setdefault("fix_versions", json_dumps([issue["version_id"]]))

        work_items: dict[str, str] = {}
        observed_at = now_utc()
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
                    stable_id("work-observation", work_item_id, event["dedup_key"]),
                    work_item_id, event["field_key"], event["from_value"], event["to_value"],
                    event["source_event_ref"], event["source_updated_at"], event["observed_at"],
                    event["last_published_run_id"],
                ],
            )

        release_ids: dict[str, str] = {}
        for row in connection.execute("SELECT * FROM jira_stream_versions WHERE board_id = ?", [board_id]):
            release_id = stable_id("release", board_id, row["id"])
            release_ids[row["id"]] = release_id
            target = row["release_date"] or ""
            snapshot_observed_at = row["synced_at"] or observed_at
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
                 target if row["released"] else "", target, snapshot_observed_at],
            )
            connection.execute(
                """
                INSERT OR IGNORE INTO execution_release_observations
                    (observation_id, release_id, source_target_date, actual_date,
                     lifecycle_state, target_authority, observed_at, source_input_id)
                VALUES (?, ?, ?, ?, ?, 'unknown', ?, ?)
                """,
                [
                    stable_id("release-observation", release_id, target, row["status"] or "unknown", observed_at),
                    release_id, target, target if row["released"] else "", row["status"] or "unknown",
                    snapshot_observed_at, legacy_snapshot_id,
                ],
            )

        sprint_ids: dict[str, str] = {}
        for row in connection.execute("SELECT * FROM jira_sprints WHERE board_id = ?", [board_id]):
            sprint_id = stable_id("sprint", board_id, row["id"])
            sprint_ids[row["id"]] = sprint_id
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
                        [stable_id("membership", work_item_id, "release", release_id, observed_at),
                         work_item_id, release_id, observed_at,
                         "authoritative_manifest" if authoritative else "incremental_observation",
                         history_run["run_id"] if history_run else ""],
                    )
            for sprint_ref in _parse_refs(fields.get("sprint", "")):
                sprint_id = sprint_ids.get(sprint_ref)
                if sprint_id:
                    connection.execute(
                        """
                        INSERT OR IGNORE INTO execution_scope_memberships
                            (membership_id, work_item_id, scope_kind, scope_id, valid_from,
                             boundary_basis, evidence_run_id)
                        VALUES (?, ?, 'sprint', ?, ?, ?, ?)
                        """,
                        [stable_id("membership", work_item_id, "sprint", sprint_id, observed_at),
                         work_item_id, sprint_id, observed_at,
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
            for source_ref in manifest_refs:
                work_item_id = work_items.get(source_ref)
                if not work_item_id:
                    continue
                fields = latest_fields.get(source_ref, {})
                desired_release_ids = {
                    release_ids[ref] for ref in _parse_list(fields.get("fix_versions", "[]"))
                    if ref in release_ids
                }
                desired_sprint_refs = _parse_refs(fields.get("sprint", ""))
                desired_sprint_ids = {
                    sprint_ids[ref] for ref in desired_sprint_refs if ref in sprint_ids
                }
                for scope_kind, desired_ids, complete_mapping in (
                    ("release", desired_release_ids, True),
                    ("sprint", desired_sprint_ids, len(desired_sprint_ids) == len(desired_sprint_refs)),
                ):
                    if not complete_mapping:
                        continue
                    if desired_ids:
                        placeholders = ", ".join("?" for _ in desired_ids)
                        connection.execute(
                            f"""
                            UPDATE execution_scope_memberships
                            SET state = 'closed', valid_to = ?
                            WHERE work_item_id = ? AND scope_kind = ? AND state = 'open'
                              AND scope_id NOT IN ({placeholders})
                            """,
                            [observed_at, work_item_id, scope_kind, *sorted(desired_ids)],
                        )
                    else:
                        connection.execute(
                            """
                            UPDATE execution_scope_memberships
                            SET state = 'closed', valid_to = ?
                            WHERE work_item_id = ? AND scope_kind = ? AND state = 'open'
                            """,
                            [observed_at, work_item_id, scope_kind],
                        )

        links_authoritative = bool(
            links_run
            and links_run["coverage_status"] == "complete"
            and links_run["authoritative_manifest"]
        )
        current_link_refs = {
            row[0] for row in connection.execute(
                """
                SELECT item_ref FROM source_evidence_published_items
                WHERE source_id = ? AND board_id = ?
                  AND dataset = 'jira_issue_links' AND is_current = 1
                """,
                [links_run["source_id"], board_id],
            )
        } if links_authoritative and links_run else set()
        link_rows = connection.execute(
            """
            SELECT * FROM jira_issue_links WHERE board_id = ? AND observation_state = 'active'
            """,
            [board_id],
        )
        for link in link_rows:
            if links_authoritative and link["source_link_ref"] not in current_link_refs:
                continue
            predecessor = work_items.get(link["issue_ref"])
            successor = work_items.get(link["related_issue_ref"])
            if not predecessor or not successor:
                continue
            dependency_id = stable_id("dependency", project_id, link["source_link_ref"])
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
                    stable_id(
                        "dependency-observation", dependency_id, link["observed_at"],
                        links_run["run_id"] if links_run else "",
                    ),
                    dependency_id, link["observed_at"], links_run["run_id"] if links_run else "",
                ],
            )

        if links_authoritative and links_run:
            closed_dependencies = connection.execute(
                """
                SELECT dependency_id FROM execution_dependencies
                WHERE project_id = ? AND state = 'active'
                  AND evidence_run_id IN (
                      SELECT run_id FROM source_evidence_runs
                      WHERE source_id = ? AND board_id = ? AND dataset = 'jira_issue_links'
                  )
                """,
                [project_id, links_run["source_id"], board_id],
            ).fetchall()
            for dependency in closed_dependencies:
                dependency_id = dependency["dependency_id"]
                source_link_ref = connection.execute(
                    "SELECT source_link_ref FROM execution_dependencies WHERE dependency_id = ?",
                    [dependency_id],
                ).fetchone()[0]
                if source_link_ref in current_link_refs:
                    continue
                connection.execute(
                    "UPDATE execution_dependencies SET state = 'inactive', observed_at = ?, evidence_run_id = ? WHERE dependency_id = ?",
                    [observed_at, links_run["run_id"], dependency_id],
                )
                connection.execute(
                    """
                    INSERT OR IGNORE INTO execution_dependency_observations
                        (observation_id, dependency_id, state, observed_at, evidence_run_id)
                    VALUES (?, ?, 'inactive', ?, ?)
                    """,
                    [stable_id("dependency-observation", dependency_id, "inactive", links_run["run_id"]),
                     dependency_id, observed_at, links_run["run_id"]],
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
            "SELECT * FROM execution_dependencies WHERE project_id = ? AND state = 'active'", [project_id]
        ):
            _fact(connection, run_id=derivation_run_id, project_id=project_id,
                  subject_kind="dependency", subject_id=dependency["dependency_id"],
                  fact_key="dependency_readiness", value={"state": dependency["state"]},
                  value_state="known", freshness_state=freshness,
                  evidence={"source_link_ref": dependency["source_link_ref"]})
            fact_count += 1
        connection.execute(
            "UPDATE execution_derivation_runs SET fact_count = ?, finished_at = ? WHERE derivation_run_id = ?",
            [fact_count, now_utc(), derivation_run_id],
        )
        connection.commit()
    return {"status": "derived", "derivation_run_id": derivation_run_id, "idempotent": False, "fact_count": fact_count}
