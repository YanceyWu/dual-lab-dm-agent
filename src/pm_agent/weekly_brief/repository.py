"""Narrow persistence operations for Weekly Brief v2 capture history."""

from __future__ import annotations

import json
import hashlib
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from pm_agent.config import settings


def json_value(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _digest(value: Any) -> str:
    return hashlib.sha256(json_value(value).encode()).hexdigest()


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


def load_operation(operation_id: str, *, db_path=None) -> dict[str, Any] | None:
    with connection(db_path) as database:
        row = database.execute(
            "SELECT * FROM weekly_brief_snapshot_operations WHERE operation_id=?", [operation_id]
        ).fetchone()
    return dict(row) if row else None


def load_by_idempotency(actor_id: str, idempotency_key: str, *, db_path=None) -> dict[str, Any] | None:
    with connection(db_path) as database:
        row = database.execute(
            """SELECT * FROM weekly_brief_snapshot_operations
               WHERE actor_id=? AND idempotency_key=?""", [actor_id, idempotency_key]
        ).fetchone()
    return dict(row) if row else None


def insert_proposal(row: dict[str, Any], *, db_path=None) -> bool:
    columns = sorted(row)
    with connection(db_path) as database:
        try:
            database.execute(
                f"INSERT INTO weekly_brief_snapshot_operations ({','.join(columns)}) "
                f"VALUES ({','.join('?' for _ in columns)})",
                [row[column] for column in columns],
            )
        except sqlite3.IntegrityError:
            return False
    return True


def claim(operation_id: str, *, token_hash: str, now: str, db_path=None) -> dict[str, Any] | None:
    """Atomically claim one unexpired proposal, returning its immutable candidate."""
    with connection(db_path) as database:
        database.execute("BEGIN IMMEDIATE")
        row = database.execute(
            "SELECT * FROM weekly_brief_snapshot_operations WHERE operation_id=?", [operation_id]
        ).fetchone()
        if not row:
            database.rollback()
            return None
        data = dict(row)
        if data["status"] in ("proposed", "claimed") and data["confirmation_token_hash"] != token_hash:
            database.rollback()
            return data
        if data["status"] in ("proposed", "claimed") and data["expires_at"] <= now:
            database.execute(
                """UPDATE weekly_brief_snapshot_operations SET status='expired',
                   failure_code='WEEKLY_BRIEF_CAPTURE_OPERATION_EXPIRED' WHERE operation_id=?""",
                [operation_id],
            )
            database.commit()
            data["status"] = "expired"
            data["failure_code"] = "WEEKLY_BRIEF_CAPTURE_OPERATION_EXPIRED"
            return data
        if data["status"] == "confirmed":
            database.rollback()
            return data
        if data["status"] == "claimed":
            database.rollback()
            return data
        if data["status"] != "proposed":
            database.rollback()
            return data
        updated = database.execute(
            "UPDATE weekly_brief_snapshot_operations SET status='claimed',claimed_at=? "
            "WHERE operation_id=? AND status='proposed' AND confirmation_token_hash=?", [now, operation_id, token_hash]
        )
        if updated.rowcount != 1:
            database.rollback()
            return None
        database.commit()
        data["status"] = "claimed"
        return data


def confirm(operation_id: str, *, snapshot_id: str, confirmed_at: str, db_path=None) -> bool:
    with connection(db_path) as database:
        database.execute("BEGIN IMMEDIATE")
        updated = database.execute(
            """UPDATE weekly_brief_snapshot_operations
               SET status='confirmed', snapshot_id=?, confirmed_at=?
               WHERE operation_id=? AND status='claimed' AND expires_at>?""",
            [snapshot_id, confirmed_at, operation_id, confirmed_at],
        )
        database.commit()
    return updated.rowcount == 1


def fail_claim(operation_id: str, *, code: str, db_path=None) -> None:
    with connection(db_path) as database:
        database.execute(
            """UPDATE weekly_brief_snapshot_operations SET status='failed', failure_code=?,
               confirmation_token_hash='' WHERE operation_id=? AND status='claimed'""",
            [code, operation_id],
        )


def latest_confirmed(scope_fingerprint: str, comparison_rule_version: str, contract_version: str, *, db_path=None) -> dict[str, Any] | None:
    with connection(db_path) as database:
        row = database.execute(
            """SELECT * FROM weekly_brief_snapshot_operations
               WHERE status='confirmed' AND structural_status='complete'
                 AND scope_fingerprint=? AND comparison_rule_version=? AND contract_version=?
               ORDER BY confirmed_at DESC, operation_id DESC LIMIT 1""", [scope_fingerprint, comparison_rule_version, contract_version]
        ).fetchone()
    return dict(row) if row else None


def baseline_is_eligible(snapshot_id: str, fingerprint: str, scope_fingerprint: str, rule_version: str, contract_version: str, *, db_path=None) -> bool:
    with connection(db_path) as database:
        return database.execute("SELECT 1 FROM weekly_brief_snapshot_operations WHERE snapshot_id=? AND result_fingerprint=? AND scope_fingerprint=? AND comparison_rule_version=? AND contract_version=? AND status='confirmed' AND structural_status='complete'", [snapshot_id, fingerprint, scope_fingerprint, rule_version, contract_version]).fetchone() is not None


def integrity_report(*, db_path=None) -> dict[str, Any]:
    with connection(db_path) as database:
        integrity = [row[0] for row in database.execute("PRAGMA integrity_check")]
        foreign_keys = database.execute("PRAGMA foreign_key_check").fetchall()
        malformed = database.execute(
            """SELECT COUNT(*) FROM weekly_brief_snapshot_operations
               WHERE structural_status != 'complete'
                  OR length(result_fingerprint) != 64
                  OR (status='confirmed' AND (snapshot_id IS NULL OR confirmed_at=''))"""
        ).fetchone()[0]
        for row in database.execute("SELECT * FROM weekly_brief_snapshot_operations WHERE structural_status='complete'"):
            try:
                candidate = json.loads(row["candidate_json"])
                from pm_agent.weekly_brief.snapshots import _normalized
                original_candidate = {key: candidate[key] for key in (
                    "execution_id", "contract_version", "comparison_rule_version", "generated_at", "week_key", "scope", "input", "baseline_snapshot_id", "baseline_fingerprint", "statement_manifest", "evidence_summary", "section_coverage", "limitation_codes"
                )}
                if _normalized(original_candidate) != candidate:
                    malformed += 1
                evidence_state = {"evidence_summary": candidate["evidence_summary"], "section_coverage": candidate["section_coverage"], "limitation_codes": candidate["limitation_codes"]}
                result = {"scope_fingerprint": _digest(candidate["scope"]), "input_fingerprint": _digest(candidate["input"]), "baseline_snapshot_id": candidate["baseline_snapshot_id"], "baseline_fingerprint": candidate["baseline_fingerprint"], "statement_fingerprint": _digest(candidate["statement_manifest"]), "evidence_state_fingerprint": _digest(evidence_state), "contract_version": candidate["contract_version"], "comparison_rule_version": candidate["comparison_rule_version"]}
                overall = _digest(result)
                if any(row[key] != value for key, value in result.items()) or row["result_fingerprint"] != overall:
                    malformed += 1
                if json.loads(row["scope_json"]) != candidate["scope"] or json.loads(row["statement_manifest_json"]) != candidate["statement_manifest"] or json.loads(row["evidence_summary_json"]) != candidate["evidence_summary"] or json.loads(row["section_coverage_json"]) != candidate["section_coverage"] or json.loads(row["limitation_codes_json"]) != candidate["limitation_codes"]:
                    malformed += 1
                if any(row[key] != candidate[key] for key in ("execution_id", "contract_version", "comparison_rule_version", "generated_at", "week_key", "baseline_snapshot_id")):
                    malformed += 1
                if row["status"] == "confirmed" and (not row["snapshot_id"] or not row["confirmed_at"] or not row["confirmation_token_hash"]):
                    malformed += 1
                if row["status"] != "confirmed" and (row["snapshot_id"] or row["confirmed_at"]):
                    malformed += 1
                if row["baseline_snapshot_id"]:
                    baseline = database.execute("SELECT scope_fingerprint,comparison_rule_version,contract_version,status,structural_status,result_fingerprint FROM weekly_brief_snapshot_operations WHERE snapshot_id=?", [row["baseline_snapshot_id"]]).fetchone()
                    if not baseline or tuple(baseline) != (row["scope_fingerprint"], row["comparison_rule_version"], row["contract_version"], "confirmed", "complete", row["baseline_fingerprint"]):
                        malformed += 1
            except (KeyError, TypeError, ValueError, json.JSONDecodeError):
                malformed += 1
    return {"state": "passed" if integrity == ["ok"] and not foreign_keys and not malformed else "failed",
            "sqlite_integrity": "ok" if integrity == ["ok"] else "failed",
            "foreign_key_violations": len(foreign_keys), "invalid_snapshot_rows": malformed}
