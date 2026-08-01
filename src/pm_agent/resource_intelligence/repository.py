"""Persistence boundary for atomic capacity publication and audit."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator
from uuid import uuid4

from pm_agent.config import settings


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


@contextmanager
def connection(db_path: str | Path | None = None) -> Iterator[sqlite3.Connection]:
    database = sqlite3.connect(Path(db_path or settings.database_path), isolation_level=None)
    database.row_factory = sqlite3.Row
    database.execute("PRAGMA foreign_keys = ON")
    database.execute("PRAGMA busy_timeout = 10000")
    try:
        yield database
    finally:
        database.close()


def session_by_fingerprint(fingerprint: str, *, db_path=None) -> dict[str, Any] | None:
    with connection(db_path) as database:
        row = database.execute(
            "SELECT * FROM resource_capacity_import_sessions WHERE package_fingerprint=?",
            [fingerprint],
        ).fetchone()
    return dict(row) if row else None


def completed_session_for_package(package_id: str, *, db_path=None) -> dict[str, Any] | None:
    with connection(db_path) as database:
        row = database.execute(
            """SELECT * FROM resource_capacity_import_sessions
               WHERE package_id=? AND status='completed'
               ORDER BY completed_at DESC LIMIT 1""",
            [package_id],
        ).fetchone()
    return dict(row) if row else None


def session_for_idempotency_key(key: str, *, db_path=None) -> dict[str, Any] | None:
    with connection(db_path) as database:
        row = database.execute(
            "SELECT * FROM resource_capacity_import_sessions WHERE idempotency_key=?", [key]
        ).fetchone()
    return dict(row) if row else None


def load_session(session_id: str, *, db_path=None) -> dict[str, Any] | None:
    with connection(db_path) as database:
        row = database.execute(
            "SELECT * FROM resource_capacity_import_sessions WHERE session_id=?", [session_id]
        ).fetchone()
    return dict(row) if row else None


def create_session(
    *, session_id: str, package: dict[str, Any], fingerprint: str, status: str,
    created_at: str, failure_code: str = "", report: dict[str, Any] | None = None,
    db_path=None,
) -> None:
    with connection(db_path) as database:
        database.execute(
            """INSERT INTO resource_capacity_import_sessions
               (session_id,package_id,idempotency_key,schema_version,package_fingerprint,
                package_json,status,created_at,completed_at,failure_code,report_json)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            [session_id, package["package_id"], package["idempotency_key"],
             package["schema_version"], fingerprint, _json(package), status, created_at,
             created_at if status == "rejected" else "", failure_code, _json(report or {})],
        )


def record_run(*, session_id: str, attempt_id: str | None, step_key: str,
               status: str, counts: dict[str, int], warning_codes: list[str],
               created_at: str, db_path=None) -> None:
    with connection(db_path) as database:
        database.execute(
            """INSERT INTO resource_capacity_import_runs
               (run_id,session_id,attempt_id,step_key,status,counts_json,
                warning_codes_json,created_at) VALUES (?,?,?,?,?,?,?,?)""",
            [f"resource-capacity-run-{uuid4().hex}", session_id, attempt_id, step_key,
             status, _json(counts), _json(warning_codes), created_at],
        )


def start_attempt(session_id: str, *, started_at: str, db_path=None) -> str:
    attempt_id = f"resource-capacity-attempt-{uuid4().hex}"
    with connection(db_path) as database:
        database.execute("BEGIN IMMEDIATE")
        claimed = database.execute(
            """UPDATE resource_capacity_import_sessions SET status='running',failure_code=''
               WHERE session_id=? AND status IN ('previewed','failed')""", [session_id]
        )
        if claimed.rowcount != 1:
            raise ValueError("RESOURCE_CAPACITY_SESSION_NOT_CONFIRMABLE")
        database.execute(
            """INSERT INTO resource_capacity_import_attempts
               (attempt_id,session_id,status,started_at) VALUES (?,?,'running',?)""",
            [attempt_id, session_id, started_at],
        )
        database.commit()
    return attempt_id


def fail_attempt(*, session_id: str, attempt_id: str, failure_code: str,
                 finished_at: str, db_path=None) -> None:
    with connection(db_path) as database:
        database.execute("BEGIN IMMEDIATE")
        database.execute(
            """UPDATE resource_capacity_import_attempts
               SET status='failed',finished_at=?,failure_code=? WHERE attempt_id=?""",
            [finished_at, failure_code, attempt_id],
        )
        database.execute(
            """UPDATE resource_capacity_import_sessions
               SET status='failed',failure_code=? WHERE session_id=?""",
            [failure_code, session_id],
        )
        database.execute(
            """INSERT INTO resource_capacity_import_runs
               (run_id,session_id,attempt_id,step_key,status,counts_json,
                warning_codes_json,created_at) VALUES (?,?,?,'publication','failed','{}',?,?)""",
            [f"resource-capacity-run-{uuid4().hex}", session_id, attempt_id,
             _json([failure_code]), finished_at],
        )
        database.commit()


def current_observation_versions(*, db_path=None) -> dict[tuple[Any, ...], tuple[int, str]]:
    with connection(db_path) as database:
        rows = database.execute(
            """SELECT o.member_id,o.year,o.month,o.commitment_kind,
                      o.source_observation_version,o.observation_fingerprint
               FROM resource_capacity_observations o
               JOIN resource_capacity_publications p ON p.publication_id=o.publication_id
               WHERE p.is_current=1"""
        ).fetchall()
    return {
        (r["member_id"], r["year"], r["month"], r["commitment_kind"]):
        (r["source_observation_version"], r["observation_fingerprint"])
        for r in rows
    }


def current_scope(*, db_path=None) -> set[tuple[str, int, int, str]] | None:
    with connection(db_path) as database:
        current = database.execute(
            "SELECT publication_id FROM resource_capacity_publications WHERE is_current=1"
        ).fetchone()
        if not current:
            return None
        rows = database.execute(
            """SELECT member_id,year,month,commitment_kind
               FROM resource_capacity_manifest_coverage WHERE publication_id=?""",
            [current["publication_id"]],
        ).fetchall()
    return {(r["member_id"], r["year"], r["month"], r["commitment_kind"]) for r in rows}


def _integrity_report(database: sqlite3.Connection) -> dict[str, Any]:
    integrity = [row[0] for row in database.execute("PRAGMA integrity_check")]
    foreign_keys = database.execute("PRAGMA foreign_key_check").fetchall()
    return {
        "sqlite_integrity": "ok" if integrity == ["ok"] else "failed",
        "foreign_key_violations": len(foreign_keys),
        "state": "passed" if integrity == ["ok"] and not foreign_keys else "failed",
    }


def _core_counts(database: sqlite3.Connection) -> dict[str, int]:
    return {
        table: database.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
        for table in ("employees", "projects", "plan_versions", "monthly_allocations")
    }


def publish(*, session_id: str, attempt_id: str, fingerprint: str,
            package: dict[str, Any], dependency: dict[str, Any],
            derivations: list[dict[str, Any]], published_at: str, db_path=None) -> dict[str, Any]:
    publication_id = f"resource-capacity-publication-{uuid4().hex}"
    with connection(db_path) as database:
        database.execute("BEGIN IMMEDIATE")
        core_counts_before = _core_counts(database)
        idempotency_conflict = database.execute(
            """SELECT 1 FROM resource_capacity_import_sessions
               WHERE idempotency_key=? AND status='completed' AND session_id<>?""",
            [package["idempotency_key"], session_id],
        ).fetchone()
        if idempotency_conflict:
            raise ValueError("RESOURCE_CAPACITY_IDEMPOTENCY_KEY_CONFLICT")
        current_publication = database.execute(
            "SELECT publication_id FROM resource_capacity_publications WHERE is_current=1"
        ).fetchone()
        if current_publication:
            prior_rows = database.execute(
                """SELECT member_id,year,month,commitment_kind,
                          source_observation_version
                   FROM resource_capacity_observations WHERE publication_id=?""",
                [current_publication["publication_id"]],
            ).fetchall()
            prior_versions = {
                (row["member_id"], row["year"], row["month"], row["commitment_kind"]):
                row["source_observation_version"]
                for row in prior_rows
            }
            incoming_versions = {
                (row["member_id"], row["year"], row["month"], row["commitment_kind"]):
                row["source_observation_version"]
                for row in package["observations"]
            }
            if set(incoming_versions) != set(prior_versions):
                raise ValueError("RESOURCE_CAPACITY_REPLACEMENT_SCOPE_INCOMPLETE")
            if any(incoming_versions[key] <= version for key, version in prior_versions.items()):
                raise ValueError("RESOURCE_CAPACITY_OBSERVATION_VERSION_CONFLICT")
        database.execute(
            "UPDATE resource_capacity_publications SET is_current=0 WHERE is_current=1"
        )
        database.execute(
            """INSERT INTO resource_capacity_publications
               (publication_id,session_id,package_id,package_fingerprint,schema_version,
                workforce_publication_id,plan_version_id,assessment_time,published_at,
                is_current,report_json) VALUES (?,?,?,?,?,?,?,?,?,1,'{}')""",
            [publication_id, session_id, package["package_id"], fingerprint,
             package["schema_version"], dependency["publication_id"],
             package["plan_version_id"], package["assessment_time"], published_at],
        )
        observations_by_key = {
            (o["member_id"], o["year"], o["month"], o["commitment_kind"]): o
            for o in package["observations"]
        }
        for key in package["manifest"]["coverage_keys"]:
            identity = (key["member_id"], key["year"], key["month"], key["commitment_kind"])
            observation = observations_by_key[identity]
            database.execute(
                """INSERT INTO resource_capacity_manifest_coverage
                   (publication_id,member_id,year,month,commitment_kind,authoritative_source_id)
                   VALUES (?,?,?,?,?,?)""",
                [publication_id, *identity, observation["authoritative_source_id"]],
            )
            database.execute(
                """INSERT INTO resource_capacity_observations
                   (observation_id,publication_id,member_id,year,month,commitment_kind,
                    fraction,value_state,authoritative_source_id,source_reference,observed_at,
                    rule_version,source_observation_version,observation_fingerprint)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                [f"resource-capacity-observation-{uuid4().hex}", publication_id, *identity,
                 observation["fraction"], observation["value_state"],
                 observation["authoritative_source_id"], observation["source_reference"],
                 observation["observed_at"], observation["rule_version"],
                 observation["source_observation_version"], observation["fingerprint"]],
            )
        for item in derivations:
            database.execute(
                """INSERT INTO resource_capacity_derivations
                   (derivation_id,publication_id,workforce_publication_id,plan_version_id,
                    member_id,year,month,state,state_reason,base_capacity,leave_fraction,
                    bau_fraction,non_project_fraction,non_project_deduction,
                    effective_capacity_raw,effective_capacity,planned_project_allocation,
                    available_capacity_raw,available_capacity,total_commitment,overload_amount,
                    overload_state,assessment_time,derivation_rule_version,
                    freshness_rule_version,base_rule_version,overload_rule_version,evidence_json)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                [f"resource-capacity-derivation-{uuid4().hex}", publication_id,
                 dependency["publication_id"], package["plan_version_id"], item["member_id"],
                 item["year"], item["month"], item["state"], item["state_reason"],
                 item["base_capacity"], item["leave_fraction"], item["bau_fraction"],
                 item["non_project_fraction"], item["non_project_deduction"],
                 item["effective_capacity_raw"], item["effective_capacity"],
                 item["planned_project_allocation"], item["available_capacity_raw"],
                 item["available_capacity"], item["total_commitment"], item["overload_amount"],
                 item["overload_state"], package["assessment_time"],
                 "effective-capacity-v1", "capacity-freshness-720h-v1",
                 "active-full-month-base-v1", "capacity-overload-v1", _json(item["evidence"])],
            )
        integrity = _integrity_report(database)
        if integrity["state"] != "passed":
            raise RuntimeError("RESOURCE_CAPACITY_INTEGRITY_FAILED")
        core_counts_after = _core_counts(database)
        if core_counts_after != core_counts_before:
            raise RuntimeError("RESOURCE_CAPACITY_ROLLBACK_COMPATIBILITY_FAILED")
        state_counts = {state: sum(d["state"] == state for d in derivations)
                        for state in ("known", "stale", "unknown", "conflicting")}
        report = {
            "publication_id": publication_id,
            "package_id": package["package_id"],
            "schema_version": package["schema_version"],
            "counts": {"observations": len(package["observations"]),
                       "derivations": len(derivations)},
            "coverage": {"state": "complete", "authoritative_manifest": True,
                         "missing_record_count": 0, "explicit_zero_count":
                         sum(o["fraction"] == 0 for o in package["observations"]),
                         "derivation_states": state_counts},
            "integrity": integrity,
            "software_rollback": {"state": "passed",
                                  "strategy": "phase4_runtime_ignores_additive_resource_capacity_tables",
                                  "prior_runtime_unchanged": True,
                                  "core_counts_before": core_counts_before,
                                  "core_counts_after": core_counts_after},
            "attempt_id": attempt_id,
        }
        database.execute(
            "UPDATE resource_capacity_publications SET report_json=? WHERE publication_id=?",
            [_json(report), publication_id],
        )
        for step, counts in (
            ("publication", {"observations": len(package["observations"])}),
            ("derivation", {"derivations": len(derivations)}),
            ("integrity", {"foreign_key_violations": integrity["foreign_key_violations"]}),
            ("rollback_compatibility", {"prior_runtime_unchanged": 1}),
        ):
            database.execute(
                """INSERT INTO resource_capacity_import_runs
                   (run_id,session_id,attempt_id,step_key,status,counts_json,
                    warning_codes_json,created_at) VALUES (?,?,?,?,'completed',?,'[]',?)""",
                [f"resource-capacity-run-{uuid4().hex}", session_id, attempt_id, step,
                 _json(counts), published_at],
            )
        database.execute(
            "UPDATE resource_capacity_import_attempts SET status='completed',finished_at=? WHERE attempt_id=?",
            [published_at, attempt_id],
        )
        database.execute(
            """UPDATE resource_capacity_import_sessions
               SET status='completed',completed_at=?,failure_code='',report_json=? WHERE session_id=?""",
            [published_at, _json(report), session_id],
        )
        database.commit()
    return report
