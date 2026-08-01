"""Fail-closed statement-manifest comparison for the B2 snapshot core.

The later B3 composer is responsible for constructing these normalized public
statement states. This module intentionally knows no upstream capability store.
"""

from __future__ import annotations

from typing import Any

_REQUIRED = {"identity_key", "producer", "scope_fingerprint", "semantic_fingerprint", "evidence_state_fingerprint", "active_material", "transition_state", "coverage_complete", "usable_evidence", "limited_active_proven"}


def compare_statement_manifests(*, baseline: list[dict[str, Any]] | None, current: list[dict[str, Any]], scope_fingerprint: str, baseline_coverage: dict[str, bool] | None = None) -> list[dict[str, Any]]:
    """Classify only explicitly evidenced transitions; all uncertainty is not comparable."""
    baseline_available = baseline is not None
    baseline_by_key = _index(baseline or [])
    current_by_key = _index(current)
    results: list[dict[str, Any]] = []
    for identity_key in sorted(set(baseline_by_key) | set(current_by_key)):
        prior = baseline_by_key.get(identity_key)
        now = current_by_key.get(identity_key)
        results.append(_classify(prior, now, scope_fingerprint, baseline_available, bool((baseline_coverage or {}).get((now or prior or {}).get("producer", "")))))
    return results


def _index(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for item in items:
        if not isinstance(item, dict) or _REQUIRED - set(item) or not isinstance(item.get("identity_key"), str):
            raise ValueError("WEEKLY_BRIEF_MANIFEST_INVALID")
        if item["identity_key"] not in indexed:
            indexed[item["identity_key"]] = item
        else:
            raise ValueError("WEEKLY_BRIEF_MANIFEST_INVALID")
    return indexed


def _usable(item: dict[str, Any] | None, scope_fingerprint: str) -> bool:
    return bool(item and item.get("scope_fingerprint") == scope_fingerprint and item.get("coverage_complete") is True and item.get("usable_evidence") is True)


def _classify(prior: dict[str, Any] | None, now: dict[str, Any] | None, scope_fingerprint: str, baseline_available: bool, baseline_coverage_complete: bool) -> dict[str, Any]:
    identity_key = (now or prior or {}).get("identity_key", "")
    result = {"identity_key": identity_key, "change_state": "not_comparable", "changed": False, "evidence_changed": False}
    if prior is None:
        if baseline_available and baseline_coverage_complete and _usable(now, scope_fingerprint) and now.get("active_material") is True:
            result["change_state"] = "new"
        return result
    if now is None:
        return result
    if prior.get("producer") != now.get("producer"):
        return result
    if not _usable(prior, scope_fingerprint) or not _usable(now, scope_fingerprint):
        if _usable(prior, scope_fingerprint) and prior.get("active_material") is True and now.get("scope_fingerprint") == scope_fingerprint and now.get("active_material") is True and now.get("transition_state") == "active" and now.get("limited_active_proven") is True:
            result["change_state"] = "continuing"
        return result
    if prior.get("active_material") is True and now.get("transition_state") in {"clear", "resolved", "completed", "green"}:
        result["change_state"] = "resolved"
    elif prior.get("active_material") is True and now.get("active_material") is True:
        result["change_state"] = "continuing"
    else:
        return result
    result["changed"] = prior.get("semantic_fingerprint") != now.get("semantic_fingerprint")
    result["evidence_changed"] = prior.get("evidence_state_fingerprint") != now.get("evidence_state_fingerprint")
    return result
