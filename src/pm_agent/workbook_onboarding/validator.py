"""Workbook validation for Team/Project + Capacity onboarding."""

from __future__ import annotations

from datetime import date

from pm_agent.workbook_onboarding.models import (
    ParsedWorkbook,
    ValidatedAllocation,
    ValidatedCapacityRow,
    ValidatedMember,
    ValidatedProject,
    ValidatedSetup,
    ValidatedWorkbook,
    ValidationIssue,
    WorkbookValidationResult,
)


def validate_workbook(parsed: ParsedWorkbook) -> WorkbookValidationResult:
    blockers: list[ValidationIssue] = []
    warnings: list[ValidationIssue] = []

    setup = _validate_setup(parsed, blockers, warnings)
    members = _validate_members(parsed, blockers, warnings)
    projects = _validate_projects(parsed, blockers, warnings)
    allocations = _validate_allocations(parsed, setup, members, projects, blockers, warnings)
    capacity_rows = _validate_capacity(parsed, setup, members, blockers, warnings)

    if setup and members and projects:
        _warn_inactive_allocations(members, allocations, warnings)
        _warn_missing_capacity_coverage(setup, members, capacity_rows, warnings)
        _validate_member_effective_ranges(setup, members, allocations, capacity_rows, blockers)

    if blockers or setup is None:
        return WorkbookValidationResult(
            workbook=None,
            blockers=blockers,
            warnings=warnings,
        )
    return WorkbookValidationResult(
        workbook=ValidatedWorkbook(
            setup=setup,
            members=members,
            projects=projects,
            allocations=allocations,
            capacity_rows=capacity_rows,
        ),
        blockers=blockers,
        warnings=warnings,
    )


def _validate_setup(
    parsed: ParsedWorkbook,
    blockers: list[ValidationIssue],
    warnings: list[ValidationIssue],
) -> ValidatedSetup | None:
    if not parsed.setup_rows:
        blockers.append(
            ValidationIssue(
                "blocker",
                "WORKBOOK_SETUP_ROW_REQUIRED",
                "Setup sheet must contain exactly one data row.",
                "Setup",
            )
        )
        return None
    if len(parsed.setup_rows) != 1:
        blockers.append(
            ValidationIssue(
                "blocker",
                "WORKBOOK_SETUP_ROW_COUNT_INVALID",
                "Setup sheet must contain exactly one data row.",
                "Setup",
            )
        )
        return None
    row = parsed.setup_rows[0]
    if not row.plan_version_name:
        blockers.append(_issue("blocker", "WORKBOOK_PLAN_VERSION_NAME_REQUIRED", row.row_number, "Setup", "plan_version_name is required."))
    start = _parse_month(row.start_month, blockers, "Setup", row.row_number, "start_month")
    end = _parse_month(row.end_month, blockers, "Setup", row.row_number, "end_month")
    if row.as_of_date is None:
        warnings.append(_issue("warning", "WORKBOOK_AS_OF_DATE_DEFAULTED", row.row_number, "Setup", "as_of_date is empty and will default to the import date."))
    else:
        _parse_date(row.as_of_date, blockers, "Setup", row.row_number, "as_of_date")
    if start is None or end is None or row.plan_version_name is None:
        return None
    if end < start:
        blockers.append(
            _issue(
                "blocker",
                "WORKBOOK_MONTH_RANGE_INVALID",
                row.row_number,
                "Setup",
                "end_month must not precede start_month.",
            )
        )
        return None
    return ValidatedSetup(
        plan_version_name=row.plan_version_name,
        as_of_date=row.as_of_date,
        start_month=row.start_month or "",
        end_month=row.end_month or "",
        covered_months=_month_range(start, end),
    )


def _validate_members(
    parsed: ParsedWorkbook,
    blockers: list[ValidationIssue],
    warnings: list[ValidationIssue],
) -> list[ValidatedMember]:
    results: list[ValidatedMember] = []
    seen: set[str] = set()
    for row in parsed.members:
        location = ("Members", row.row_number)
        if not row.member_key:
            blockers.append(_issue("blocker", "WORKBOOK_MEMBER_KEY_REQUIRED", row.row_number, "Members", "member_key is required."))
            continue
        if row.member_key in seen:
            blockers.append(_issue("blocker", "WORKBOOK_MEMBER_KEY_DUPLICATE", row.row_number, "Members", "member_key must be unique."))
            continue
        seen.add(row.member_key)
        if not row.display_name:
            blockers.append(_issue("blocker", "WORKBOOK_MEMBER_DISPLAY_NAME_REQUIRED", row.row_number, "Members", "display_name is required."))
            continue
        if row.fte_type not in {"LTFTE", "STFTE"}:
            blockers.append(_issue("blocker", "WORKBOOK_MEMBER_FTE_TYPE_INVALID", row.row_number, "Members", "fte_type must be LTFTE or STFTE."))
            continue
        if row.status not in {"active", "inactive"}:
            blockers.append(_issue("blocker", "WORKBOOK_MEMBER_STATUS_INVALID", row.row_number, "Members", "status must be active or inactive."))
            continue
        if row.level is not None and not 5 <= row.level <= 10:
            blockers.append(_issue("blocker", "WORKBOOK_MEMBER_LEVEL_INVALID", row.row_number, "Members", "level must be between 5 and 10 when provided."))
            continue
        if row.effective_start is None:
            warnings.append(_issue("warning", "WORKBOOK_MEMBER_EFFECTIVE_START_DEFAULTED", row.row_number, "Members", "effective_start is empty and will be derived by the adapter."))
        else:
            _parse_date(row.effective_start, blockers, *location, "effective_start")
            if row.effective_start[8:] != "01":
                blockers.append(_issue("blocker", "WORKBOOK_MEMBER_EFFECTIVE_START_NOT_MONTH_BOUNDARY", row.row_number, "Members", "effective_start must be the first day of a month."))
                continue
        if row.effective_end is not None:
            _parse_date(row.effective_end, blockers, *location, "effective_end")
            if row.effective_end != _last_day_of_month(row.effective_end[:7]):
                blockers.append(_issue("blocker", "WORKBOOK_MEMBER_EFFECTIVE_END_NOT_MONTH_BOUNDARY", row.row_number, "Members", "effective_end must be the last day of a month."))
                continue
        if row.effective_start and row.effective_end and row.effective_end < row.effective_start:
            blockers.append(_issue("blocker", "WORKBOOK_MEMBER_EFFECTIVE_RANGE_INVALID", row.row_number, "Members", "effective_end must not precede effective_start."))
            continue
        if row.fte_type == "STFTE" and (not row.current_hiref_id or not row.hiref_end_date):
            blockers.append(_issue("blocker", "WORKBOOK_MEMBER_STFTE_HIREF_REQUIRED", row.row_number, "Members", "STFTE rows require current_hiref_id and hiref_end_date."))
            continue
        if bool(row.current_hiref_id) != bool(row.hiref_end_date):
            blockers.append(_issue("blocker", "WORKBOOK_MEMBER_HIREF_FIELDS_INCOMPLETE", row.row_number, "Members", "current_hiref_id and hiref_end_date must be provided together."))
            continue
        if row.hiref_end_date is not None:
            _parse_date(row.hiref_end_date, blockers, *location, "hiref_end_date")
        results.append(
            ValidatedMember(
                row_number=row.row_number,
                member_key=row.member_key,
                display_name=row.display_name,
                fte_type=row.fte_type,
                status=row.status,
                current_hiref_id=row.current_hiref_id,
                hiref_end_date=row.hiref_end_date,
                role=row.role,
                level=row.level,
                effective_start=row.effective_start,
                effective_end=row.effective_end,
            )
        )
    if not results:
        blockers.append(
            ValidationIssue(
                "blocker",
                "WORKBOOK_MEMBERS_EMPTY",
                "Members sheet must contain at least one valid member row.",
                "Members",
            )
        )
    return results


def _validate_projects(
    parsed: ParsedWorkbook,
    blockers: list[ValidationIssue],
    warnings: list[ValidationIssue],
) -> list[ValidatedProject]:
    results: list[ValidatedProject] = []
    seen: set[str] = set()
    for row in parsed.projects:
        if not row.project_key:
            blockers.append(_issue("blocker", "WORKBOOK_PROJECT_KEY_REQUIRED", row.row_number, "Projects", "project_key is required."))
            continue
        if row.project_key in seen:
            blockers.append(_issue("blocker", "WORKBOOK_PROJECT_KEY_DUPLICATE", row.row_number, "Projects", "project_key must be unique."))
            continue
        seen.add(row.project_key)
        if not row.display_name:
            blockers.append(_issue("blocker", "WORKBOOK_PROJECT_DISPLAY_NAME_REQUIRED", row.row_number, "Projects", "display_name is required."))
            continue
        if row.status not in {"planning", "active", "done"}:
            blockers.append(_issue("blocker", "WORKBOOK_PROJECT_STATUS_INVALID", row.row_number, "Projects", "status must be planning, active, or done."))
            continue
        if row.priority is None or not 1 <= row.priority <= 5:
            blockers.append(_issue("blocker", "WORKBOOK_PROJECT_PRIORITY_INVALID", row.row_number, "Projects", "priority must be an integer between 1 and 5."))
            continue
        if row.start_date is None or row.target_end is None:
            warnings.append(_issue("warning", "WORKBOOK_PROJECT_DATE_MISSING", row.row_number, "Projects", "project date fields are optional but missing values reduce planning context."))
        if row.start_date is not None:
            _parse_date(row.start_date, blockers, "Projects", row.row_number, "start_date")
        if row.target_end is not None:
            _parse_date(row.target_end, blockers, "Projects", row.row_number, "target_end")
        if row.start_date and row.target_end and row.target_end < row.start_date:
            blockers.append(_issue("blocker", "WORKBOOK_PROJECT_DATE_RANGE_INVALID", row.row_number, "Projects", "target_end must not precede start_date."))
            continue
        results.append(
            ValidatedProject(
                row_number=row.row_number,
                project_key=row.project_key,
                display_name=row.display_name,
                status=row.status,
                priority=row.priority,
                start_date=row.start_date,
                target_end=row.target_end,
            )
        )
    if not results:
        blockers.append(
            ValidationIssue(
                "blocker",
                "WORKBOOK_PROJECTS_EMPTY",
                "Projects sheet must contain at least one valid project row.",
                "Projects",
            )
        )
    return results


def _validate_allocations(
    parsed: ParsedWorkbook,
    setup: ValidatedSetup | None,
    members: list[ValidatedMember],
    projects: list[ValidatedProject],
    blockers: list[ValidationIssue],
    warnings: list[ValidationIssue],
) -> list[ValidatedAllocation]:
    del warnings
    results: list[ValidatedAllocation] = []
    member_keys = {member.member_key for member in members}
    project_keys = {project.project_key for project in projects}
    seen: set[tuple[str, str, str]] = set()
    covered = {month for month in setup.covered_months} if setup else set()
    for row in parsed.allocations:
        if not row.member_key or not row.project_key or not row.month or row.allocation is None:
            blockers.append(_issue("blocker", "WORKBOOK_ALLOCATION_FIELDS_REQUIRED", row.row_number, "Allocations", "member_key, project_key, month, and allocation are required."))
            continue
        month = _parse_month(row.month, blockers, "Allocations", row.row_number, "month")
        if month is None:
            continue
        if setup and month not in covered:
            blockers.append(_issue("blocker", "WORKBOOK_ALLOCATION_MONTH_OUT_OF_RANGE", row.row_number, "Allocations", "allocation month is outside the Setup month range."))
            continue
        if not 0.0 <= row.allocation <= 1.0:
            blockers.append(_issue("blocker", "WORKBOOK_ALLOCATION_RANGE_INVALID", row.row_number, "Allocations", "allocation must be between 0 and 1."))
            continue
        if row.member_key not in member_keys:
            blockers.append(_issue("blocker", "WORKBOOK_ALLOCATION_MEMBER_NOT_FOUND", row.row_number, "Allocations", "allocation references a missing member_key."))
            continue
        if row.project_key not in project_keys:
            blockers.append(_issue("blocker", "WORKBOOK_ALLOCATION_PROJECT_NOT_FOUND", row.row_number, "Allocations", "allocation references a missing project_key."))
            continue
        key = (row.member_key, row.project_key, row.month)
        if key in seen:
            blockers.append(_issue("blocker", "WORKBOOK_ALLOCATION_DUPLICATE", row.row_number, "Allocations", "member_key + project_key + month must be unique."))
            continue
        seen.add(key)
        results.append(
            ValidatedAllocation(
                row_number=row.row_number,
                member_key=row.member_key,
                project_key=row.project_key,
                month=row.month,
                year=month[0],
                month_number=month[1],
                allocation=row.allocation,
            )
        )
    return results


def _validate_capacity(
    parsed: ParsedWorkbook,
    setup: ValidatedSetup | None,
    members: list[ValidatedMember],
    blockers: list[ValidationIssue],
    warnings: list[ValidationIssue],
) -> list[ValidatedCapacityRow]:
    del warnings
    results: list[ValidatedCapacityRow] = []
    member_keys = {member.member_key for member in members}
    seen: set[tuple[str, str]] = set()
    covered = {month for month in setup.covered_months} if setup else set()
    for row in parsed.capacity_rows:
        if (
            not row.member_key
            or not row.month
            or row.leave_fraction is None
            or row.bau_fraction is None
            or row.non_project_fraction is None
        ):
            blockers.append(_issue("blocker", "WORKBOOK_CAPACITY_FIELDS_REQUIRED", row.row_number, "Capacity", "member_key, month, leave_fraction, bau_fraction, and non_project_fraction are required."))
            continue
        month = _parse_month(row.month, blockers, "Capacity", row.row_number, "month")
        if month is None:
            continue
        if setup and month not in covered:
            blockers.append(_issue("blocker", "WORKBOOK_CAPACITY_MONTH_OUT_OF_RANGE", row.row_number, "Capacity", "capacity month is outside the Setup month range."))
            continue
        if row.member_key not in member_keys:
            blockers.append(_issue("blocker", "WORKBOOK_CAPACITY_MEMBER_NOT_FOUND", row.row_number, "Capacity", "capacity row references a missing member_key."))
            continue
        fractions = (row.leave_fraction, row.bau_fraction, row.non_project_fraction)
        if any(value < 0.0 or value > 1.0 for value in fractions):
            blockers.append(_issue("blocker", "WORKBOOK_CAPACITY_RANGE_INVALID", row.row_number, "Capacity", "capacity fractions must be between 0 and 1."))
            continue
        if sum(fractions) > 1.0 + 1e-9:
            blockers.append(_issue("blocker", "WORKBOOK_CAPACITY_TOTAL_EXCEEDS_ONE", row.row_number, "Capacity", "leave_fraction + bau_fraction + non_project_fraction must not exceed 1.0."))
            continue
        key = (row.member_key, row.month)
        if key in seen:
            blockers.append(_issue("blocker", "WORKBOOK_CAPACITY_DUPLICATE", row.row_number, "Capacity", "member_key + month must be unique in Capacity."))
            continue
        seen.add(key)
        results.append(
            ValidatedCapacityRow(
                row_number=row.row_number,
                member_key=row.member_key,
                month=row.month,
                year=month[0],
                month_number=month[1],
                leave_fraction=row.leave_fraction,
                bau_fraction=row.bau_fraction,
                non_project_fraction=row.non_project_fraction,
            )
        )
    return results


def _warn_inactive_allocations(
    members: list[ValidatedMember],
    allocations: list[ValidatedAllocation],
    warnings: list[ValidationIssue],
) -> None:
    inactive = {member.member_key for member in members if member.status == "inactive"}
    for allocation in allocations:
        if allocation.member_key in inactive and allocation.allocation > 0:
            warnings.append(
                _issue(
                    "warning",
                    "WORKBOOK_INACTIVE_MEMBER_ALLOCATION",
                    allocation.row_number,
                    "Allocations",
                    "inactive member still has a non-zero allocation.",
                )
            )


def _warn_missing_capacity_coverage(
    setup: ValidatedSetup,
    members: list[ValidatedMember],
    capacity_rows: list[ValidatedCapacityRow],
    warnings: list[ValidationIssue],
) -> None:
    if not capacity_rows:
        return
    covered = {(row.member_key, row.month) for row in capacity_rows}
    for member in members:
        for year, month in setup.covered_months:
            month_text = f"{year:04d}-{month:02d}"
            if (member.member_key, month_text) not in covered:
                warnings.append(
                    ValidationIssue(
                        "warning",
                        "WORKBOOK_CAPACITY_ROW_MISSING",
                        "member-month has no Capacity row and will remain unknown/no coverage.",
                        f"Capacity:{member.member_key}:{month_text}",
                    )
                )


def _validate_member_effective_ranges(
    setup: ValidatedSetup,
    members: list[ValidatedMember],
    allocations: list[ValidatedAllocation],
    capacity_rows: list[ValidatedCapacityRow],
    blockers: list[ValidationIssue],
) -> None:
    allocation_months: dict[str, set[str]] = {}
    for item in allocations:
        allocation_months.setdefault(item.member_key, set()).add(item.month)
    capacity_months: dict[str, set[str]] = {}
    for item in capacity_rows:
        capacity_months.setdefault(item.member_key, set()).add(item.month)
    for member in members:
        if member.effective_start is None and member.effective_end is None:
            continue
        start = member.effective_start or f"{setup.start_month}-01"
        end = member.effective_end or _last_day_of_month(setup.end_month)
        for month in sorted(allocation_months.get(member.member_key, set()) | capacity_months.get(member.member_key, set())):
            month_start = f"{month}-01"
            month_end = _last_day_of_month(month)
            if month_start < start or month_end > end:
                blockers.append(
                    ValidationIssue(
                        "blocker",
                        "WORKBOOK_MEMBER_EFFECTIVE_RANGE_CONFLICT",
                        "allocation/capacity month falls outside the member effective range.",
                        f"Members!{member.row_number}:{member.member_key}:{month}",
                    )
                )


def _parse_month(
    value: str | None,
    blockers: list[ValidationIssue],
    sheet: str,
    row_number: int,
    field: str,
) -> tuple[int, int] | None:
    if value is None:
        blockers.append(_issue("blocker", "WORKBOOK_MONTH_REQUIRED", row_number, sheet, f"{field} is required."))
        return None
    try:
        year_text, month_text = value.split("-")
        year, month = int(year_text), int(month_text)
    except (ValueError, AttributeError):
        blockers.append(_issue("blocker", "WORKBOOK_MONTH_INVALID", row_number, sheet, f"{field} must use YYYY-MM."))
        return None
    if not 2000 <= year <= 2100 or not 1 <= month <= 12:
        blockers.append(_issue("blocker", "WORKBOOK_MONTH_INVALID", row_number, sheet, f"{field} must use YYYY-MM."))
        return None
    if value != f"{year:04d}-{month:02d}":
        blockers.append(_issue("blocker", "WORKBOOK_MONTH_INVALID", row_number, sheet, f"{field} must use YYYY-MM."))
        return None
    return year, month


def _parse_date(
    value: str | None,
    blockers: list[ValidationIssue],
    sheet: str,
    row_number: int,
    field: str,
) -> date | None:
    if value is None:
        return None
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        blockers.append(_issue("blocker", "WORKBOOK_DATE_INVALID", row_number, sheet, f"{field} must use YYYY-MM-DD."))
        return None
    if value != parsed.isoformat():
        blockers.append(_issue("blocker", "WORKBOOK_DATE_INVALID", row_number, sheet, f"{field} must use YYYY-MM-DD."))
        return None
    return parsed


def _month_range(start: tuple[int, int], end: tuple[int, int]) -> list[tuple[int, int]]:
    result: list[tuple[int, int]] = []
    year, month = start
    while (year, month) <= end:
        result.append((year, month))
        month += 1
        if month == 13:
            year += 1
            month = 1
    return result


def _last_day_of_month(month_text: str) -> str:
    year, month = map(int, month_text.split("-"))
    if month == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month + 1, 1)
    return date.fromordinal(next_month.toordinal() - 1).isoformat()


def _issue(
    severity: str,
    code: str,
    row_number: int,
    sheet: str,
    message: str,
) -> ValidationIssue:
    return ValidationIssue(severity, code, message, f"{sheet}!{row_number}")
