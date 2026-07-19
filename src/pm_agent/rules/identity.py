from __future__ import annotations

import re


def normalize_name(name: str) -> str:
    value = (name or "").strip()
    value = re.sub(r"\s*[（(][^）)]+[）)]\s*", "", value)
    return value.strip().lower()


def slugify_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (value or "").strip().lower()).strip("-")


def normalize_resource_portal_id(raw_id: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (raw_id or "").strip().lower())


def derive_workday_id(employee_key: str | None) -> str | None:
    normalized = normalize_resource_portal_id(employee_key or "")
    if not normalized:
        return None
    if normalized.isdigit():
        return normalized
    match = re.fullmatch(r"cqa(\d+)", normalized)
    if match:
        return match.group(1)
    return None


def is_placeholder_identifier(value: str | None) -> bool:
    normalized = normalize_resource_portal_id(value or "")
    if not normalized:
        return False
    return normalized.startswith("hiref") or normalized == "tobehired"


def build_default_resource_portal_id(
    workday_id: str,
    resource_type: str | None = None,
) -> str:
    normalized_workday_id = normalize_resource_portal_id(workday_id)
    resource_type_value = (resource_type or "").strip().upper()
    if resource_type_value == "STFTE":
        return f"cqa{normalized_workday_id}"
    return normalized_workday_id


def build_placeholder_id(raw_identifier: str | None, fallback_name: str = "") -> str:
    normalized_identifier = normalize_resource_portal_id(raw_identifier or "")
    if normalized_identifier:
        return normalized_identifier

    slug = slugify_text(fallback_name)
    return slug or "placeholder"
