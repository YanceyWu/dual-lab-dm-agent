from __future__ import annotations

import sqlite3
from pathlib import Path

from pm_agent.contract_coverage import service


def publish_contract_coverage_from_legacy(
    db_path: Path,
    *,
    package_id: str = "package-test-contract-coverage-r1",
) -> dict:
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        members = []
        for row in connection.execute(
            """
            SELECT e.id,e.name,e.status,e.resource_type,e.current_hiref,
                   COALESCE(h.end_date, e.billing_end_date) AS current_hiref_end_date
            FROM employees e
            LEFT JOIN hiref h ON h.id = e.current_hiref
            WHERE e.status='active'
            ORDER BY e.id
            """
        ).fetchall():
            current_hiref_id = str(row["current_hiref"] or "") or None
            hiref_end_date = str(row["current_hiref_end_date"] or "") or None
            if not current_hiref_id or not hiref_end_date:
                current_hiref_id = None
                hiref_end_date = None
            members.append(
                {
                    "member_id": str(row["id"]),
                    "display_name": str(row["name"]),
                    "status": "active" if str(row["status"]) == "active" else "inactive",
                    "resource_type": str(row["resource_type"] or ""),
                    "current_hiref_id": current_hiref_id,
                    "hiref_end_date": hiref_end_date,
                }
            )

    member_ids = [member["member_id"] for member in members]
    stfte_member_ids = sorted(
        member["member_id"] for member in members if member["resource_type"] == "STFTE"
    )
    ltfte_member_ids = sorted(
        member["member_id"] for member in members if member["resource_type"] == "LTFTE"
    )
    contract_member_ids = sorted(
        member["member_id"]
        for member in members
        if member["current_hiref_id"] and member["hiref_end_date"]
    )
    unknown_resource_type_member_ids = sorted(
        member["member_id"] for member in members if member["resource_type"] == ""
    )
    package = {
        "dataset_marker": "TEST_CONTRACT_COVERAGE",
        "package_id": package_id,
        "schema_version": service.PACKAGE_SCHEMA_VERSION,
        "generated_at": "2026-08-15T00:00:00+00:00",
        "source_id": "source-test-contract-coverage",
        "publication_scope": {
            "scope_key": "test-contract-coverage",
            "as_of_date": "2026-08-15",
        },
        "manifest": {
            "member_ids": member_ids,
            "stfte_member_ids": stfte_member_ids,
            "ltfte_member_ids": ltfte_member_ids,
            "contract_member_ids": contract_member_ids,
            "unknown_resource_type_member_ids": unknown_resource_type_member_ids,
        },
        "members": members,
    }
    preview = service.preview_import(package, db_path=db_path)
    return service.confirm_import(preview["session_id"], db_path=db_path)
