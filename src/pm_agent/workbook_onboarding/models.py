"""Typed workbook onboarding models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


IssueSeverity = Literal["blocker", "warning"]


@dataclass(frozen=True)
class ValidationIssue:
    severity: IssueSeverity
    code: str
    message: str
    location: str


@dataclass(frozen=True)
class WorkbookSetupRow:
    row_number: int
    plan_version_name: str | None
    as_of_date: str | None
    start_month: str | None
    end_month: str | None


@dataclass(frozen=True)
class WorkbookMemberRow:
    row_number: int
    member_key: str | None
    display_name: str | None
    fte_type: str | None
    status: str | None
    current_hiref_id: str | None
    hiref_end_date: str | None
    role: str | None
    level: int | None
    effective_start: str | None
    effective_end: str | None


@dataclass(frozen=True)
class WorkbookProjectRow:
    row_number: int
    project_key: str | None
    display_name: str | None
    status: str | None
    priority: int | None
    start_date: str | None
    target_end: str | None


@dataclass(frozen=True)
class WorkbookAllocationRow:
    row_number: int
    member_key: str | None
    project_key: str | None
    month: str | None
    allocation: float | None


@dataclass(frozen=True)
class WorkbookCapacityRow:
    row_number: int
    member_key: str | None
    month: str | None
    leave_fraction: float | None
    bau_fraction: float | None
    non_project_fraction: float | None


@dataclass(frozen=True)
class ParsedWorkbook:
    setup_rows: list[WorkbookSetupRow]
    members: list[WorkbookMemberRow]
    projects: list[WorkbookProjectRow]
    allocations: list[WorkbookAllocationRow]
    capacity_rows: list[WorkbookCapacityRow]


@dataclass(frozen=True)
class ValidatedSetup:
    plan_version_name: str
    as_of_date: str | None
    start_month: str
    end_month: str
    covered_months: list[tuple[int, int]]


@dataclass(frozen=True)
class ValidatedMember:
    row_number: int
    member_key: str
    display_name: str
    fte_type: Literal["LTFTE", "STFTE"]
    status: Literal["active", "inactive"]
    current_hiref_id: str | None
    hiref_end_date: str | None
    role: str | None
    level: int | None
    effective_start: str | None
    effective_end: str | None


@dataclass(frozen=True)
class ValidatedProject:
    row_number: int
    project_key: str
    display_name: str
    status: Literal["planning", "active", "done"]
    priority: int
    start_date: str | None
    target_end: str | None


@dataclass(frozen=True)
class ValidatedAllocation:
    row_number: int
    member_key: str
    project_key: str
    month: str
    year: int
    month_number: int
    allocation: float


@dataclass(frozen=True)
class ValidatedCapacityRow:
    row_number: int
    member_key: str
    month: str
    year: int
    month_number: int
    leave_fraction: float
    bau_fraction: float
    non_project_fraction: float


@dataclass(frozen=True)
class ValidatedWorkbook:
    setup: ValidatedSetup
    members: list[ValidatedMember]
    projects: list[ValidatedProject]
    allocations: list[ValidatedAllocation]
    capacity_rows: list[ValidatedCapacityRow]


@dataclass(frozen=True)
class WorkbookValidationResult:
    workbook: ValidatedWorkbook | None
    blockers: list[ValidationIssue]
    warnings: list[ValidationIssue]
