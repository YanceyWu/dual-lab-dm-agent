from __future__ import annotations

import hashlib
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pytest

from pm_agent.database import repository
from pm_agent.database.bootstrap import (
    _migrate_allocation_integrity_v24,
    _migrate_staffing_token_hash_v24,
    main as init_db,
)


def _seed_integrity_entities(database_path) -> None:
    init_db(quiet=True)
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            INSERT INTO employees (id, wd_id, name, status)
            VALUES ('990101', '990101', 'Alex Example', 'active')
            """
        )
        connection.executemany(
            """
            INSERT INTO projects (id, name, status)
            VALUES (?, ?, 'active')
            """,
            [
                ("project-atlas-990001", "Project Atlas"),
                ("project-beacon-990002", "Project Beacon"),
            ],
        )
        connection.execute(
            """
            INSERT INTO plan_versions
                (plan_version_id, version_name, version_status)
            VALUES ('plan-2026-08', 'Synthetic Plan', 'active')
            """
        )


def test_database_rejects_invalid_and_duplicate_allocations(isolated_db) -> None:
    _seed_integrity_entities(isolated_db)

    with sqlite3.connect(isolated_db) as connection:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO monthly_allocations
                    (employee_id, project_id, year, month, allocation,
                     plan_version_id)
                VALUES ('990101', 'project-atlas-990001', 2026, 13, 0.5,
                        'plan-2026-08')
                """
            )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO monthly_allocations
                    (employee_id, project_id, year, month, allocation,
                     plan_version_id)
                VALUES ('990101', 'project-atlas-990001', 2026, 8, NULL,
                        'plan-2026-08')
                """
            )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO assignments
                    (employee_id, project_id, allocation, status)
                VALUES ('990101', 'project-atlas-990001', 1.2, 'planned')
                """
            )
        connection.execute(
            """
            INSERT INTO monthly_allocations
                (employee_id, project_id, year, month, allocation,
                 plan_version_id)
            VALUES ('990101', 'project-atlas-990001', 2026, 8, 0.5,
                    'plan-2026-08')
            """
        )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO monthly_allocations
                    (employee_id, project_id, year, month, allocation,
                     plan_version_id)
                VALUES ('990101', 'project-atlas-990001', 2026, 8, 0.2,
                        'plan-2026-08')
                """
            )


def test_staffing_confirmation_token_is_stored_only_as_hash(isolated_db) -> None:
    init_db(quiet=True)
    token = "synthetic-one-time-token"
    repository.create_staffing_proposal(
        {
            "proposal_id": "proposal-hash-test",
            "expires_at": (
                datetime.now(timezone.utc) + timedelta(minutes=10)
            ).isoformat(),
            "confirmation_token": token,
            "request": {},
            "evidence": {},
            "proposal": {},
        }
    )

    with sqlite3.connect(isolated_db) as connection:
        columns = {
            row[1] for row in connection.execute(
                "PRAGMA table_info(staffing_proposals)"
            )
        }
        stored_hash = connection.execute(
            """
            SELECT confirmation_token_hash
            FROM staffing_proposals
            WHERE proposal_id = 'proposal-hash-test'
            """
        ).fetchone()[0]

    assert "confirmation_token" not in columns
    assert stored_hash == hashlib.sha256(token.encode("utf-8")).hexdigest()
    assert token != stored_hash


def test_legacy_token_migration_removes_plaintext_and_preserves_hash(
    isolated_db,
) -> None:
    init_db(quiet=True)
    token = "legacy-synthetic-token"
    with sqlite3.connect(isolated_db) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("DROP TABLE staffing_proposals")
        connection.execute(
            """
            CREATE TABLE staffing_proposals (
                proposal_id TEXT PRIMARY KEY,
                status TEXT NOT NULL DEFAULT 'proposed',
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                confirmed_at TEXT DEFAULT '',
                confirmation_token TEXT NOT NULL UNIQUE,
                request_json TEXT NOT NULL,
                evidence_json TEXT NOT NULL DEFAULT '{}',
                proposal_json TEXT NOT NULL,
                decision_id INTEGER REFERENCES decision_log(id),
                failure_reason TEXT DEFAULT ''
            )
            """
        )
        connection.execute(
            """
            INSERT INTO staffing_proposals
                (proposal_id, created_at, expires_at, confirmation_token,
                 request_json, proposal_json)
            VALUES ('legacy-proposal', '2026-07-26T00:00:00+00:00',
                    '2026-07-26T01:00:00+00:00', ?, '{}', '{}')
            """,
            [token],
        )

        _migrate_staffing_token_hash_v24(connection)

        columns = {
            row[1] for row in connection.execute(
                "PRAGMA table_info(staffing_proposals)"
            )
        }
        stored_hash = connection.execute(
            """
            SELECT confirmation_token_hash
            FROM staffing_proposals
            WHERE proposal_id = 'legacy-proposal'
            """
        ).fetchone()[0]

    assert "confirmation_token" not in columns
    assert stored_hash == hashlib.sha256(token.encode("utf-8")).hexdigest()


def test_integrity_migration_rejects_dirty_legacy_rows_without_rewriting(
    isolated_db,
) -> None:
    _seed_integrity_entities(isolated_db)
    with sqlite3.connect(isolated_db) as connection:
        connection.execute("DROP TABLE monthly_allocations")
        connection.execute(
            """
            CREATE TABLE monthly_allocations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id TEXT NOT NULL REFERENCES employees(id),
                project_id TEXT NOT NULL REFERENCES projects(id),
                year INTEGER NOT NULL,
                month INTEGER NOT NULL,
                allocation REAL DEFAULT 0.0,
                plan_version_id TEXT DEFAULT ''
                    REFERENCES plan_versions(plan_version_id)
            )
            """
        )
        connection.execute(
            """
            INSERT INTO monthly_allocations
                (employee_id, project_id, year, month, allocation,
                 plan_version_id)
            VALUES ('990101', 'project-atlas-990001', 2026, 13, 1.2,
                    'plan-2026-08')
            """
        )

        with pytest.raises(ValueError, match="repair them before"):
            _migrate_allocation_integrity_v24(connection)

        dirty_row = connection.execute(
            "SELECT month, allocation FROM monthly_allocations"
        ).fetchone()
        replacement_exists = connection.execute(
            """
            SELECT 1 FROM sqlite_master
            WHERE type='table' AND name='monthly_allocations_v24'
            """
        ).fetchone()

    assert dirty_row == (13, 1.2)
    assert replacement_exists is None


def _proposal(
    proposal_id: str,
    token: str,
    project_id: str,
) -> dict:
    request = {
        "project_id": project_id,
        "start_period": "2026-08",
        "end_period": "2026-08",
        "role": "developer",
    }
    proposal = {
        "periods": [{"year": 2026, "month": 8}],
        "plan_version_id": "plan-2026-08",
        "selections": [{"member_id": "990101", "allocation": 0.6}],
        "candidates": [],
    }
    repository.create_staffing_proposal(
        {
            "proposal_id": proposal_id,
            "expires_at": (
                datetime.now(timezone.utc) + timedelta(minutes=10)
            ).isoformat(),
            "confirmation_token": token,
            "request": request,
            "evidence": {},
            "proposal": proposal,
        }
    )
    return proposal


def test_concurrent_proposals_cannot_overallocate_one_member_period(
    isolated_db,
) -> None:
    _seed_integrity_entities(isolated_db)
    proposals = {
        "proposal-atlas": (
            "token-atlas",
            _proposal(
                "proposal-atlas",
                "token-atlas",
                "project-atlas-990001",
            ),
        ),
        "proposal-beacon": (
            "token-beacon",
            _proposal(
                "proposal-beacon",
                "token-beacon",
                "project-beacon-990002",
            ),
        ),
    }

    def confirm(item):
        proposal_id, (token, proposal) = item
        try:
            result = repository.confirm_staffing_proposal(
                proposal_id,
                token,
                proposal,
            )
            return result["status"]
        except ValueError as exc:
            return str(exc)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(confirm, proposals.items()))

    assert results.count("confirmed") == 1
    assert results.count(
        "Confirmed allocation would exceed 1.0 for a member period"
    ) == 1
    with sqlite3.connect(isolated_db) as connection:
        total = connection.execute(
            """
            SELECT SUM(allocation)
            FROM monthly_allocations
            WHERE employee_id = '990101' AND year = 2026 AND month = 8
            """
        ).fetchone()[0]
        decisions = connection.execute(
            """
            SELECT COUNT(*) FROM decision_log
            WHERE type = 'staffing_proposal'
            """
        ).fetchone()[0]
        statuses = [
            row[0]
            for row in connection.execute(
                """
                SELECT status FROM staffing_proposals
                ORDER BY proposal_id
                """
            )
        ]

    assert total == pytest.approx(0.6)
    assert decisions == 1
    assert statuses == ["confirmed", "proposed"] or statuses == [
        "proposed",
        "confirmed",
    ]
