from __future__ import annotations

import re
from datetime import date

from pm_agent.config import settings
from pm_agent.rules.identity import slugify_text


def days_until(date_text: str | None) -> int | None:
    value = (date_text or "").strip()
    if not value:
        return None
    try:
        return (date.fromisoformat(value) - date.today()).days
    except ValueError:
        return None


def urgency(days: int | None) -> str:
    if days is None:
        return "unknown"
    if days <= 0:
        return "expired"
    if days <= 60:
        return "critical"
    if days <= 90:
        return "high"
    if days <= 180:
        return "medium"
    return "ok"


def hiref_urgency(days: int | None, has_next_hiref: bool = False) -> str:
    if has_next_hiref and days is not None and days > 0:
        return "ok"
    return urgency(days)


def project_alignment_status(
    hiref_project: str | None,
    actual_project_names: list[str] | None = None,
    actual_project_ids: list[str] | None = None,
    actual_project_keys: list[str] | None = None,
    alias_groups: list[set[str]] | None = None,
) -> str:
    actual_names = [value.strip() for value in (actual_project_names or []) if value and value.strip()]
    actual_ids = [value.strip() for value in (actual_project_ids or []) if value and value.strip()]
    actual_keys = [value.strip() for value in (actual_project_keys or []) if value and value.strip()]

    if not actual_names and not actual_ids and not actual_keys:
        return "no_active_assignment"

    hiref_codes = _extract_project_codes(hiref_project)
    actual_codes: set[str] = set()
    for value in [*actual_names, *actual_ids, *actual_keys]:
        actual_codes.update(_extract_project_codes(value))
    if hiref_codes and actual_codes and hiref_codes.intersection(actual_codes):
        return "aligned"

    hiref_label = _normalize_project_label(hiref_project)
    actual_labels = {
        label
        for label in (
            _normalize_project_label(value)
            for value in [*actual_names, *actual_ids, *actual_keys]
        )
        if label
    }

    if hiref_label and any(
        label == hiref_label or label in hiref_label or hiref_label in label
        for label in actual_labels
    ):
        return "aligned"

    effective_alias_groups = (
        _normalize_alias_groups(alias_groups)
        if alias_groups is not None
        else _normalize_alias_groups(settings.project_alias_groups())
    )
    if hiref_label and any(
        _labels_share_alias_group(hiref_label, label, effective_alias_groups)
        for label in actual_labels
    ):
        return "aligned"

    if not hiref_project:
        return "unknown"
    return "mismatch"


def _extract_project_codes(value: str | None) -> set[str]:
    matches = re.findall(r"\d{4,}", value or "")
    return {(match.lstrip("0") or "0") for match in matches}


def _normalize_project_label(value: str | None) -> str:
    text = value or ""
    text = re.sub(r"\s*[（(][^）)]*[）)]\s*", " ", text)
    text = re.sub(r"\b\d{4,}\b", " ", text)
    return slugify_text(text)


def _normalize_alias_groups(alias_groups: list[set[str]]) -> list[set[str]]:
    return [
        {slugify_text(value) for value in group if slugify_text(value)}
        for group in alias_groups
        if group
    ]


def _labels_share_alias_group(
    left: str,
    right: str,
    alias_groups: list[set[str]],
) -> bool:
    for group in alias_groups:
        left_match = any(left == alias or alias in left or left in alias for alias in group)
        right_match = any(right == alias or alias in right or right in alias for alias in group)
        if left_match and right_match:
            return True
    return False
