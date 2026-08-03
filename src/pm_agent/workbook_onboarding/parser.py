"""Workbook parsing for Team/Project + Capacity onboarding."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any

from openpyxl import load_workbook

from pm_agent.workbook_onboarding.models import (
    ParsedWorkbook,
    WorkbookAllocationRow,
    WorkbookCapacityRow,
    WorkbookMemberRow,
    WorkbookProjectRow,
    WorkbookSetupRow,
)

EXPECTED_SHEETS = ("Setup", "Members", "Projects", "Allocations", "Capacity")
EXPECTED_HEADERS = {
    "Setup": ["plan_version_name", "as_of_date", "start_month", "end_month"],
    "Members": [
        "member_key",
        "display_name",
        "fte_type",
        "status",
        "current_hiref_id",
        "hiref_end_date",
        "role",
        "level",
        "effective_start",
        "effective_end",
    ],
    "Projects": [
        "project_key",
        "display_name",
        "status",
        "priority",
        "start_date",
        "target_end",
    ],
    "Allocations": ["member_key", "project_key", "month", "allocation"],
    "Capacity": [
        "member_key",
        "month",
        "leave_fraction",
        "bau_fraction",
        "non_project_fraction",
    ],
}


class WorkbookParseError(ValueError):
    """Raised when the workbook structure does not match the locked contract."""


def parse_workbook(path: str | Path) -> ParsedWorkbook:
    workbook = load_workbook(Path(path), data_only=True)
    sheet_names = tuple(workbook.sheetnames)
    if set(sheet_names) != set(EXPECTED_SHEETS) or len(sheet_names) != len(EXPECTED_SHEETS):
        raise WorkbookParseError("WORKBOOK_SHEETS_INVALID")
    rows_by_sheet = {
        name: _read_sheet(workbook[name], expected_headers=EXPECTED_HEADERS[name])
        for name in EXPECTED_SHEETS
    }
    return ParsedWorkbook(
        setup_rows=[
            WorkbookSetupRow(
                row_number=row_number,
                plan_version_name=_as_text(values[0]),
                as_of_date=_as_date_text(values[1]),
                start_month=_as_month_text(values[2]),
                end_month=_as_month_text(values[3]),
            )
            for row_number, values in rows_by_sheet["Setup"]
        ],
        members=[
            WorkbookMemberRow(
                row_number=row_number,
                member_key=_as_text(values[0]),
                display_name=_as_text(values[1]),
                fte_type=_as_text(values[2]),
                status=_as_text(values[3]),
                current_hiref_id=_as_text(values[4]),
                hiref_end_date=_as_date_text(values[5]),
                role=_as_text(values[6]),
                level=_as_int(values[7]),
                effective_start=_as_date_text(values[8]),
                effective_end=_as_date_text(values[9]),
            )
            for row_number, values in rows_by_sheet["Members"]
        ],
        projects=[
            WorkbookProjectRow(
                row_number=row_number,
                project_key=_as_text(values[0]),
                display_name=_as_text(values[1]),
                status=_as_text(values[2]),
                priority=_as_int(values[3]),
                start_date=_as_date_text(values[4]),
                target_end=_as_date_text(values[5]),
            )
            for row_number, values in rows_by_sheet["Projects"]
        ],
        allocations=[
            WorkbookAllocationRow(
                row_number=row_number,
                member_key=_as_text(values[0]),
                project_key=_as_text(values[1]),
                month=_as_month_text(values[2]),
                allocation=_as_float(values[3]),
            )
            for row_number, values in rows_by_sheet["Allocations"]
        ],
        capacity_rows=[
            WorkbookCapacityRow(
                row_number=row_number,
                member_key=_as_text(values[0]),
                month=_as_month_text(values[1]),
                leave_fraction=_as_float(values[2]),
                bau_fraction=_as_float(values[3]),
                non_project_fraction=_as_float(values[4]),
            )
            for row_number, values in rows_by_sheet["Capacity"]
            if not _is_capacity_note_row(values)
        ],
    )


def _read_sheet(worksheet: Any, *, expected_headers: list[str]) -> list[tuple[int, list[Any]]]:
    rows = list(worksheet.iter_rows(values_only=True))
    if not rows:
        raise WorkbookParseError("WORKBOOK_HEADER_MISSING")
    header_row = list(rows[0])
    header = [_as_header_text(value) for value in header_row[: len(expected_headers)]]
    if header != expected_headers:
        raise WorkbookParseError(f"WORKBOOK_HEADERS_INVALID:{worksheet.title}")
    if any(not _is_blank(value) for value in header_row[len(expected_headers) :]):
        raise WorkbookParseError(f"WORKBOOK_HEADERS_INVALID:{worksheet.title}")
    results: list[tuple[int, list[Any]]] = []
    for row_number, values in enumerate(rows[1:], start=2):
        row_values = list(values)
        if any(not _is_blank(value) for value in row_values[len(expected_headers) :]):
            raise WorkbookParseError(
                f"WORKBOOK_ROW_WIDTH_INVALID:{worksheet.title}:{row_number}"
            )
        current = row_values[: len(expected_headers)]
        if all(_is_blank(value) for value in current):
            continue
        results.append((row_number, current))
    return results


def _is_blank(value: object) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _as_header_text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _as_text(value: object) -> str | None:
    if _is_blank(value):
        return None
    if isinstance(value, (date, datetime)):
        return value.date().isoformat() if isinstance(value, datetime) else value.isoformat()
    return str(value).strip()


def _as_date_text(value: object) -> str | None:
    if _is_blank(value):
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value).strip()


def _as_month_text(value: object) -> str | None:
    if _is_blank(value):
        return None
    if isinstance(value, datetime):
        return value.strftime("%Y-%m")
    if isinstance(value, date):
        return value.strftime("%Y-%m")
    return str(value).strip()


def _as_int(value: object) -> int | None:
    if _is_blank(value):
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return None


def _as_float(value: object) -> float | None:
    if _is_blank(value):
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).strip())
    except ValueError:
        return None


def _is_capacity_note_row(values: list[Any]) -> bool:
    first = _as_text(values[0])
    if not first or not first.lower().startswith("note:"):
        return False
    return all(_is_blank(value) for value in values[1:])
