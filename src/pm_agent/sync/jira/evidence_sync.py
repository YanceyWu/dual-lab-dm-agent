"""Bounded read-only Jira acquisition for Phase 3 B1 source evidence."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import json
import sqlite3
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests

from pm_agent.config import settings
from pm_agent.database import source_evidence


@dataclass(frozen=True)
class JiraEvidenceConfig:
    source_id: str
    board_id: str
    base_jql: str
    field_mappings: dict[str, str]
    bootstrap_days: int = 90
    overlap_seconds: int = 300
    page_size: int = 100
    max_pages: int = 100
    max_issues: int = 5000
    supported_link_types: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.source_id.strip() or not self.board_id.strip() or not self.base_jql.strip():
            raise ValueError("source_id, board_id, and base_jql are required")
        if not 1 <= self.bootstrap_days <= 3650:
            raise ValueError("bootstrap_days must be between 1 and 3650")
        if not 0 <= self.overlap_seconds <= 86400:
            raise ValueError("overlap_seconds must be between 0 and 86400")
        if not 1 <= self.page_size <= 100:
            raise ValueError("page_size must be between 1 and 100")
        if not 1 <= self.max_pages <= 1000:
            raise ValueError("max_pages must be between 1 and 1000")
        if not 1 <= self.max_issues <= 50000:
            raise ValueError("max_issues must be between 1 and 50000")
        allowed = source_evidence.NORMALIZED_FIELD_KEYS - {
            "issue_observed",
            "tombstone",
        }
        invalid = set(self.field_mappings.values()) - allowed
        if invalid:
            raise ValueError(f"Unsupported normalized field mapping(s): {sorted(invalid)}")
        if not all(
            isinstance(key, str)
            and key.strip()
            and isinstance(value, str)
            and value.strip()
            for key, value in self.field_mappings.items()
        ):
            raise ValueError("field_mappings must contain non-empty string keys and values")


@dataclass
class AcquisitionResult:
    coverage_status: str
    pages_received: int = 0
    pages_expected: int | None = None
    issue_events: list[source_evidence.IssueEvent] = field(default_factory=list)
    issue_links: list[source_evidence.IssueLink] = field(default_factory=list)
    manifest_refs: set[str] = field(default_factory=set)
    cursor_time: str = ""
    cursor_ref: str = ""
    field_coverage: dict[str, Any] = field(default_factory=dict)
    warning_codes: list[str] = field(default_factory=list)
    error_code: str = ""
    rows_rejected: int = 0


def load_evidence_config(
    board_id: str,
    *,
    db_path: str | Path | None = None,
) -> JiraEvidenceConfig:
    """Load bounded connector-local evidence settings without inspecting credentials."""
    path = Path(db_path or settings.database_path)
    with sqlite3.connect(path) as connection:
        row = connection.execute(
            """
            SELECT bc.base_jql, ds.id, ds.config_json
            FROM jira_board_configs bc
            JOIN data_sources ds ON ds.id = 'jira-evidence-' || bc.id
            WHERE bc.id = ? AND bc.active = 1 AND ds.active = 1
            """,
            [board_id],
        ).fetchone()
    if not row:
        raise ValueError(f"Active Jira evidence source not found for board: {board_id}")
    try:
        raw_config = json.loads(row[2] or "{}")
    except json.JSONDecodeError as exc:
        raise ValueError("Jira evidence source config_json is invalid") from exc
    if not isinstance(raw_config, dict):
        raise ValueError("Jira evidence source configuration must be an object")
    field_mappings = raw_config.get("field_mappings", {})
    supported_link_types = raw_config.get("supported_link_types", [])
    if not isinstance(field_mappings, dict) or not isinstance(supported_link_types, list):
        raise ValueError("Jira evidence field/link mappings are invalid")
    return JiraEvidenceConfig(
        source_id=row[1],
        board_id=board_id,
        base_jql=row[0],
        field_mappings=field_mappings,
        bootstrap_days=raw_config.get("bootstrap_days", 90),
        overlap_seconds=raw_config.get("overlap_seconds", 300),
        page_size=raw_config.get("page_size", 100),
        max_pages=raw_config.get("max_pages", 100),
        max_issues=raw_config.get("max_issues", 5000),
        supported_link_types=tuple(supported_link_types),
    )


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_timestamp(value: str) -> datetime:
    normalized = value.strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _incremental_jql(config: JiraEvidenceConfig, cursor: dict | None) -> str:
    if cursor and cursor.get("cursor_time"):
        start = _parse_timestamp(str(cursor["cursor_time"])) - timedelta(
            seconds=config.overlap_seconds
        )
        boundary = start.strftime("%Y-%m-%d %H:%M")
        return f"({config.base_jql}) AND updated >= \"{boundary}\" ORDER BY updated ASC, key ASC"
    return (
        f"({config.base_jql}) AND updated >= -{config.bootstrap_days}d "
        "ORDER BY updated ASC, key ASC"
    )


def _safe_response_json(response: requests.Response) -> dict | None:
    if response.status_code != 200:
        return None
    try:
        payload = response.json()
    except (TypeError, ValueError):
        return None
    return payload if isinstance(payload, dict) else None


def _normalized_current_value(normalized_field: str, value: object) -> object:
    if value is None:
        return ""
    if normalized_field == "fix_versions":
        if not isinstance(value, list):
            raise ValueError("fix_versions must be a list")
        identifiers = []
        for item in value:
            if not isinstance(item, dict) or not isinstance(item.get("id"), str):
                raise ValueError("fix_versions entries require stable source IDs")
            identifiers.append(item["id"])
        return sorted(set(identifiers))
    if normalized_field in {"status", "status_category", "sprint"}:
        if isinstance(value, dict):
            identifier = value.get("id") or value.get("key")
            if not isinstance(identifier, str) or not identifier:
                raise ValueError(f"{normalized_field} requires a stable source ID")
            return identifier
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, list) and all(
        item is None or isinstance(item, (str, int, float, bool)) for item in value
    ):
        return value
    raise ValueError(f"{normalized_field} contains unsupported source structure")


def _search_issues(
    session: requests.Session,
    base_url: str,
    config: JiraEvidenceConfig,
    cursor: dict | None,
    *,
    fields: list[str],
) -> tuple[list[dict], int, list[str], str]:
    issues: list[dict] = []
    next_page_token = ""
    pages_received = 0
    warnings: list[str] = []
    for _ in range(config.max_pages):
        body: dict[str, Any] = {
            "jql": _incremental_jql(config, cursor),
            "maxResults": config.page_size,
            "fields": fields,
        }
        if next_page_token:
            body["nextPageToken"] = next_page_token
        try:
            response = session.post(
                f"{base_url.rstrip('/')}/rest/api/3/search/jql",
                json=body,
                timeout=30,
            )
        except requests.RequestException:
            return (
                issues,
                pages_received,
                warnings + ["JIRA_SEARCH_FAILED"],
                "JIRA_SEARCH_FAILED",
            )
        payload = _safe_response_json(response)
        if payload is None:
            return issues, pages_received, warnings + ["JIRA_SEARCH_FAILED"], "JIRA_SEARCH_FAILED"
        page_issues = payload.get("issues")
        if not isinstance(page_issues, list):
            return issues, pages_received, warnings + ["MALFORMED_SEARCH_PAGE"], "MALFORMED_PAGE"
        pages_received += 1
        issues.extend(item for item in page_issues if isinstance(item, dict))
        if len(issues) > config.max_issues:
            return (
                issues[: config.max_issues],
                pages_received,
                warnings + ["ISSUE_LIMIT_REACHED"],
                "BOUNDED_LIMIT_REACHED",
            )
        if payload.get("isLast") is True:
            return issues, pages_received, warnings, ""
        next_page_token = payload.get("nextPageToken")
        if not isinstance(next_page_token, str) or not next_page_token:
            return (
                issues,
                pages_received,
                warnings + ["MISSING_NEXT_PAGE_TOKEN"],
                "PARTIAL_PAGINATION",
            )
    return issues, pages_received, warnings + ["PAGE_LIMIT_REACHED"], "BOUNDED_LIMIT_REACHED"


def acquire_issue_links(
    session: requests.Session,
    base_url: str,
    config: JiraEvidenceConfig,
    cursor: dict | None,
    *,
    observed_at: str | None = None,
) -> AcquisitionResult:
    observed_at = observed_at or _utc_now().isoformat(timespec="seconds")
    issues, page_count, warnings, error_code = _search_issues(
        session,
        base_url,
        config,
        cursor,
        fields=["updated", "issuelinks"],
    )
    result = AcquisitionResult(
        coverage_status="complete" if not error_code else "partial",
        pages_received=page_count,
        pages_expected=page_count if not error_code else None,
        warning_codes=warnings,
        error_code=error_code,
        field_coverage={"updated": True, "issuelinks": not bool(error_code)},
    )
    high_water: tuple[str, str] = ("", "")
    supported = set(config.supported_link_types)
    for issue in issues:
        issue_ref = issue.get("key")
        fields = issue.get("fields")
        if not isinstance(issue_ref, str) or not issue_ref or not isinstance(fields, dict):
            result.rows_rejected += 1
            result.coverage_status = "partial"
            result.warning_codes.append("MALFORMED_ISSUE")
            continue
        updated = fields.get("updated")
        links = fields.get("issuelinks")
        if not isinstance(updated, str) or not isinstance(links, list):
            result.rows_rejected += 1
            result.coverage_status = "partial"
            result.warning_codes.append("REQUIRED_FIELD_UNAVAILABLE")
            continue
        high_water = max(high_water, (updated, issue_ref))
        for raw_link in links:
            if not isinstance(raw_link, dict):
                result.rows_rejected += 1
                result.coverage_status = "partial"
                continue
            link_ref = str(raw_link.get("id") or "")
            type_data = raw_link.get("type") or {}
            link_name = str(type_data.get("name") or "UNKNOWN")
            outward = raw_link.get("outwardIssue")
            inward = raw_link.get("inwardIssue")
            if isinstance(outward, dict) and isinstance(outward.get("key"), str):
                related = outward["key"]
                direction = "outward"
            elif isinstance(inward, dict) and isinstance(inward.get("key"), str):
                related = inward["key"]
                direction = "inward"
            else:
                result.rows_rejected += 1
                result.coverage_status = "partial"
                result.warning_codes.append("MALFORMED_ISSUE_LINK")
                continue
            state = "active" if link_name in supported else "unsupported"
            result.issue_links.append(
                source_evidence.IssueLink(
                    source_link_ref=link_ref,
                    issue_ref=issue_ref,
                    related_issue_ref=related,
                    link_type=link_name,
                    direction=direction,
                    observation_state=state,
                    source_updated_at=updated,
                    observed_at=observed_at,
                )
            )
            if link_ref:
                result.manifest_refs.add(link_ref)
    if high_water != ("", ""):
        result.cursor_time, result.cursor_ref = high_water
    elif cursor:
        result.cursor_time = str(cursor.get("cursor_time") or "")
        result.cursor_ref = str(cursor.get("cursor_ref") or "")
    if result.coverage_status == "complete" and not result.cursor_time:
        result.cursor_time = observed_at
        result.cursor_ref = "__empty__"
    result.warning_codes = sorted(set(result.warning_codes))
    return result


def acquire_issue_history(
    session: requests.Session,
    base_url: str,
    config: JiraEvidenceConfig,
    cursor: dict | None,
    *,
    observed_at: str | None = None,
) -> AcquisitionResult:
    observed_at = observed_at or _utc_now().isoformat(timespec="seconds")
    search_fields = sorted({"updated", *config.field_mappings.keys()})
    issues, search_pages, warnings, error_code = _search_issues(
        session,
        base_url,
        config,
        cursor,
        fields=search_fields,
    )
    result = AcquisitionResult(
        coverage_status="complete" if not error_code else "partial",
        pages_received=search_pages,
        warning_codes=warnings,
        error_code=error_code,
        field_coverage={
            normalized: True for normalized in sorted(set(config.field_mappings.values()))
        },
    )
    high_water: tuple[str, str] = ("", "")
    for issue in issues:
        issue_ref = issue.get("key")
        fields = issue.get("fields")
        if not isinstance(issue_ref, str) or not issue_ref or not isinstance(fields, dict):
            result.rows_rejected += 1
            result.coverage_status = "partial"
            result.warning_codes.append("MALFORMED_ISSUE")
            continue
        updated = fields.get("updated")
        if not isinstance(updated, str) or not updated:
            result.rows_rejected += 1
            result.coverage_status = "partial"
            result.warning_codes.append("REQUIRED_FIELD_UNAVAILABLE")
            continue
        high_water = max(high_water, (updated, issue_ref))
        result.manifest_refs.add(issue_ref)
        result.issue_events.append(
            source_evidence.IssueEvent(
                issue_ref=issue_ref,
                event_type="issue_observed",
                field_key="issue_observed",
                source_updated_at=updated,
                observed_at=observed_at,
                to_value="present",
            )
        )
        for source_field, normalized_field in config.field_mappings.items():
            if source_field not in fields:
                result.coverage_status = "partial"
                result.warning_codes.append("CONFIGURED_FIELD_UNAVAILABLE")
                result.field_coverage[normalized_field] = False
                continue
            try:
                current_value = _normalized_current_value(
                    normalized_field,
                    fields.get(source_field),
                )
            except ValueError:
                result.rows_rejected += 1
                result.coverage_status = "partial"
                result.warning_codes.append("CONFIGURED_FIELD_MALFORMED")
                result.field_coverage[normalized_field] = False
                continue
            result.issue_events.append(
                source_evidence.IssueEvent(
                    issue_ref=issue_ref,
                    event_type="issue_observed",
                    field_key=normalized_field,
                    source_updated_at=updated,
                    observed_at=observed_at,
                    to_value=current_value,
                )
            )
        changelog_events, changelog_pages, changelog_error = _fetch_changelog(
            session,
            base_url,
            config,
            issue_ref,
            observed_at,
        )
        result.pages_received += changelog_pages
        result.issue_events.extend(changelog_events)
        if changelog_error:
            result.coverage_status = "partial"
            result.warning_codes.append(changelog_error)
            result.error_code = result.error_code or "PARTIAL_CHANGELOG"
    result.pages_expected = result.pages_received if result.coverage_status == "complete" else None
    if high_water != ("", ""):
        result.cursor_time, result.cursor_ref = high_water
    elif cursor:
        result.cursor_time = str(cursor.get("cursor_time") or "")
        result.cursor_ref = str(cursor.get("cursor_ref") or "")
    if result.coverage_status == "complete" and not result.cursor_time:
        result.cursor_time = observed_at
        result.cursor_ref = "__empty__"
    result.warning_codes = sorted(set(result.warning_codes))
    return result


def _fetch_changelog(
    session: requests.Session,
    base_url: str,
    config: JiraEvidenceConfig,
    issue_ref: str,
    observed_at: str,
) -> tuple[list[source_evidence.IssueEvent], int, str]:
    events: list[source_evidence.IssueEvent] = []
    start_at = 0
    pages = 0
    for _ in range(config.max_pages):
        try:
            response = session.get(
                f"{base_url.rstrip('/')}/rest/api/3/issue/{quote(issue_ref, safe='')}/changelog",
                params={"startAt": start_at, "maxResults": config.page_size},
                timeout=30,
            )
        except requests.RequestException:
            return events, pages, "JIRA_CHANGELOG_FAILED"
        payload = _safe_response_json(response)
        if payload is None:
            return events, pages, "JIRA_CHANGELOG_FAILED"
        histories = payload.get("values")
        total = payload.get("total")
        if not isinstance(histories, list) or not isinstance(total, int):
            return events, pages, "MALFORMED_CHANGELOG_PAGE"
        pages += 1
        for history in histories:
            if not isinstance(history, dict):
                continue
            created = history.get("created")
            event_ref = str(history.get("id") or "")
            items = history.get("items")
            if not isinstance(created, str) or not isinstance(items, list):
                continue
            for index, item in enumerate(items):
                if not isinstance(item, dict):
                    continue
                source_field = str(item.get("fieldId") or item.get("field") or "")
                normalized_field = config.field_mappings.get(source_field)
                if not normalized_field:
                    continue
                events.append(
                    source_evidence.IssueEvent(
                        issue_ref=issue_ref,
                        source_event_ref=f"{event_ref}:{index}" if event_ref else "",
                        event_type="field_changed",
                        field_key=normalized_field,
                        from_value=item.get("from", item.get("fromString")),
                        to_value=item.get("to", item.get("toString")),
                        source_updated_at=created,
                        observed_at=observed_at,
                    )
                )
        start_at += len(histories)
        if start_at >= total:
            return events, pages, ""
        if not histories:
            return events, pages, "PARTIAL_CHANGELOG_PAGINATION"
    return events, pages, "CHANGELOG_PAGE_LIMIT_REACHED"


def sync_dataset(
    session: requests.Session,
    base_url: str,
    config: JiraEvidenceConfig,
    dataset: str,
    *,
    db_path: str | None = None,
    observed_at: str | None = None,
) -> tuple[str, AcquisitionResult]:
    cursor = source_evidence.get_cursor(
        config.source_id,
        config.board_id,
        dataset,
        db_path=db_path,
    )
    run_id = source_evidence.start_run(
        config.source_id,
        config.board_id,
        dataset,
        overlap_seconds=config.overlap_seconds,
        db_path=db_path,
    )
    if dataset == "jira_issue_history":
        result = acquire_issue_history(
            session,
            base_url,
            config,
            cursor,
            observed_at=observed_at,
        )
        source_evidence.stage_issue_events(
            run_id,
            result.issue_events,
            manifest_issue_refs=result.manifest_refs,
            db_path=db_path,
        )
    elif dataset == "jira_issue_links":
        result = acquire_issue_links(
            session,
            base_url,
            config,
            cursor,
            observed_at=observed_at,
        )
        source_evidence.stage_issue_links(
            run_id,
            result.issue_links,
            manifest_link_refs=result.manifest_refs,
            db_path=db_path,
        )
    else:
        raise ValueError(f"Unsupported evidence dataset: {dataset}")
    source_evidence.finish_staging(
        run_id,
        coverage_status=result.coverage_status,
        pages_received=result.pages_received,
        pages_expected=result.pages_expected,
        proposed_cursor_time=result.cursor_time,
        proposed_cursor_ref=result.cursor_ref,
        # Incremental updated-since acquisition is not an authoritative full-scope
        # manifest. A separately validated complete manifest must opt into closure
        # through the repository publication contract.
        authoritative_manifest=False,
        field_coverage=result.field_coverage,
        warning_codes=result.warning_codes,
        error_code=result.error_code,
        rows_rejected=result.rows_rejected,
        db_path=db_path,
    )
    if result.coverage_status == "complete":
        source_evidence.publish_run(run_id, db_path=db_path)
    else:
        source_evidence.reject_run(run_id, db_path=db_path)
    return run_id, result
