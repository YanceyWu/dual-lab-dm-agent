"""Deterministic interaction-memory status, demo seed, and context composition."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pm_agent.interaction_memory import repository

_VALID_SCOPE_IDENTIFIER = re.compile(r"^[A-Za-z0-9._:/-]{1,128}$")
_INTENT_KEYWORDS = {
    "capacity": (
        "capacity",
        "workload",
        "load",
        "available",
        "room",
        "capacity review",
        "容量",
        "负载",
        "空闲",
        "谁还有容量",
    ),
    "weekly_brief": (
        "weekly brief",
        "weekly",
        "brief",
        "snapshot",
        "本周 brief",
        "weekly dm brief",
        "周报",
        "简报",
        "快照",
    ),
    "planning": (
        "implementation plan",
        "plan",
        "spec",
        "design",
        "实施计划",
        "规划",
        "设计",
        "方案",
    ),
}
_TERMINAL_STATES = {"active", "open"}


@dataclass(frozen=True)
class ScopeResolution:
    """Deterministic repo/project scope resolution for interaction memory."""

    state: str
    scope_id: str
    scope_source: str
    scope_key: str
    display_name: str


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip())


def _stable_repo_scope_id(root: Path) -> tuple[str, str]:
    digest = hashlib.sha256(str(root).encode("utf-8")).hexdigest()
    return f"repo:{digest[:24]}", digest


def _find_repo_root(start: Path) -> Path | None:
    candidate = start.resolve()
    for current in (candidate, *candidate.parents):
        marker = current / ".git"
        if marker.is_dir() or marker.is_file():
            return current
    return None


def _manual_event_ref(scope: ScopeResolution, operation_kind: str) -> dict[str, str]:
    event_key = "manual-" + hashlib.sha256(
        f"{scope.scope_id}:{operation_kind}".encode("utf-8")
    ).hexdigest()[:16]
    return {
        "repo_scope_id": scope.scope_id,
        "conversation_id": "manual-cli",
        "turn_id": operation_kind,
        "operation_kind": operation_kind,
        "event_key": event_key,
    }


def resolve_scope(
    *,
    project_id: str | None = None,
    repo_root: str | Path | None = None,
) -> ScopeResolution:
    """Resolve the current repo/project scope without consulting business data."""
    normalized_project_id = (project_id or "").strip()
    if normalized_project_id:
        if _VALID_SCOPE_IDENTIFIER.fullmatch(normalized_project_id) is None:
            return ScopeResolution(
                state="scope_unknown",
                scope_id="",
                scope_source="",
                scope_key="",
                display_name="",
            )
        return ScopeResolution(
            state="resolved",
            scope_id=f"project:{normalized_project_id}",
            scope_source="project_id",
            scope_key=normalized_project_id,
            display_name=normalized_project_id,
        )
    root_candidate = Path(repo_root).resolve() if repo_root else Path.cwd().resolve()
    root = _find_repo_root(root_candidate)
    if root is None:
        return ScopeResolution(
            state="scope_unknown",
            scope_id="",
            scope_source="",
            scope_key="",
            display_name="",
        )
    scope_id, scope_key = _stable_repo_scope_id(root)
    return ScopeResolution(
        state="resolved",
        scope_id=scope_id,
        scope_source="repo_root_fingerprint",
        scope_key=scope_key,
        display_name=root.name,
    )


def _scope_payload(scope: ScopeResolution) -> dict[str, Any]:
    return {
        "scope_id": scope.scope_id,
        "scope_source": scope.scope_source,
        "scope_key": scope.scope_key,
        "display_name": scope.display_name,
    }


def _base_status_payload(
    *,
    scope: ScopeResolution,
    capability_state: str,
    counts: dict[str, Any] | None = None,
    integrity: dict[str, Any] | None = None,
    enabled: bool | None = None,
    include_integrity: bool = False,
) -> dict[str, Any]:
    diagnostics = integrity
    if diagnostics is None:
        diagnostics = (
            repository.integrity_report()
            if include_integrity
            else {"state": "not_run"}
        )
    return {
        "status": "success",
        "capability_state": capability_state,
        "scope": _scope_payload(scope) if scope.state == "resolved" else None,
        "enabled": enabled,
        "summary": counts or {
            "total_entries": 0,
            "by_kind": {},
            "by_state": {},
            "audit_event_count": 0,
        },
        "diagnostics": diagnostics,
    }


def _schema_unavailable_payload(
    *,
    scope: ScopeResolution,
    include_integrity: bool,
) -> dict[str, Any]:
    return _base_status_payload(
        scope=scope,
        capability_state="unavailable",
        enabled=False,
        include_integrity=include_integrity,
        integrity={
            "state": "not_initialized",
            "reason": "interaction_memory_schema_missing",
        },
    )


def interaction_memory_status(
    *,
    project_id: str | None = None,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    """Return bounded capability state and grouped local counts."""
    scope = resolve_scope(project_id=project_id, repo_root=repo_root)
    if not repository.schema_ready():
        return _schema_unavailable_payload(scope=scope, include_integrity=False)
    if scope.state != "resolved":
        return _base_status_payload(
            scope=scope,
            capability_state="scope_unknown",
            enabled=False,
            include_integrity=True,
        )
    scope_row = repository.load_scope(scope.scope_id)
    counts = repository.count_entries(scope.scope_id)
    if scope_row is not None and not scope_row["enabled"]:
        return _base_status_payload(
            scope=scope,
            capability_state="disabled",
            counts=counts,
            enabled=False,
            include_integrity=True,
        )
    capability_state = "enabled" if counts["total_entries"] else "empty"
    return _base_status_payload(
        scope=scope,
        capability_state=capability_state,
        counts=counts,
        enabled=True,
        include_integrity=True,
    )


def _seed_entries(scope: ScopeResolution) -> list[dict[str, Any]]:
    event_ref = _manual_event_ref(scope, "demo_seed")
    entries = [
        {
            "memory_kind": "preference",
            "category": "answer-language",
            "title": "zh-CN",
            "summary": "Respond in Chinese for this repository.",
            "state": "active",
            "confidence": 1.0,
            "weight": 1.0,
            "metadata": {"value": "zh-CN", "intent_tags": ["all"]},
            "interaction_event_ref": event_ref,
        },
        {
            "memory_kind": "preference",
            "category": "answer-shape",
            "title": "conclusion-first",
            "summary": "Lead with the conclusion before supporting detail.",
            "state": "active",
            "confidence": 0.95,
            "weight": 1.0,
            "metadata": {"value": "conclusion-first", "intent_tags": ["all"]},
            "interaction_event_ref": event_ref,
        },
        {
            "memory_kind": "context",
            "category": "main-entry",
            "title": "copilot-chat",
            "summary": "GitHub Copilot Chat is the main entry for this repo.",
            "state": "active",
            "confidence": 0.95,
            "weight": 0.9,
            "metadata": {
                "intent_tags": ["all"],
                "keywords": ["copilot", "chat"],
            },
            "interaction_event_ref": event_ref,
        },
        {
            "memory_kind": "context",
            "category": "capacity-routing",
            "title": "team-workload",
            "summary": "Capacity-style questions in this repo usually map to team workload review.",
            "state": "active",
            "confidence": 0.92,
            "weight": 1.0,
            "metadata": {
                "intent_tags": ["capacity"],
                "keywords": ["capacity", "workload", "容量", "负载", "谁还有容量"],
                "routing_hint": "team-workload-overview",
            },
            "interaction_event_ref": event_ref,
        },
        {
            "memory_kind": "follow_up",
            "category": "weekly-brief-snapshot",
            "title": "pending-confirm",
            "summary": "Weekly brief snapshot is still pending confirmation.",
            "state": "open",
            "confidence": 0.88,
            "weight": 1.0,
            "metadata": {
                "intent_tags": ["weekly_brief", "capacity"],
                "keywords": ["brief", "weekly", "snapshot", "周报", "简报", "快照"],
                "follow_up_kind": "exact_preview_confirmation_pending",
            },
            "interaction_event_ref": event_ref,
        },
        {
            "memory_kind": "strategy",
            "category": "surface-relevant-followup-once",
            "title": "enabled",
            "summary": "When directly relevant, surface one open follow-up reminder once.",
            "state": "active",
            "confidence": 0.9,
            "weight": 1.0,
            "metadata": {
                "intent_tags": ["capacity", "weekly_brief"],
                "strategy_flag": "surface-relevant-followup-once",
            },
            "interaction_event_ref": event_ref,
        },
        {
            "memory_kind": "strategy",
            "category": "minimize-redundant-clarification",
            "title": "enabled",
            "summary": "Reuse repo-local context before asking repetitive clarification questions.",
            "state": "active",
            "confidence": 0.85,
            "weight": 0.9,
            "metadata": {
                "intent_tags": ["all"],
                "strategy_flag": "minimize-redundant-clarification",
            },
            "interaction_event_ref": event_ref,
        },
    ]
    return entries


def demo_seed(
    *,
    project_id: str | None = None,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    """Insert one deterministic demo profile for manual testing."""
    repository.ensure_schema()
    scope = resolve_scope(project_id=project_id, repo_root=repo_root)
    if scope.state != "resolved":
        return {
            "status": "failed",
            "warnings": ["INTERACTION_MEMORY_SCOPE_UNKNOWN"],
        }
    repository.ensure_scope(
        scope_id=scope.scope_id,
        scope_source=scope.scope_source,
        scope_key=scope.scope_key,
        scope_display_name=scope.display_name,
    )
    seeded: list[dict[str, Any]] = []
    for entry in _seed_entries(scope):
        stored = repository.upsert_entry(scope_id=scope.scope_id, **entry)
        repository.insert_audit(
            scope_id=scope.scope_id,
            entry_id=stored["entry_id"],
            operation_type="demo_seed",
            interaction_event_ref=entry["interaction_event_ref"],
            prior_state={},
            new_state={
                "memory_kind": stored["memory_kind"],
                "category": stored["category"],
                "title": stored["title"],
                "state": stored["state"],
            },
        )
        seeded.append(stored)
    counts = repository.count_entries(scope.scope_id)
    scope_row = repository.load_scope(scope.scope_id)
    enabled = not scope_row or scope_row["enabled"]
    return {
        "status": "success",
        "operation": "demo_seed",
        "capability_state": "enabled" if enabled else "disabled",
        "scope": _scope_payload(scope),
        "enabled": enabled,
        "summary": counts,
        "seeded_entry_ids": [entry["entry_id"] for entry in seeded],
    }


def inspect_memory(
    *,
    project_id: str | None = None,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    """Return all normalized memory rows for one scope."""
    scope = resolve_scope(project_id=project_id, repo_root=repo_root)
    if not repository.schema_ready():
        return {
            **_schema_unavailable_payload(scope=scope, include_integrity=False),
            "entries": [],
        }
    if scope.state != "resolved":
        return _base_status_payload(
            scope=scope,
            capability_state="scope_unknown",
            enabled=False,
            include_integrity=True,
        )
    scope_row = repository.load_scope(scope.scope_id)
    counts = repository.count_entries(scope.scope_id)
    entries = repository.list_entries(scope.scope_id)
    capability_state = (
        "disabled"
        if scope_row is not None and not scope_row["enabled"]
        else "enabled"
        if counts["total_entries"]
        else "empty"
    )
    return {
        **_base_status_payload(
            scope=scope,
            capability_state=capability_state,
            counts=counts,
            enabled=not scope_row or scope_row["enabled"],
            include_integrity=True,
        ),
        "entries": entries,
    }


def disable_scope(
    *,
    project_id: str | None = None,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    """Disable automatic interaction-memory use for one scope."""
    repository.ensure_schema()
    scope = resolve_scope(project_id=project_id, repo_root=repo_root)
    if scope.state != "resolved":
        return {
            "status": "failed",
            "warnings": ["INTERACTION_MEMORY_SCOPE_UNKNOWN"],
        }
    repository.ensure_scope(
        scope_id=scope.scope_id,
        scope_source=scope.scope_source,
        scope_key=scope.scope_key,
        scope_display_name=scope.display_name,
    )
    scope_update = repository.set_scope_enabled_with_audit(
        scope_id=scope.scope_id,
        enabled=False,
        operation_type="disable",
        interaction_event_ref=_manual_event_ref(scope, "disable_scope"),
    )
    return {
        "status": "success",
        "capability_state": "disabled",
        "scope": _scope_payload(scope),
        "enabled": bool(scope_update["scope"] and scope_update["scope"]["enabled"]),
        "summary": repository.count_entries(scope.scope_id),
    }


def enable_scope(
    *,
    project_id: str | None = None,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    """Enable automatic interaction-memory use for one scope."""
    repository.ensure_schema()
    scope = resolve_scope(project_id=project_id, repo_root=repo_root)
    if scope.state != "resolved":
        return {
            "status": "failed",
            "warnings": ["INTERACTION_MEMORY_SCOPE_UNKNOWN"],
        }
    repository.ensure_scope(
        scope_id=scope.scope_id,
        scope_source=scope.scope_source,
        scope_key=scope.scope_key,
        scope_display_name=scope.display_name,
    )
    scope_update = repository.set_scope_enabled_with_audit(
        scope_id=scope.scope_id,
        enabled=True,
        operation_type="enable",
        interaction_event_ref=_manual_event_ref(scope, "enable_scope"),
    )
    counts = repository.count_entries(scope.scope_id)
    return {
        "status": "success",
        "capability_state": "enabled" if counts["total_entries"] else "empty",
        "scope": _scope_payload(scope),
        "enabled": bool(scope_update["scope"] and scope_update["scope"]["enabled"]),
        "summary": counts,
    }


def _message_intents(message: str) -> list[str]:
    normalized = _normalize_text(message).lower()
    intents: list[str] = []
    for intent, keywords in _INTENT_KEYWORDS.items():
        if any(keyword in normalized for keyword in keywords):
            intents.append(intent)
    return intents or ["general"]


def _entry_score(entry: dict[str, Any], intents: list[str], normalized_message: str) -> float:
    metadata = entry["metadata"]
    intent_tags = {str(value) for value in metadata.get("intent_tags", [])}
    keywords = [str(value).lower() for value in metadata.get("keywords", [])]
    score = 0.0
    if "all" in intent_tags:
        score += 1.0
    score += 3.0 * len(intent_tags.intersection(intents))
    score += 0.5 * sum(1 for keyword in keywords if keyword and keyword in normalized_message)
    score += float(entry["weight"])
    score += float(entry["confidence"])
    return score


def _select_entries(
    entries: list[dict[str, Any]],
    *,
    memory_kind: str,
    intents: list[str],
    normalized_message: str,
    limit: int,
) -> list[dict[str, Any]]:
    filtered = [
        entry
        for entry in entries
        if entry["memory_kind"] == memory_kind and entry["state"] in _TERMINAL_STATES
    ]
    ranked = sorted(
        filtered,
        key=lambda entry: (
            _entry_score(entry, intents, normalized_message),
            entry["updated_at"],
            entry["entry_id"],
        ),
        reverse=True,
    )
    return ranked[:limit]


def _selected_memory_payload(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "entry_id": entry["entry_id"],
            "category": entry["category"],
            "title": entry["title"],
            "summary": entry["summary"],
            "state": entry["state"],
            "confidence": entry["confidence"],
            "weight": entry["weight"],
            "metadata": entry["metadata"],
        }
        for entry in entries
    ]


def _first_entry_per_category(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    seen_categories: set[str] = set()
    for entry in entries:
        category = str(entry["category"])
        if category in seen_categories:
            continue
        seen_categories.add(category)
        selected.append(entry)
    return selected


def resolve_turn_context(
    *,
    message: str,
    project_id: str | None = None,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    """Resolve repo-scoped memory and compose one bounded turn-context object."""
    normalized_message = _normalize_text(message)
    scope = resolve_scope(project_id=project_id, repo_root=repo_root)
    if not repository.schema_ready():
        return {
            **_schema_unavailable_payload(scope=scope, include_integrity=False),
            "turn": {
                "message": normalized_message,
                "intent_tags": _message_intents(normalized_message),
            },
            "selected_memory": {
                "preferences": [],
                "contexts": [],
                "follow_ups": [],
                "strategies": [],
            },
            "working_context": {},
        }
    if scope.state != "resolved":
        return {
            **_base_status_payload(
                scope=scope,
                capability_state="scope_unknown",
                enabled=False,
            ),
            "turn": {
                "message": normalized_message,
                "intent_tags": _message_intents(normalized_message),
            },
            "selected_memory": {
                "preferences": [],
                "contexts": [],
                "follow_ups": [],
                "strategies": [],
            },
            "working_context": {},
        }
    scope_row = repository.load_scope(scope.scope_id)
    counts = repository.count_entries(scope.scope_id)
    intents = _message_intents(normalized_message)
    if scope_row is not None and not scope_row["enabled"]:
        return {
            **_base_status_payload(
                scope=scope,
                capability_state="disabled",
                counts=counts,
                enabled=False,
            ),
            "turn": {"message": normalized_message, "intent_tags": intents},
            "selected_memory": {
                "preferences": [],
                "contexts": [],
                "follow_ups": [],
                "strategies": [],
            },
            "working_context": {},
        }
    if counts["total_entries"] == 0:
        return {
            **_base_status_payload(
                scope=scope,
                capability_state="empty",
                counts=counts,
                enabled=True,
            ),
            "turn": {"message": normalized_message, "intent_tags": intents},
            "selected_memory": {
                "preferences": [],
                "contexts": [],
                "follow_ups": [],
                "strategies": [],
            },
            "working_context": {},
        }
    entries = repository.list_entries(scope.scope_id)
    selected_preferences = _select_entries(
        entries,
        memory_kind="preference",
        intents=intents,
        normalized_message=normalized_message.lower(),
        limit=4,
    )
    selected_preferences = _first_entry_per_category(selected_preferences)
    selected_contexts = _select_entries(
        entries,
        memory_kind="context",
        intents=intents,
        normalized_message=normalized_message.lower(),
        limit=3,
    )
    selected_follow_ups = _select_entries(
        entries,
        memory_kind="follow_up",
        intents=intents,
        normalized_message=normalized_message.lower(),
        limit=2,
    )
    selected_strategies = _select_entries(
        entries,
        memory_kind="strategy",
        intents=intents,
        normalized_message=normalized_message.lower(),
        limit=3,
    )
    preference_values = {
        entry["category"]: entry["metadata"].get("value", entry["title"])
        for entry in selected_preferences
    }
    strategy_flags = [
        str(entry["metadata"].get("strategy_flag") or entry["category"])
        for entry in selected_strategies
    ]
    routing_hints = [
        str(entry["metadata"].get("routing_hint"))
        for entry in selected_contexts
        if entry["metadata"].get("routing_hint")
    ]
    composed_guidance: list[str] = []
    if preference_values.get("answer-language") == "zh-CN":
        composed_guidance.append("Respond in Chinese for this repository.")
    if preference_values.get("answer-shape") == "conclusion-first":
        composed_guidance.append(
            "Lead with the conclusion before supporting detail."
        )
    for context_entry in selected_contexts:
        composed_guidance.append(f"Local context: {context_entry['summary']}")
    if (
        "surface-relevant-followup-once" in strategy_flags
        and selected_follow_ups
    ):
        composed_guidance.append(
            "If directly relevant, surface one open follow-up reminder once."
        )
    if "minimize-redundant-clarification" in strategy_flags:
        composed_guidance.append(
            "Reuse repo-local context before asking repetitive clarification questions."
        )
    return {
        **_base_status_payload(
            scope=scope,
            capability_state="enabled",
            counts=counts,
            enabled=True,
        ),
        "turn": {"message": normalized_message, "intent_tags": intents},
        "selected_memory": {
            "preferences": _selected_memory_payload(selected_preferences),
            "contexts": _selected_memory_payload(selected_contexts),
            "follow_ups": _selected_memory_payload(selected_follow_ups),
            "strategies": _selected_memory_payload(selected_strategies),
        },
        "working_context": {
            "answer_preferences": {
                "language": preference_values.get("answer-language", ""),
                "answer_shape": preference_values.get("answer-shape", ""),
            },
            "routing_hints": routing_hints,
            "follow_up_hints": [
                entry["summary"] for entry in selected_follow_ups
            ],
            "strategy_flags": strategy_flags,
            "composed_guidance": composed_guidance,
        },
    }
