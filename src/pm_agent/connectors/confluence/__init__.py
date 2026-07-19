from __future__ import annotations

import json
import re
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path

from pm_agent.database.bootstrap import main as init_db
from pm_agent.config import settings
from pm_agent.connectors.base import ConnectorValidationResult
from pm_agent.connectors.shared import AtlassianAuthError, AtlassianAuthSession, get_auth_session
from pm_agent.database import repository
from pm_agent.repo_tools import bootstrap as repo_bootstrap

CONNECTOR_NAME = "confluence"
DISPLAY_NAME = "Confluence"
SOURCE_TYPE = "confluence"


def _effective_config() -> dict:
    try:
        return repo_bootstrap.build_effective_config().config.get("connectors", {}).get("confluence", {})
    except repo_bootstrap.StarterRepoError:
        return {}


def _build_auth() -> AtlassianAuthSession:
    config = _effective_config()
    base_url = (
        str(config.get("base_url") or settings.confluence_base_url or settings.jira_base_url).strip()
    )
    return get_auth_session(
        "confluence",
        base_url_hint=base_url,
        email=settings.confluence_email or settings.jira_user_email,
        api_token=settings.confluence_api_token or settings.jira_api_token,
        verify_ssl=settings.confluence_verify_ssl,
        cloud_id_hint=str(
            config.get("cloud_id")
            or settings.confluence_cloud_id
            or settings.atlassian_cloud_id
        ),
    )


def _api_get(auth: AtlassianAuthSession, path: str, params: dict | None = None) -> dict:
    response = auth.session.get(f"{auth.base_url}/wiki/rest/api{path}", params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def _api_get_v2(auth: AtlassianAuthSession, path: str, params: dict | None = None) -> dict:
    response = auth.session.get(f"{auth.base_url}/wiki/api/v2{path}", params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def search(query: str, max_results: int = 20) -> dict:
    auth = _build_auth()
    if any(op in query for op in ["=", "~", " AND ", " OR ", " NOT ", "type ="]):
        cql = query
    else:
        cql = f'text ~ "{query}" ORDER BY lastModified DESC'
    return _api_get(
        auth,
        "/content/search",
        params={"cql": cql, "limit": max_results, "expand": "version,space"},
    )


def fetch_page(page_id: str) -> dict:
    auth = _build_auth()
    return _api_get_v2(
        auth,
        f"/pages/{page_id}",
        params={"body-format": "storage", "include-version": "true"},
    )


def _storage_to_markdown(storage_value: str) -> str:
    try:
        from bs4 import BeautifulSoup
        import markdownify

        soup = BeautifulSoup(storage_value, "html.parser")
        for junk in soup.select("script, style"):
            junk.decompose()
        markdown = markdownify.markdownify(str(soup), heading_style="ATX", bullets="-")
        return re.sub(r"\n{3,}", "\n\n", markdown).strip()
    except ImportError:
        clean = re.sub(r"<[^>]+>", "", storage_value)
        return re.sub(r"\n{3,}", "\n\n", clean).strip()


def _extract_status_block(markdown: str) -> dict:
    result = {
        "rag_status": None,
        "status_as_of": None,
        "owner": None,
        "summary_text": None,
        "risks_text": None,
        "impact_text": None,
        "sprint_iteration": None,
        "milestones_text": None,
    }

    rag_match = re.search(r"Overall RAG status[:\*\s]+(.+)", markdown, re.IGNORECASE)
    if rag_match:
        rag_raw = rag_match.group(1).strip()
        if "🟢" in rag_raw or "🟩" in rag_raw or "GREEN" in rag_raw.upper():
            result["rag_status"] = "GREEN"
        elif "🔴" in rag_raw or "RED" in rag_raw.upper():
            result["rag_status"] = "RED"
        elif (
            "🟡" in rag_raw
            or "🟠" in rag_raw
            or "AMBER" in rag_raw.upper()
            or "YELLOW" in rag_raw.upper()
            or "ORANGE" in rag_raw.upper()
        ):
            result["rag_status"] = "AMBER"
        elif "pick one" not in rag_raw.lower() and rag_raw.replace(" ", "").replace("(pickone)", ""):
            result["rag_status"] = rag_raw[:30]

    status_match = re.search(r"Status as of[:\*\s]+([^\n\*]+)", markdown, re.IGNORECASE)
    if status_match:
        status_as_of = status_match.group(1).strip().strip("*").strip()
        if status_as_of and "squad" not in status_as_of.lower() and "owner" not in status_as_of.lower():
            result["status_as_of"] = status_as_of

    owner_match = re.search(r"Squad\s*/\s*Owner[:\*\s]+([^\n]+)", markdown, re.IGNORECASE)
    if owner_match:
        result["owner"] = owner_match.group(1).strip().strip("*").strip()

    sprint_match = re.search(r"Sprint\s*/\s*Iteration[:\*\s]+([^\n]+)", markdown, re.IGNORECASE)
    if sprint_match:
        sprint_iteration = sprint_match.group(1).strip()
        if sprint_iteration and sprint_iteration not in {"-", "N/A", "NA"}:
            result["sprint_iteration"] = sprint_iteration

    def _extract_section(heading: str) -> str | None:
        pattern = rf"#+\s+(?:\d+\.\s+)?{re.escape(heading)}[^\n]*\n(.*?)(?=\n#+\s|\Z)"
        match = re.search(pattern, markdown, re.IGNORECASE | re.DOTALL)
        if not match:
            return None
        text = re.sub(r"\n{3,}", "\n\n", match.group(1).strip())
        if text and text.upper() not in {"N/A", "NA", "-"}:
            return text[:2000]
        return None

    result["summary_text"] = _extract_section("Summary")
    result["risks_text"] = _extract_section("Key Risks")
    result["impact_text"] = _extract_section("Impact")
    result["milestones_text"] = _extract_section("Milestones")
    return result


def _fetch_page_v2(auth: AtlassianAuthSession, page_id: str) -> dict:
    return _api_get_v2(
        auth,
        f"/pages/{page_id}",
        params={"body-format": "storage", "include-version": "true"},
    )


def _configured_page_jobs(pages: list[tuple[str, str, str]]) -> dict[str, tuple[str, str]]:
    """Build sync work exclusively from locally configured page registry rows."""
    return {
        board_id: (page_id, title)
        for page_id, board_id, title in pages
    }


def _sync_action_tracker(
    cursor: sqlite3.Cursor,
    auth: AtlassianAuthSession,
    synced_date: str,
    page_id: str,
) -> int:
    page = _fetch_page_v2(auth, page_id)
    storage = (page.get("body", {}).get("storage") or {}).get("value", "")
    markdown = _storage_to_markdown(storage) if storage else ""

    rows: list[dict] = []
    in_table = False
    header_skipped = False
    for line in markdown.split("\n"):
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            if not header_skipped:
                if "---" in cells[0] or "Date" in cells[0] or "Item" in cells[0]:
                    header_skipped = True
                    in_table = True
                continue
            if in_table and len(cells) >= 5:
                _, item, action, assignee, due, status, *rest = (cells + [""] * 7)
                if item.strip():
                    rows.append(
                        {
                            "item": item.strip(),
                            "action_required": action.strip() or None,
                            "assignee": assignee.strip() or None,
                            "due_date": due.strip() or None,
                            "status": status.strip(),
                            "remarks": rest[0].strip() if rest else None,
                        }
                    )

    if not rows:
        return 0

    def _norm(status: str) -> str:
        lowered = status.lower()
        if "done" in lowered or "green" in lowered:
            return "Done"
        if "in progress" in lowered or "blue" in lowered or "yellow" in lowered:
            return "In Progress"
        if "blocked" in lowered or "red" in lowered:
            return "Blocked"
        if "todo" in lowered or "to do" in lowered:
            return "To Do"
        if "pending" in lowered:
            return "In Progress"
        return status.title() if status else "To Do"

    cursor.execute("DELETE FROM action_tracker WHERE synced_date = ?", (synced_date,))
    for row in rows:
        cursor.execute(
            """
            INSERT INTO action_tracker
                (page_id, item, action_required, assignee, due_date, status, remarks, synced_date)
            VALUES (?,?,?,?,?,?,?,?)
            """,
            (
                page_id,
                row["item"],
                row["action_required"],
                row["assignee"],
                row["due_date"],
                _norm(row["status"]),
                row["remarks"],
                synced_date,
            ),
        )

    last_modified = ((page.get("version") or {}).get("createdAt", ""))[:10]
    cursor.execute(
        """
        UPDATE confluence_pages
        SET last_synced=?, last_modified=?
        WHERE id=?
        """,
        (synced_date, last_modified, page_id),
    )
    return len(rows)


def sync_status_pages(db_path: str | None = None) -> dict:
    init_db(quiet=True)
    auth = _build_auth()
    target_db = Path(db_path or settings.database_path)
    today = str(date.today())

    run_id = repository.start_sync_run(
        "confluence-status-batch",
        run_type="full",
        target_tables=["confluence_pages", "confluence_status_snapshots", "action_tracker"],
        triggered_by="cli",
        notes="Triggered via repo-native Confluence connector.",
    )

    conn = sqlite3.connect(target_db)
    cursor = conn.cursor()
    stored = 0
    action_tracker_rows = 0
    rows_in = 0
    try:
        cursor.execute("SELECT id, board_id, title FROM confluence_pages WHERE board_id != 'global'")
        pages = cursor.fetchall()
        if not pages:
            raise RuntimeError("No confluence_pages configured in DB.")

        page_jobs = _configured_page_jobs(pages)

        all_ids = [job[0] for job in page_jobs.values()]
        fetched: dict[str, dict] = {}
        errors: dict[str, str] = {}
        with ThreadPoolExecutor(max_workers=min(8, len(all_ids))) as pool:
            futures = {pool.submit(_fetch_page_v2, auth, page_id): page_id for page_id in all_ids}
            for future in as_completed(futures):
                page_id = futures[future]
                try:
                    fetched[page_id] = future.result()
                except Exception as exc:
                    errors[page_id] = str(exc)
        rows_in += len(all_ids)

        for board_id, (page_id, page_title) in page_jobs.items():
            if page_id in errors:
                continue
            page = fetched.get(page_id)
            if not page:
                continue

            storage = (page.get("body", {}).get("storage") or {}).get("value", "")
            markdown = _storage_to_markdown(storage) if storage else ""
            last_modified = ((page.get("version") or {}).get("createdAt", ""))[:10]
            actual_title = page.get("title", page_title)
            fields = _extract_status_block(markdown)

            cursor.execute(
                "DELETE FROM confluence_status_snapshots WHERE board_id=? AND snapshot_date=?",
                (board_id, today),
            )
            cursor.execute(
                """
                INSERT INTO confluence_status_snapshots
                    (board_id, page_id, page_title, snapshot_date, rag_status, status_as_of,
                     owner, summary_text, risks_text, impact_text, sprint_iteration,
                     milestones_text, raw_content)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    board_id,
                    page_id,
                    actual_title,
                    today,
                    fields["rag_status"],
                    fields["status_as_of"] or last_modified,
                    fields["owner"],
                    fields["summary_text"],
                    fields["risks_text"],
                    fields["impact_text"],
                    fields["sprint_iteration"],
                    fields["milestones_text"],
                    markdown[:5000],
                ),
            )
            cursor.execute(
                """
                UPDATE confluence_pages
                SET id=?, title=?, last_modified=?, last_synced=?
                WHERE board_id=?
                """,
                (page_id, actual_title, last_modified, today, board_id),
            )
            stored += 1

        action_tracker_page_id = settings.confluence_action_tracker_page_id.strip()
        if action_tracker_page_id:
            action_tracker_rows = _sync_action_tracker(cursor, auth, today, action_tracker_page_id)
            rows_in += 1
        conn.commit()
        repository.finish_sync_run(
            run_id,
            rows_in=rows_in,
            rows_changed=stored + action_tracker_rows,
            notes=f"Confluence status sync stored {stored} project pages and {action_tracker_rows} action-tracker rows.",
        )
        return {"pages_synced": stored, "page_count": len(page_jobs), "action_tracker_rows": action_tracker_rows}
    except Exception as exc:
        conn.rollback()
        repository.fail_sync_run(
            run_id,
            str(exc),
            rows_in=rows_in,
            rows_changed=stored + action_tracker_rows,
            notes="Repo-native Confluence connector failed.",
        )
        raise
    finally:
        conn.close()


def validate_connector() -> ConnectorValidationResult:
    config = _effective_config()
    enabled = bool(config.get("enabled", False))
    auth_mode = str(config.get("auth_mode", "atlassian_oauth"))
    base_url = (
        str(config.get("base_url") or settings.confluence_base_url or settings.jira_base_url).strip()
    )

    warnings: list[str] = []
    errors: list[str] = []
    details: dict[str, str] = {
        "base_url": base_url or "-",
        "action_tracker_page_configured": (
            "yes" if settings.confluence_action_tracker_page_id.strip() else "no"
        ),
    }

    db_path = Path(settings.database_path)
    configured_pages = 0
    if db_path.exists():
        try:
            with sqlite3.connect(db_path) as conn:
                row = conn.execute(
                    "SELECT COUNT(*) FROM confluence_pages WHERE board_id != 'global'"
                ).fetchone()
                configured_pages = int(row[0] if row else 0)
        except sqlite3.OperationalError:
            warnings.append(
                "Confluence runtime tables are not initialized yet. Run `pm init` or `python scripts/init_db.py`."
            )
    details["configured_pages"] = str(configured_pages)

    if enabled and not base_url:
        errors.append("Confluence connector is enabled but no base URL is configured.")

    if enabled and base_url:
        try:
            auth = _build_auth()
            details["resolved_auth_type"] = auth.auth_type
            details["resolved_base_url"] = auth.base_url
            if auth.cloud_id:
                details["cloud_id"] = auth.cloud_id
            if auth.token_source:
                details["token_source"] = auth.token_source
        except AtlassianAuthError as exc:
            errors.append(str(exc))
        except Exception as exc:
            errors.append(f"Confluence auth probe failed: {exc}")

    if enabled and configured_pages == 0:
        warnings.append(
            "No Confluence pages are configured in `confluence_pages`; sync will have nothing to ingest."
        )

    return ConnectorValidationResult(
        name=CONNECTOR_NAME,
        display_name=DISPLAY_NAME,
        enabled=enabled,
        ready=enabled and not errors,
        auth_mode=auth_mode,
        details=details,
        warnings=warnings,
        errors=errors,
    )
