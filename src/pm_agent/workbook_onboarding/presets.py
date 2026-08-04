"""Packaged workbook presets for Team/Project + Capacity onboarding."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

PresetStatus = Literal["active", "deprecated", "retired"]

DEFAULT_WORKBOOK_MAPPING_PRESET_ID = "team-project-capacity-workbook-v1"
WORKBOOK_MAPPING_PRESET_ID_WITH_ALIASES = "team-project-capacity-workbook-v1-aliases"


@dataclass(frozen=True)
class WorkbookPresetField:
    field_key: str
    header_name: str
    aliases: tuple[str, ...] = ()

    @property
    def accepted_header_names(self) -> tuple[str, ...]:
        return (self.header_name, *self.aliases)


@dataclass(frozen=True)
class WorkbookPresetSection:
    section_key: str
    display_name: str
    primary_sheet_name: str
    sheet_aliases: tuple[str, ...]
    required: bool
    fields: tuple[WorkbookPresetField, ...]

    @property
    def accepted_sheet_names(self) -> tuple[str, ...]:
        return (self.primary_sheet_name, *self.sheet_aliases)


@dataclass(frozen=True)
class WorkbookPreset:
    mapping_preset_id: str
    display_name: str
    status: PresetStatus
    sections: tuple[WorkbookPresetSection, ...]
    capacity_row_coverage_policy: str
    semantic_notes: tuple[str, ...]


@dataclass(frozen=True)
class WorkbookHeaderResolution:
    field_key: str
    expected_header_name: str
    resolved_header_name: str
    matched_via_alias: bool


@dataclass(frozen=True)
class WorkbookSectionResolution:
    section_key: str
    display_name: str
    required: bool
    expected_sheet_name: str
    resolved_sheet_name: str | None
    matched_via_alias: bool
    header_matches: tuple[WorkbookHeaderResolution, ...] = ()


@dataclass(frozen=True)
class WorkbookPresetResolution:
    mapping_preset_id: str
    display_name: str
    status: PresetStatus
    matched_via_alias: bool
    sections: tuple[WorkbookSectionResolution, ...]
    missing_optional_sections: tuple[str, ...]
    missing_required_sections: tuple[str, ...]


def _section(
    section_key: str,
    display_name: str,
    *,
    required: bool = True,
    sheet_aliases: tuple[str, ...] = (),
    fields: tuple[WorkbookPresetField, ...],
) -> WorkbookPresetSection:
    return WorkbookPresetSection(
        section_key=section_key,
        display_name=display_name,
        primary_sheet_name=display_name,
        sheet_aliases=sheet_aliases,
        required=required,
        fields=fields,
    )


_BASELINE_SECTIONS = (
    _section(
        "setup",
        "Setup",
        fields=(
            WorkbookPresetField("plan_version_name", "plan_version_name"),
            WorkbookPresetField("as_of_date", "as_of_date"),
            WorkbookPresetField("start_month", "start_month"),
            WorkbookPresetField("end_month", "end_month"),
        ),
    ),
    _section(
        "members",
        "Members",
        fields=(
            WorkbookPresetField("member_key", "member_key"),
            WorkbookPresetField("display_name", "display_name"),
            WorkbookPresetField("fte_type", "fte_type"),
            WorkbookPresetField("status", "status"),
            WorkbookPresetField("current_hiref_id", "current_hiref_id"),
            WorkbookPresetField("hiref_end_date", "hiref_end_date"),
            WorkbookPresetField("role", "role"),
            WorkbookPresetField("level", "level"),
            WorkbookPresetField("effective_start", "effective_start"),
            WorkbookPresetField("effective_end", "effective_end"),
        ),
    ),
    _section(
        "projects",
        "Projects",
        fields=(
            WorkbookPresetField("project_key", "project_key"),
            WorkbookPresetField("display_name", "display_name"),
            WorkbookPresetField("status", "status"),
            WorkbookPresetField("priority", "priority"),
            WorkbookPresetField("start_date", "start_date"),
            WorkbookPresetField("target_end", "target_end"),
        ),
    ),
    _section(
        "allocations",
        "Allocations",
        fields=(
            WorkbookPresetField("member_key", "member_key"),
            WorkbookPresetField("project_key", "project_key"),
            WorkbookPresetField("month", "month"),
            WorkbookPresetField("allocation", "allocation"),
        ),
    ),
    _section(
        "capacity",
        "Capacity",
        fields=(
            WorkbookPresetField("member_key", "member_key"),
            WorkbookPresetField("month", "month"),
            WorkbookPresetField("leave_fraction", "leave_fraction"),
            WorkbookPresetField("bau_fraction", "bau_fraction"),
            WorkbookPresetField("non_project_fraction", "non_project_fraction"),
        ),
    ),
)

_ALIAS_SECTIONS = (
    _section(
        "setup",
        "Setup",
        sheet_aliases=("Plan Setup",),
        fields=(
            WorkbookPresetField("plan_version_name", "plan_version_name", ("plan_name",)),
            WorkbookPresetField("as_of_date", "as_of_date", ("snapshot_date",)),
            WorkbookPresetField("start_month", "start_month"),
            WorkbookPresetField("end_month", "end_month"),
        ),
    ),
    _section(
        "members",
        "Members",
        sheet_aliases=("Team Members",),
        fields=(
            WorkbookPresetField("member_key", "member_key"),
            WorkbookPresetField("display_name", "display_name", ("member_name",)),
            WorkbookPresetField("fte_type", "fte_type"),
            WorkbookPresetField("status", "status"),
            WorkbookPresetField("current_hiref_id", "current_hiref_id", ("hiref_id",)),
            WorkbookPresetField("hiref_end_date", "hiref_end_date"),
            WorkbookPresetField("role", "role"),
            WorkbookPresetField("level", "level"),
            WorkbookPresetField("effective_start", "effective_start"),
            WorkbookPresetField("effective_end", "effective_end", ("effective_until",)),
        ),
    ),
    _section(
        "projects",
        "Projects",
        sheet_aliases=("Project List",),
        fields=(
            WorkbookPresetField("project_key", "project_key", ("project_id",)),
            WorkbookPresetField("display_name", "display_name"),
            WorkbookPresetField("status", "status"),
            WorkbookPresetField("priority", "priority"),
            WorkbookPresetField("start_date", "start_date"),
            WorkbookPresetField("target_end", "target_end", ("target_end_date",)),
        ),
    ),
    _section(
        "allocations",
        "Allocations",
        sheet_aliases=("Project Allocations",),
        fields=(
            WorkbookPresetField("member_key", "member_key"),
            WorkbookPresetField("project_key", "project_key", ("project_id",)),
            WorkbookPresetField("month", "month"),
            WorkbookPresetField("allocation", "allocation", ("allocation_fraction",)),
        ),
    ),
    _section(
        "capacity",
        "Capacity",
        sheet_aliases=("Member Capacity",),
        fields=(
            WorkbookPresetField("member_key", "member_key"),
            WorkbookPresetField("month", "month"),
            WorkbookPresetField("leave_fraction", "leave_fraction"),
            WorkbookPresetField("bau_fraction", "bau_fraction"),
            WorkbookPresetField(
                "non_project_fraction",
                "non_project_fraction",
                ("non_project_allocation",),
            ),
        ),
    ),
)

_PRESETS = (
    WorkbookPreset(
        mapping_preset_id=DEFAULT_WORKBOOK_MAPPING_PRESET_ID,
        display_name="Team/Project + Capacity workbook v1",
        status="active",
        sections=_BASELINE_SECTIONS,
        capacity_row_coverage_policy="missing_row_means_unknown",
        semantic_notes=(
            "Canonical workforce and capacity packages match the Batch A workbook v1 baseline.",
        ),
    ),
    WorkbookPreset(
        mapping_preset_id=WORKBOOK_MAPPING_PRESET_ID_WITH_ALIASES,
        display_name="Workbook v1 alias contract",
        status="active",
        sections=_ALIAS_SECTIONS,
        capacity_row_coverage_policy="missing_row_means_unknown",
        semantic_notes=(
            "Accepted sheet/header aliases still produce the same canonical packages as workbook v1.",
        ),
    ),
)

_PRESET_BY_ID = {preset.mapping_preset_id: preset for preset in _PRESETS}


def list_workbook_presets() -> list[WorkbookPreset]:
    return list(_PRESETS)


def get_workbook_preset(mapping_preset_id: str) -> WorkbookPreset:
    preset = _PRESET_BY_ID.get(mapping_preset_id)
    if preset is None:
        raise ValueError("WORKBOOK_MAPPING_PRESET_UNKNOWN")
    return preset


def default_source_options(mapping_preset_id: str) -> dict[str, Any]:
    preset = get_workbook_preset(mapping_preset_id)
    required_sheets = [
        section.primary_sheet_name for section in preset.sections if section.required
    ]
    optional_sheets = [
        section.primary_sheet_name for section in preset.sections if not section.required
    ]
    sheet_aliases = {
        section.primary_sheet_name: list(section.sheet_aliases)
        for section in preset.sections
        if section.sheet_aliases
    }
    header_aliases = {
        section.primary_sheet_name: {
            field.header_name: list(field.aliases)
            for field in section.fields
            if field.aliases
        }
        for section in preset.sections
        if any(field.aliases for field in section.fields)
    }
    return {
        "required_sheets": required_sheets,
        "optional_sheets": optional_sheets,
        "sheet_aliases": sheet_aliases,
        "header_aliases": header_aliases,
        "capacity_row_coverage_policy": preset.capacity_row_coverage_policy,
    }


def serialize_workbook_preset_summary(preset: WorkbookPreset) -> dict[str, Any]:
    return {
        "source_type": "workbook",
        "mapping_preset_id": preset.mapping_preset_id,
        "display_name": preset.display_name,
        "status": preset.status,
    }


def serialize_workbook_preset_lookup(mapping_preset_id: str) -> dict[str, Any]:
    try:
        return serialize_workbook_preset_summary(get_workbook_preset(mapping_preset_id))
    except ValueError as exc:
        if str(exc) != "WORKBOOK_MAPPING_PRESET_UNKNOWN":
            raise
        return {
            "source_type": "workbook",
            "mapping_preset_id": mapping_preset_id,
            "display_name": None,
            "status": "unknown",
        }


def serialize_workbook_preset(preset: WorkbookPreset) -> dict[str, Any]:
    return {
        **serialize_workbook_preset_summary(preset),
        "source_options": default_source_options(preset.mapping_preset_id),
        "semantic_notes": list(preset.semantic_notes),
        "sections": [
            {
                "section_key": section.section_key,
                "display_name": section.display_name,
                "required": section.required,
                "primary_sheet_name": section.primary_sheet_name,
                "accepted_sheet_names": list(section.accepted_sheet_names),
                "primary_headers": [field.header_name for field in section.fields],
                "header_aliases": {
                    field.header_name: list(field.aliases)
                    for field in section.fields
                    if field.aliases
                },
            }
            for section in preset.sections
        ],
    }


def serialize_preset_resolution(
    resolution: WorkbookPresetResolution,
) -> dict[str, Any]:
    return {
        "mapping_preset_id": resolution.mapping_preset_id,
        "display_name": resolution.display_name,
        "status": resolution.status,
        "matched_via_alias": resolution.matched_via_alias,
        "missing_optional_sections": list(resolution.missing_optional_sections),
        "missing_required_sections": list(resolution.missing_required_sections),
        "sections": [
            {
                "section_key": section.section_key,
                "display_name": section.display_name,
                "required": section.required,
                "expected_sheet_name": section.expected_sheet_name,
                "resolved_sheet_name": section.resolved_sheet_name,
                "matched_via_alias": section.matched_via_alias,
                "header_matches": [
                    {
                        "field_key": match.field_key,
                        "expected_header_name": match.expected_header_name,
                        "resolved_header_name": match.resolved_header_name,
                        "matched_via_alias": match.matched_via_alias,
                    }
                    for match in section.header_matches
                ],
            }
            for section in resolution.sections
        ],
    }


def build_source_contract(
    resolution: WorkbookPresetResolution,
) -> dict[str, Any]:
    return {
        "mapping_preset": serialize_workbook_preset_summary(
            get_workbook_preset(resolution.mapping_preset_id)
        ),
        "resolution": serialize_preset_resolution(resolution),
    }


def validate_preset_registry() -> None:
    seen_ids: set[str] = set()
    for preset in _PRESETS:
        if preset.mapping_preset_id in seen_ids:
            raise RuntimeError("WORKBOOK_PRESET_REGISTRY_DUPLICATE_ID")
        seen_ids.add(preset.mapping_preset_id)
        section_keys: set[str] = set()
        accepted_sheet_names: dict[str, str] = {}
        for section in preset.sections:
            if section.section_key in section_keys:
                raise RuntimeError(
                    f"WORKBOOK_PRESET_REGISTRY_DUPLICATE_SECTION:{preset.mapping_preset_id}:{section.section_key}"
                )
            section_keys.add(section.section_key)
            for name in section.accepted_sheet_names:
                if not name.strip():
                    raise RuntimeError(
                        f"WORKBOOK_PRESET_REGISTRY_BLANK_SHEET_ALIAS:{preset.mapping_preset_id}:{section.section_key}"
                    )
                owner = accepted_sheet_names.get(name)
                if owner is not None and owner != section.section_key:
                    raise RuntimeError(
                        f"WORKBOOK_PRESET_REGISTRY_SHEET_ALIAS_COLLISION:{preset.mapping_preset_id}:{name}"
                    )
                accepted_sheet_names[name] = section.section_key
            accepted_headers: dict[str, str] = {}
            for field in section.fields:
                for header_name in field.accepted_header_names:
                    if not header_name.strip():
                        raise RuntimeError(
                            f"WORKBOOK_PRESET_REGISTRY_BLANK_HEADER_ALIAS:{preset.mapping_preset_id}:{section.section_key}:{field.field_key}"
                        )
                    owner = accepted_headers.get(header_name)
                    if owner is not None and owner != field.field_key:
                        raise RuntimeError(
                            f"WORKBOOK_PRESET_REGISTRY_HEADER_ALIAS_COLLISION:{preset.mapping_preset_id}:{section.section_key}:{header_name}"
                        )
                    accepted_headers[header_name] = field.field_key


validate_preset_registry()
