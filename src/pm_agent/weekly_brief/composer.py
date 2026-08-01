"""B3 deterministic, renderer-neutral Weekly Brief v2 composition.

This module consumes only promoted public read contracts.  It deliberately does
not register a route, write a snapshot, or inspect another capability's tables.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from pm_agent.action.read_model import list_action_records
from pm_agent.attention.read_model import current_attention
from pm_agent.database.execution_review import list_latest_execution_facts
from pm_agent.project_health.read_model import latest_assessments
from pm_agent.project_identity.read_model import active_project_manifest
from pm_agent.resource_intelligence.read_model import get_project_capacity_coverage
from pm_agent.weekly_brief import repository as snapshot_repository
from pm_agent.weekly_brief.comparison import compare_statement_manifests

_SECTIONS = (
    "overall_health", "changes_since_previous_snapshot", "highest_attention_signals",
    "achievements", "risks_and_dependencies", "decisions_required",
    "resource_concerns", "next_actions", "freshness_and_limitations",
)
_RULE_VERSION = "weekly-brief-comparison-v2"
_CONTRACT_VERSION = "weekly-brief-v2"


class WeeklyBriefQueryAdapter:
    """Non-routed B3 seam supplying B2's injected lookup/recomposition contract."""

    def __init__(self, *, db_path: str | Path | None = None):
        self.db_path = db_path
        self._candidates: dict[str, dict[str, Any]] = {}

    def compose(self, **parameters: Any) -> dict[str, Any]:
        result = compose_weekly_brief_v2(db_path=self.db_path, **parameters)
        candidate = result.get("snapshot", {}).get("capture_candidate")
        if candidate:
            self._candidates[candidate["execution_id"]] = candidate
        return result

    def query_lookup(self, execution_id: str) -> dict[str, Any] | None:
        return self._candidates.get(execution_id)

    def recompose(self, candidate: dict[str, Any]) -> dict[str, Any] | None:
        scope, inputs = candidate.get("scope"), candidate.get("input")
        if not isinstance(scope, dict) or not isinstance(inputs, dict):
            return None
        result = compose_weekly_brief_v2(
            project_ids=None if scope.get("kind") == "global" else scope.get("project_ids"),
            plan_version_id=inputs.get("plan_version_id"),
            attention_limit=inputs.get("attention_limit", 10),
            baseline_snapshot_id=candidate.get("baseline_snapshot_id") or None,
            generated_at=inputs.get("as_of"), db_path=self.db_path,
        )
        return result.get("snapshot", {}).get("capture_candidate")


def compose_weekly_brief_v2(*, project_ids: list[str] | None = None,
                            plan_version_id: str | None = None,
                            attention_limit: int = 10,
                            baseline_snapshot_id: str | None = None,
                            generated_at: str | None = None,
                            db_path: str | Path | None = None) -> dict[str, Any]:
    """Compose current facts, preserving uncertainty instead of fabricating health."""
    now = generated_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    if not isinstance(attention_limit, int) or not 1 <= attention_limit <= 50:
        raise ValueError("WEEKLY_BRIEF_ATTENTION_LIMIT_INVALID")
    manifest = active_project_manifest(project_ids=project_ids, db_path=db_path)
    scope = manifest["scope"]
    if manifest["coverage"]["state"] != "complete":
        return _unavailable(now, scope, "PROJECT_MANIFEST_NOT_COMPLETE")
    ids = sorted(item["project_id"] for item in manifest["projects"])
    capture_scope = {"kind": scope["kind"], "project_ids": ids}
    sections = {key: _section("not_available", [], []) for key in _SECTIONS}
    statements: list[dict[str, Any]] = []

    # Health has no promoted freshness/completeness assertion suitable for green.
    assessments = {item["project_id"]: item for item in latest_assessments(db_path=db_path) if item["project_id"] in ids}
    health_items, health_limits = [], []
    for project_id in ids:
        assessment = assessments.get(project_id)
        if not assessment:
            health_items.append({"project_id": project_id, "state": "unknown", "limitation": "PROJECT_HEALTH_NOT_AVAILABLE"})
            health_limits.append("PROJECT_HEALTH_NOT_AVAILABLE")
            continue
        state = assessment["state"]
        health_items.append({"project_id": project_id, "state": state, "assessment_id": assessment["assessment_run_id"]})
        # The reader publishes a state but not a contract-level freshness proof.
        health_limits.append("PROJECT_HEALTH_FRESHNESS_NOT_PUBLISHED")
        if state in {"red", "amber"}:
            statements.append(_statement("overall_health", "project_health", project_id, "layered_health", True, "active", {"state": state}, [assessment["assessment_run_id"]], []))
    states = {item["state"] for item in health_items}
    overall = "red" if "red" in states else "amber" if "amber" in states else "unknown"
    sections["overall_health"] = _section("partial" if health_limits else "available", health_items, health_limits, overall=overall)

    # The promoted public reader's maximum page is 50.  A truncated page is
    # explicitly partial; B3 never claims it proves full Attention coverage.
    attention = current_attention(limit=50, db_path=db_path)
    scoped_attention = [item for item in attention["items"] if scope["kind"] == "global" or (item["project_association"]["state"] == "known" and item["project_association"]["project_id"] in ids)]
    scoped_attention.sort(key=lambda item: (item["severity"], item["attention_id"]))
    visible_attention = scoped_attention[:attention_limit]
    attention_limits = ([] if attention["reconciliation_coverage"]["status"] == "complete" else ["ATTENTION_COVERAGE_" + attention["reconciliation_coverage"]["status"].upper()])
    if attention.get("summary", {}).get("truncated"):
        attention_limits.append("ATTENTION_RESULT_TRUNCATED")
    if len(scoped_attention) > len(visible_attention):
        attention_limits.append("WEEKLY_BRIEF_ATTENTION_TRUNCATED")
    for item in visible_attention:
        statements.append(_statement("highest_attention_signals", "attention", item["subject"]["id"], item["rule_key"], True, "active", {"severity": item["severity"], "rule_version": item["rule_version"]}, [item["attention_id"]], []))
    sections["highest_attention_signals"] = _section("available" if not attention_limits else "partial", [{"attention_id": item["attention_id"], "severity": item["severity"], "rule_key": item["rule_key"], "subject": item["subject"]} for item in visible_attention], attention_limits, before_count=len(scoped_attention))

    actions = list_action_records(statuses=["open"], through=now, db_path=db_path)
    action_limits = list(actions["coverage"]["limitation_codes"])
    action_items = []
    for item in sorted(actions["items"], key=lambda entry: entry["action_id"]):
        if not item["follow_up_reasons"]:
            continue
        association = item["project_association"]
        if scope["kind"] == "projects" and (association["state"] != "known" or association["project_id"] not in ids):
            action_limits.append("ACTION_PROJECT_SCOPE_NOT_PROVED")
            continue
        action_items.append({"action_id": item["action_id"], "severity": item["severity"], "follow_up_reasons": item["follow_up_reasons"], "project_association": association})
        statements.append(_statement("next_actions", "action", item["action_id"], "follow_up", True, "active", {"severity": item["severity"], "reasons": item["follow_up_reasons"]}, [item["action_id"]], []))
    if actions["coverage"]["state"] != "complete":
        action_limits.append("ACTION_COVERAGE_NOT_COMPLETE")
    sections["next_actions"] = _section("available" if not action_limits else "partial", action_items, action_limits)
    sections["decisions_required"] = _section("not_available", [], ["DECISION_REQUIRED_DEFINITION_NOT_AVAILABLE"])

    resource_limits: list[str] = []
    if plan_version_id:
        year, month = int(now[:4]), int(now[5:7])
        capacity = sorted((get_project_capacity_coverage(project_id, year, month, plan_version_id, db_path=db_path) for project_id in ids), key=lambda item: item["project_id"])
        # The promoted reader intentionally has no overall freshness contract.
        resource_limits.append("RESOURCE_FRESHNESS_NOT_PUBLISHED")
        for item in capacity:
            if item["state"] != "known":
                resource_limits.append(item["state_reason"])
            elif (item.get("value") or {}).get("overload_state") in {"amber", "red"}:
                statements.append(_statement("resource_concerns", "resource_intelligence", item["project_id"], "capacity_coverage", True, "active", {"overload_state": item["value"]["overload_state"]}, _resource_evidence_ids(item), []))
        sections["resource_concerns"] = _section("partial", capacity, resource_limits)
    else:
        sections["resource_concerns"] = _section("not_available", [], ["RESOURCE_PLAN_VERSION_NOT_PROVIDED"])

    # B1's execution reader has no collection coverage/truncation contract.
    # It can prove an observed exception, but not that no other exception exists.
    execution_limits: list[str] = ["EXECUTION_COVERAGE_NOT_PUBLISHED"]
    for project_id in ids:
        facts = list_latest_execution_facts(project_id, layer="release_milestone", subject_kind=None, subject_id=None, since="1970-01-01T00:00:00Z", limit=50, db_path=db_path)
        for fact in facts:
            if fact["subject_kind"] in {"dependency", "milestone"} and fact["value_state"] in {"conflicting", "unknown"}:
                statements.append(_statement("risks_and_dependencies", "execution", fact["subject_id"], fact["fact_key"], True, "active", {"value_state": fact["value_state"]}, _execution_evidence_ids(fact), [{"state": fact.get("freshness_state", fact.get("run_freshness_state", "not_available")), "observed_at": fact.get("fact_observed_at", "")}]))
    risk_items = [item for item in statements if item["section"] in {"overall_health", "highest_attention_signals", "risks_and_dependencies"} and item["active_material"]]
    risk_limits = list(execution_limits)
    if any(item["producer"] == "project_health" for item in risk_items):
        risk_limits.append("PROJECT_HEALTH_FRESHNESS_NOT_PUBLISHED")
    sections["risks_and_dependencies"] = _section("partial" if risk_limits else "available", sorted(risk_items, key=lambda item: item["statement_id"]), risk_limits)

    producer_coverage = {
        "attention": attention["reconciliation_coverage"]["status"] == "complete" and not attention.get("summary", {}).get("truncated"),
        "action": actions["coverage"]["state"] == "complete" and not action_limits,
        "project_health": False, "execution": False, "resource_intelligence": False,
    }
    current_manifest = _manifest_statements(statements, capture_scope, producer_coverage)
    try:
        baseline = (snapshot_repository.load_confirmed_snapshot(baseline_snapshot_id, db_path=db_path) if baseline_snapshot_id else snapshot_repository.latest_confirmed(_hash(capture_scope), _RULE_VERSION, _CONTRACT_VERSION, db_path=db_path))
        if baseline_snapshot_id and (not baseline or baseline.get("scope_fingerprint") != _hash(capture_scope) or baseline.get("comparison_rule_version") != _RULE_VERSION or baseline.get("contract_version") != _CONTRACT_VERSION):
            return _unavailable(now, scope, "WEEKLY_BRIEF_BASELINE_INVALID")
        else:
            baseline_error = False
    except Exception:
        baseline, baseline_error = None, True
    comparison = {"state": "not_available", "baseline_snapshot_id": None, "items": []}
    if baseline:
        baseline_manifest = json.loads(baseline["statement_manifest_json"])
        baseline_coverage = {key: value == "complete" for key, value in json.loads(baseline.get("section_coverage_json", "{}")).items()}
        changes = compare_statement_manifests(baseline=baseline_manifest, current=current_manifest, scope_fingerprint=_hash(capture_scope), baseline_coverage=baseline_coverage)
        comparison = {"state": "available", "baseline_snapshot_id": baseline["snapshot_id"], "items": changes}
        sections["changes_since_previous_snapshot"] = _section("available", changes, [])
    else:
        code = "WEEKLY_BRIEF_BASELINE_DATA_ACCESS_FAILED" if baseline_error else "WEEKLY_BRIEF_BASELINE_NOT_AVAILABLE"
        sections["changes_since_previous_snapshot"] = _section("not_available", [], [code])

    achievement_items, achievement_limits = [], []
    if baseline:
        completed = list_action_records(statuses=["done"], completed_since=baseline["confirmed_at"], through=now, db_path=db_path)
        if completed["coverage"]["state"] != "complete":
            achievement_limits.extend(completed["coverage"]["limitation_codes"] or ["ACTION_COVERAGE_NOT_COMPLETE"])
        elif scope["kind"] == "global":
            achievement_items.extend({"kind": "action_completion", "action_id": item["action_id"], "completed_at": item["completed_at"]} for item in completed["items"] if item["completion_state"] == "known")
        else:
            achievement_limits.append("ACTION_PROJECT_SCOPE_NOT_PROVED")
        # The current execution reader lacks collection completeness metadata;
        # do not turn its bounded page into a complete achievement set.
        achievement_limits.append("EXECUTION_COVERAGE_NOT_PUBLISHED")
        achievement_items.sort(key=lambda item: (item.get("occurred_at", item.get("completed_at", "")), item.get("kind", ""), item.get("milestone_id", item.get("action_id", ""))))
        sections["achievements"] = _section("available" if not achievement_limits else "partial", achievement_items, achievement_limits)
    else:
        sections["achievements"] = _section("not_available", [], ["ACHIEVEMENT_WINDOW_BASELINE_NOT_AVAILABLE"])

    for statement in statements:
        comparison_item = next((item for item in comparison["items"] if item["identity_key"] == statement["statement_id"]), None)
        statement["change_state"] = comparison_item["change_state"] if comparison_item else "not_comparable"
        statement["changed"] = comparison_item["changed"] if comparison_item else False
        statement["evidence_changed"] = comparison_item["evidence_changed"] if comparison_item else False
    ordered = sorted(statements, key=lambda item: item["statement_id"])
    limitations = sorted({code for section in sections.values() for code in section["limitations"]})
    freshness_items = [{"producer": producer, "coverage": "complete" if complete else "partial"} for producer, complete in sorted(producer_coverage.items())]
    freshness_items.extend({"section": key, "availability": section["availability"]} for key, section in sections.items() if key != "freshness_and_limitations")
    sections["freshness_and_limitations"] = _section("partial" if limitations else "available", freshness_items, limitations)
    capture_input = {"as_of": now, "attention_limit": attention_limit, **({"plan_version_id": plan_version_id} if plan_version_id else {})}
    facts = [_fact(item) for item in ordered if item["producer"] in {"project_health", "execution", "resource_intelligence"}]
    facts.extend(_section_facts(sections, facts))
    signals = [_signal(item) for item in ordered if item["producer"] == "attention"]
    recommendations = [_recommendation(item) for item in ordered if item["producer"] == "action"]
    for item in ordered:
        item["fact_refs"] = [fact["fact_id"] for fact in facts if fact["statement_id"] == item["statement_id"]]
        item["signal_refs"] = [signal["signal_id"] for signal in signals if signal["statement_id"] == item["statement_id"]]
        item["recommendation_refs"] = [recommendation["recommendation_id"] for recommendation in recommendations if recommendation["statement_id"] == item["statement_id"]]
    _project_section_references(sections, ordered, facts)
    result_manifest = {"scope": scope, "comparison": comparison, "sections": sections, "facts": facts, "signals": signals, "recommendations": recommendations, "summary": {"project_count": len(ids), "overall_state": overall, "statement_count": len(ordered)}}
    candidate = _capture_candidate(now, capture_scope, capture_input, baseline, current_manifest, producer_coverage, limitations, facts + signals + recommendations, result_manifest)
    return {
        "week": now[:10], "brief": _markdown(sections), "brief_version": "2.0", "generated_at": now,
        "scope": scope, "comparison": comparison, "sections": sections,
        "facts": facts, "signals": signals, "recommendations": recommendations,
        "statements": ordered, "statement_manifest": current_manifest,
        "summary": {"project_count": len(ids), "overall_state": overall, "statement_count": len(ordered)},
        "snapshot": {"capture_state": "not_requested", "baseline_snapshot_id": baseline["snapshot_id"] if baseline else None, "capture_candidate": candidate},
    }


def _milestone_in_window(fact: dict[str, Any], confirmed_at: str, now: str) -> bool:
    """An achievement is event-date bounded, never derivation-run bounded."""
    if fact.get("fact_key") != "milestone_adherence" or fact.get("value") not in {"achieved_on_time", "achieved_late"}:
        return False
    if fact.get("event_time_state") != "known" or fact.get("completeness_state") != "complete" or fact.get("run_freshness_state") != "fresh":
        return False
    try:
        return date.fromisoformat(confirmed_at[:10]) < date.fromisoformat(fact["event_occurred_at"]) <= date.fromisoformat(now[:10])
    except (TypeError, ValueError):
        return False


def _resource_evidence_ids(item: dict[str, Any]) -> list[str]:
    evidence = item.get("evidence", {})
    allocation = evidence.get("allocation", {}) if isinstance(evidence, dict) else {}
    ids = [item["project_id"]]
    if isinstance(allocation, dict) and allocation.get("publication_id"):
        ids.append(str(allocation["publication_id"]))
    for derivation in evidence.get("capacity_derivations", []) if isinstance(evidence, dict) else []:
        if isinstance(derivation, dict) and derivation.get("derivation_id"):
            ids.append(str(derivation["derivation_id"]))
    return sorted(set(ids))


def _execution_evidence_ids(fact: dict[str, Any]) -> list[str]:
    ids = [str(fact[key]) for key in ("fact_id", "derivation_run_id") if fact.get(key)]
    for item in fact.get("input_ids", []):
        if isinstance(item, dict) and item.get("input_kind") and item.get("input_id"):
            ids.append(f"{item['input_kind']}-{item['input_id']}")
    return sorted(set(ids))


def _project_section_references(sections: dict[str, dict[str, Any]], statements: list[dict[str, Any]], facts: list[dict[str, Any]]) -> None:
    """Keep renderer-neutral section projections traceable to typed statements."""
    by_producer_subject = {(item["producer"], item["subject_id"]): item for item in statements}
    for item in sections["overall_health"]["items"]:
        _copy_refs(item, by_producer_subject.get(("project_health", item["project_id"])), facts)
    for item in sections["highest_attention_signals"]["items"]:
        statement = next((entry for entry in statements if entry["producer"] == "attention" and any(ref["source_id"] == _stable(item["attention_id"]) for ref in entry["evidence_refs"])), None)
        _copy_refs(item, statement, facts)
    for item in sections["resource_concerns"]["items"]:
        _copy_refs(item, by_producer_subject.get(("resource_intelligence", item["project_id"])), facts)
    for item in sections["next_actions"]["items"]:
        _copy_refs(item, by_producer_subject.get(("action", item["action_id"])), facts)


def _copy_refs(target: dict[str, Any], statement: dict[str, Any] | None, facts: list[dict[str, Any]]) -> None:
    target["fact_refs"] = list(statement["fact_refs"]) if statement else [fact["fact_id"] for fact in facts if fact["producer"] in {"project_health", "resource_intelligence"} and fact["subject_id"] == target.get("project_id")]
    target["signal_refs"] = list(statement["signal_refs"]) if statement else []
    target["recommendation_refs"] = list(statement["recommendation_refs"]) if statement else []


def _section_facts(sections: dict[str, dict[str, Any]], existing: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Add anonymous facts for non-material Health/Resource section items."""
    existing_keys = {(fact["producer"], fact["subject_id"]) for fact in existing}
    facts: list[dict[str, Any]] = []
    for producer, section, value_key in (("project_health", "overall_health", "state"), ("resource_intelligence", "resource_concerns", "state")):
        for item in sections[section]["items"]:
            project_id = item.get("project_id")
            if not project_id or (producer, project_id) in existing_keys:
                continue
            source_ids = [item["assessment_id"]] if producer == "project_health" and item.get("assessment_id") else _resource_evidence_ids(item) if producer == "resource_intelligence" else []
            facts.append({"fact_id": f"fact-{producer}-{project_id}", "statement_id": None, "producer": producer, "subject_id": project_id, "value_state": item.get(value_key, "unknown"), "evidence_refs": [{"evidence_id": "weekly-brief-" + _stable(source_id), "producer": producer, "source_id": _stable(source_id)} for source_id in source_ids], "freshness_refs": [{"state": "not_available", "reason_code": "PROJECT_HEALTH_FRESHNESS_NOT_PUBLISHED" if producer == "project_health" else "RESOURCE_FRESHNESS_NOT_PUBLISHED"}]})
    return facts


def _capture_candidate(now: str, scope: dict[str, Any], inputs: dict[str, Any], baseline: dict[str, Any] | None, manifest: list[dict[str, Any]], coverage: dict[str, bool], limitations: list[str], typed_items: list[dict[str, Any]], result_manifest: dict[str, Any]) -> dict[str, Any]:
    evidence_ids = sorted({ref["evidence_id"] for item in typed_items for ref in item["evidence_refs"]})
    return {"execution_id": "weekly-v2-execution-" + _hash({"scope": scope, "input": inputs})[:20], "contract_version": _CONTRACT_VERSION, "comparison_rule_version": _RULE_VERSION, "generated_at": now, "week_key": now[:10], "scope": scope, "input": inputs, "baseline_snapshot_id": baseline["snapshot_id"] if baseline else "", "baseline_fingerprint": baseline["result_fingerprint"] if baseline else "", "statement_manifest": manifest, "evidence_summary": {"producer": "weekly-brief-composer", "evidence_ids": evidence_ids, "freshness_states": ["partial"] if any(not value for value in coverage.values()) else ["fresh"]}, "section_coverage": {producer: "complete" if complete else "partial" for producer, complete in coverage.items()}, "limitation_codes": limitations, "result_manifest": _hash(result_manifest)}


def _section(availability: str, items: list[dict[str, Any]], limitations: list[str], *, before_count: int | None = None, **extra: Any) -> dict[str, Any]:
    return {"availability": availability, "items": items, "counts": {"before_limit": len(items) if before_count is None else before_count, "after_limit": len(items)}, "limitations": sorted(set(limitations)), **extra}


def _statement(section: str, producer: str, subject_id: str, fact_type: str, active: bool, transition: str, value: dict[str, Any], evidence_ids: list[str], freshness_refs: list[dict[str, Any]]) -> dict[str, Any]:
    identity = ":".join(_stable(part) for part in (section, producer, subject_id, fact_type))
    evidence_refs = [{"evidence_id": "weekly-brief-" + _stable(evidence_id), "producer": producer, "source_id": _stable(evidence_id)} for evidence_id in sorted(evidence_ids)]
    if not freshness_refs and producer != "action":
        code = {
            "project_health": "PROJECT_HEALTH_FRESHNESS_NOT_PUBLISHED",
            "resource_intelligence": "RESOURCE_FRESHNESS_NOT_PUBLISHED",
            "execution": "EXECUTION_COVERAGE_NOT_PUBLISHED",
            "attention": "ATTENTION_FRESHNESS_NOT_PUBLISHED",
        }.get(producer, "WEEKLY_BRIEF_FRESHNESS_NOT_PUBLISHED")
        freshness_refs = [{"state": "not_available", "reason_code": code}]
    subject_kind = {"project_health": "project", "resource_intelligence": "project", "attention": "attention", "action": "action"}.get(producer, "execution")
    return {"statement_id": identity, "section": section, "producer": producer, "subject_kind": subject_kind, "subject_id": subject_id, "fact_type": fact_type, "normalized_value": value, "value_state": "known", "reason_codes": [], "active_material": active, "transition_state": transition, "semantic_fingerprint": _hash(value), "evidence_state_fingerprint": _hash({"evidence_refs": evidence_refs, "freshness_refs": freshness_refs}), "evidence_ids": [item["evidence_id"] for item in evidence_refs], "evidence_refs": evidence_refs, "freshness_refs": freshness_refs, "fact_refs": [], "signal_refs": [], "recommendation_refs": []}


def _manifest_statements(statements: list[dict[str, Any]], scope: dict[str, Any], producer_coverage: dict[str, bool]) -> list[dict[str, Any]]:
    scope_fingerprint = _hash(scope)
    return [{"identity_key": item["statement_id"], "producer": item["producer"], "scope_fingerprint": scope_fingerprint, "semantic_fingerprint": item["semantic_fingerprint"], "evidence_state_fingerprint": item["evidence_state_fingerprint"], "active_material": item["active_material"], "transition_state": item["transition_state"], "coverage_complete": producer_coverage.get(item["producer"], False), "usable_evidence": bool(item["evidence_refs"]) and producer_coverage.get(item["producer"], False), "limited_active_proven": item["active_material"] and bool(item["evidence_refs"]) and producer_coverage.get(item["producer"], False)} for item in sorted(statements, key=lambda value: value["statement_id"])]


def _fact(item: dict[str, Any]) -> dict[str, Any]:
    return {"fact_id": "fact-" + item["statement_id"], "statement_id": item["statement_id"], "producer": item["producer"], "subject_id": item["subject_id"], "value_state": item["value_state"], "evidence_refs": item["evidence_refs"], "freshness_refs": item["freshness_refs"]}


def _signal(item: dict[str, Any]) -> dict[str, Any]:
    return {"signal_id": "signal-" + item["statement_id"], "statement_id": item["statement_id"], "producer": item["producer"], "subject_id": item["subject_id"], "severity": item["normalized_value"].get("severity", "unknown"), "evidence_refs": item["evidence_refs"], "freshness_refs": item["freshness_refs"]}


def _recommendation(item: dict[str, Any]) -> dict[str, Any]:
    return {"recommendation_id": "recommendation-" + item["statement_id"], "statement_id": item["statement_id"], "producer": "action", "subject_id": item["subject_id"], "evidence_refs": item["evidence_refs"], "freshness_refs": item["freshness_refs"]}


def _markdown(sections: dict[str, dict[str, Any]]) -> str:
    return "\n".join(f"## {key}\n{section['availability']}: {section['counts']['after_limit']}" for key, section in sections.items())


def _hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _stable(value: str) -> str:
    return str(value).replace("_", "-")


def _unavailable(now: str, scope: dict[str, Any], code: str) -> dict[str, Any]:
    sections = {key: _section("not_available", [], [code]) for key in _SECTIONS}
    return {"week": now[:10], "brief": _markdown(sections), "brief_version": "2.0", "generated_at": now, "scope": scope, "comparison": {"state": "not_available", "baseline_snapshot_id": None, "items": []}, "sections": sections, "facts": [], "signals": [], "recommendations": [], "statements": [], "statement_manifest": [], "summary": {"project_count": 0, "overall_state": "unknown", "statement_count": 0}, "snapshot": {"capture_state": "not_requested"}}
