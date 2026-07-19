#!/usr/bin/env python3
# ruff: noqa: E402
"""Import Confluence page registry rows from CSV."""

from __future__ import annotations

import argparse
import csv
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from pm_agent.config import settings
from pm_agent.database.bootstrap import main as init_db


def _load_rows(file_path: Path) -> list[dict[str, str]]:
    with file_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return [dict(row) for row in reader]


def _delete_stale_pages(
    con: sqlite3.Connection,
    incoming_page_ids: list[str],
    incoming_board_ids: list[str],
) -> tuple[int, int]:
    stale_page_ids = (
        [
            row[0]
            for row in con.execute(
                f"SELECT id FROM confluence_pages WHERE board_id != 'global' AND id NOT IN ({','.join('?' for _ in incoming_page_ids)})",
                incoming_page_ids,
            ).fetchall()
        ]
        if incoming_page_ids
        else [
            row[0]
            for row in con.execute(
                "SELECT id FROM confluence_pages WHERE board_id != 'global'"
            ).fetchall()
        ]
    )
    stale_board_ids = (
        [
            row[0]
            for row in con.execute(
                f"SELECT DISTINCT board_id FROM confluence_pages WHERE board_id != 'global' AND board_id NOT IN ({','.join('?' for _ in incoming_board_ids)})",
                incoming_board_ids,
            ).fetchall()
        ]
        if incoming_board_ids
        else [
            row[0]
            for row in con.execute(
                "SELECT DISTINCT board_id FROM confluence_pages WHERE board_id != 'global'"
            ).fetchall()
        ]
    )

    if stale_page_ids:
        placeholders = ",".join("?" for _ in stale_page_ids)
        con.execute(f"DELETE FROM action_tracker WHERE page_id IN ({placeholders})", stale_page_ids)
        con.execute(f"DELETE FROM confluence_pages WHERE id IN ({placeholders})", stale_page_ids)
    if stale_board_ids:
        placeholders = ",".join("?" for _ in stale_board_ids)
        con.execute(
            f"DELETE FROM confluence_status_snapshots WHERE board_id IN ({placeholders})",
            stale_board_ids,
        )
    return len(stale_page_ids), len(stale_board_ids)


def import_confluence_pages(
    file_path: Path,
    dry_run: bool = False,
    merge_only: bool = False,
) -> None:
    init_db()
    rows = _load_rows(file_path)
    print(f"Loaded {len(rows)} Confluence page rows from {file_path}")
    incoming_page_ids = [row.get("id", "").strip() for row in rows if row.get("id", "").strip()]
    incoming_board_ids = [row.get("board_id", "").strip() for row in rows if row.get("board_id", "").strip()]
    if dry_run:
        for row in rows[:5]:
            print(
                "  DRY",
                row.get("board_id", "").strip(),
                row.get("id", "").strip(),
                row.get("page_type", "").strip() or "status_page",
            )
        if not merge_only:
            print("  DRY sync-mode: rows absent from the CSV would be removed from page registry and related snapshots.")
        return

    con = sqlite3.connect(settings.database_path)
    imported = 0
    removed_pages = 0
    removed_boards = 0
    try:
        if not merge_only:
            removed_pages, removed_boards = _delete_stale_pages(
                con,
                incoming_page_ids,
                incoming_board_ids,
            )
        for row in rows:
            page_id = row.get("id", "").strip()
            board_id = row.get("board_id", "").strip()
            if not page_id or not board_id:
                raise ValueError("Each CSV row must include id and board_id.")

            con.execute("DELETE FROM confluence_pages WHERE board_id = ? AND id <> ?", [board_id, page_id])
            con.execute(
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
                    page_id,
                    board_id,
                    row.get("title", "").strip(),
                    row.get("page_type", "").strip() or "status_page",
                    row.get("last_synced", "").strip(),
                    row.get("last_modified", "").strip(),
                    row.get("content_summary", "").strip(),
                ],
            )
            imported += 1

        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()

    print(f"Imported {imported} Confluence page registry rows.")
    if not merge_only:
        print(
            f"Removed {removed_pages} stale page row(s) and {removed_boards} stale board snapshot set(s)."
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Import Confluence page registry from CSV")
    parser.add_argument("--file", required=True, help="Path to confluence_pages CSV")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--merge-only",
        action="store_true",
        help="Only upsert rows from the CSV; do not delete pages/boards missing from the file.",
    )
    args = parser.parse_args()
    import_confluence_pages(Path(args.file), dry_run=args.dry_run, merge_only=args.merge_only)


if __name__ == "__main__":
    main()
