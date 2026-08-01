from __future__ import annotations

import json

from pm_agent.weekly_brief import composer
from pm_agent.weekly_brief.snapshots import _normalized
from pm_agent.weekly_brief.snapshots import WeeklyBriefSnapshotService
from pm_agent.database.bootstrap import main as init_db


def _manifest() -> dict:
    return {"scope": {"kind": "projects", "project_ids": ["project-synthetic-001"]}, "projects": [{"project_id": "project-synthetic-001"}], "coverage": {"state": "complete"}}


def test_composer_emits_all_nine_sections_and_explicit_unavailable_contracts(monkeypatch) -> None:
    monkeypatch.setattr(composer, "active_project_manifest", lambda **_kwargs: _manifest())
    monkeypatch.setattr(composer, "current_attention", lambda **_kwargs: {"items": [], "reconciliation_coverage": {"status": "complete"}})
    monkeypatch.setattr(composer, "latest_assessments", lambda **_kwargs: [])
    monkeypatch.setattr(composer, "list_action_records", lambda **_kwargs: {"items": [], "coverage": {"state": "complete", "limitation_codes": []}})
    monkeypatch.setattr(composer, "list_latest_execution_facts", lambda *_args, **_kwargs: [])
    result = composer.compose_weekly_brief_v2(generated_at="2026-08-01T00:00:00Z")
    assert result["brief_version"] == "2.0"
    assert set(result["sections"]) == set(composer._SECTIONS)
    assert result["sections"]["decisions_required"]["limitations"] == ["DECISION_REQUIRED_DEFINITION_NOT_AVAILABLE"]
    assert result["sections"]["resource_concerns"]["availability"] == "not_available"
    assert result["sections"]["changes_since_previous_snapshot"]["availability"] == "not_available"
    assert result["sections"]["overall_health"]["overall"] == "unknown"
    assert _normalized(result["snapshot"]["capture_candidate"])["scope"] == {"kind": "projects", "project_ids": ["project-synthetic-001"]}


def test_composer_uses_only_explicit_project_attention_association(monkeypatch) -> None:
    monkeypatch.setattr(composer, "active_project_manifest", lambda **_kwargs: _manifest())
    monkeypatch.setattr(composer, "latest_assessments", lambda **_kwargs: [])
    monkeypatch.setattr(composer, "list_action_records", lambda **_kwargs: {"items": [], "coverage": {"state": "complete", "limitation_codes": []}})
    monkeypatch.setattr(composer, "list_latest_execution_facts", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(composer, "current_attention", lambda **_kwargs: {"reconciliation_coverage": {"status": "complete"}, "items": [{"attention_id": "attention-synthetic-001", "severity": "high", "rule_key": "project_health_attention", "rule_version": "v1", "subject": {"id": "project-synthetic-001"}, "project_association": {"state": "known", "project_id": "project-synthetic-001"}}, {"attention_id": "attention-synthetic-002", "severity": "high", "rule_key": "source_freshness_attention", "rule_version": "v1", "subject": {"id": "source-synthetic-001"}, "project_association": {"state": "unavailable", "project_id": None}}]})
    result = composer.compose_weekly_brief_v2(generated_at="2026-08-01T00:00:00Z")
    assert [item["attention_id"] for item in result["sections"]["highest_attention_signals"]["items"]] == ["attention-synthetic-001"]
    assert _normalized(result["snapshot"]["capture_candidate"])["statement_manifest"]


def test_incomplete_manifest_makes_every_section_not_available(monkeypatch) -> None:
    monkeypatch.setattr(composer, "active_project_manifest", lambda **_kwargs: {"scope": {"kind": "global", "project_ids": []}, "projects": [], "coverage": {"state": "unavailable"}})
    result = composer.compose_weekly_brief_v2(generated_at="2026-08-01T00:00:00Z")
    assert {section["availability"] for section in result["sections"].values()} == {"not_available"}


def test_project_scoped_actions_need_explicit_project_association(monkeypatch) -> None:
    monkeypatch.setattr(composer, "active_project_manifest", lambda **_kwargs: _manifest())
    monkeypatch.setattr(composer, "current_attention", lambda **_kwargs: {"items": [], "reconciliation_coverage": {"status": "complete"}})
    monkeypatch.setattr(composer, "latest_assessments", lambda **_kwargs: [])
    monkeypatch.setattr(composer, "list_latest_execution_facts", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(composer, "list_action_records", lambda **_kwargs: {"coverage": {"state": "complete", "limitation_codes": []}, "items": [{"action_id": "action-synthetic-001", "severity": "high", "follow_up_reasons": ["overdue"], "project_association": {"state": "unavailable", "project_id": None}}]})
    result = composer.compose_weekly_brief_v2(generated_at="2026-08-01T00:00:00Z")
    assert result["sections"]["next_actions"]["items"] == []
    assert result["sections"]["next_actions"]["limitations"] == ["ACTION_PROJECT_SCOPE_NOT_PROVED"]


def test_confirmed_same_scope_baseline_enables_fail_closed_comparison(monkeypatch) -> None:
    monkeypatch.setattr(composer, "active_project_manifest", lambda **_kwargs: _manifest())
    monkeypatch.setattr(composer, "latest_assessments", lambda **_kwargs: [])
    monkeypatch.setattr(composer, "list_action_records", lambda **_kwargs: {"items": [], "coverage": {"state": "complete", "limitation_codes": []}})
    monkeypatch.setattr(composer, "list_latest_execution_facts", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(composer, "current_attention", lambda **_kwargs: {"reconciliation_coverage": {"status": "complete"}, "items": [{"attention_id": "attention-synthetic-001", "severity": "high", "rule_key": "project_health_attention", "rule_version": "v1", "subject": {"id": "project-synthetic-001"}, "project_association": {"state": "known", "project_id": "project-synthetic-001"}}]})
    monkeypatch.setattr(composer.snapshot_repository, "latest_confirmed", lambda *_args, **_kwargs: None)
    first = composer.compose_weekly_brief_v2(generated_at="2026-08-01T00:00:00Z")
    monkeypatch.setattr(composer.snapshot_repository, "latest_confirmed", lambda *_args, **_kwargs: {"snapshot_id": "weekly-brief-snapshot-synthetic-001", "result_fingerprint": "a" * 64, "confirmed_at": "2026-07-25T00:00:00Z", "statement_manifest_json": json.dumps(first["statement_manifest"])})
    second = composer.compose_weekly_brief_v2(generated_at="2026-08-01T00:00:00Z")
    assert second["sections"]["changes_since_previous_snapshot"]["availability"] == "available"
    assert {item["change_state"] for item in second["sections"]["changes_since_previous_snapshot"]["items"]} == {"continuing"}


def test_clean_bootstrap_composition_is_fail_closed(isolated_db) -> None:
    init_db(quiet=True)
    result = composer.compose_weekly_brief_v2(
        generated_at="2026-08-01T00:00:00Z", db_path=isolated_db
    )
    assert result["brief_version"] == "2.0"
    assert result["summary"]["overall_state"] == "unknown"
    assert result["sections"]["overall_health"]["availability"] == "not_available"


def test_statement_contract_has_anonymous_evidence_reference_chains(monkeypatch) -> None:
    monkeypatch.setattr(composer, "active_project_manifest", lambda **_kwargs: _manifest())
    monkeypatch.setattr(composer, "latest_assessments", lambda **_kwargs: [{"project_id": "project-synthetic-001", "assessment_run_id": "health-run-synthetic-001", "state": "red"}])
    monkeypatch.setattr(composer, "current_attention", lambda **_kwargs: {"items": [], "reconciliation_coverage": {"status": "complete"}})
    monkeypatch.setattr(composer, "list_action_records", lambda **_kwargs: {"items": [], "coverage": {"state": "complete", "limitation_codes": []}})
    monkeypatch.setattr(composer, "list_latest_execution_facts", lambda *_args, **_kwargs: [])
    result = composer.compose_weekly_brief_v2(generated_at="2026-08-01T00:00:00Z")
    statement = result["statements"][0]
    assert statement["evidence_refs"] == [{"evidence_id": "weekly-brief-health-run-synthetic-001", "producer": "project_health", "source_id": "health-run-synthetic-001"}]
    assert result["facts"][0]["statement_id"] == statement["statement_id"]
    assert statement["fact_refs"] == [result["facts"][0]["fact_id"]]
    assert statement["freshness_refs"] == [{"state": "not_available", "reason_code": "PROJECT_HEALTH_FRESHNESS_NOT_PUBLISHED"}]
    assert result["comparison"]["state"] == "not_available"
    assert "PROJECT_HEALTH_FRESHNESS_NOT_PUBLISHED" in result["sections"]["overall_health"]["limitations"]


def test_milestone_achievement_is_withheld_without_execution_collection_coverage(monkeypatch) -> None:
    monkeypatch.setattr(composer, "active_project_manifest", lambda **_kwargs: _manifest())
    monkeypatch.setattr(composer, "latest_assessments", lambda **_kwargs: [])
    monkeypatch.setattr(composer, "current_attention", lambda **_kwargs: {"items": [], "reconciliation_coverage": {"status": "complete"}})
    monkeypatch.setattr(composer, "list_action_records", lambda **_kwargs: {"items": [], "coverage": {"state": "complete", "limitation_codes": []}})
    fact = {"subject_kind": "milestone", "subject_id": "milestone-synthetic-001", "fact_key": "milestone_adherence", "value": "achieved_on_time", "value_state": "known", "event_time_state": "known", "event_occurred_at": "2026-07-30", "completeness_state": "complete", "run_freshness_state": "fresh", "derivation_run_id": "run-synthetic-001"}
    monkeypatch.setattr(composer, "list_latest_execution_facts", lambda *_args, **_kwargs: [fact])
    monkeypatch.setattr(composer.snapshot_repository, "latest_confirmed", lambda *_args, **_kwargs: {"snapshot_id": "weekly-brief-snapshot-synthetic-001", "result_fingerprint": "a" * 64, "confirmed_at": "2026-07-25T00:00:00Z", "statement_manifest_json": "[]", "section_coverage_json": "{}"})
    result = composer.compose_weekly_brief_v2(generated_at="2026-08-01T00:00:00Z")
    assert result["sections"]["achievements"]["items"] == []
    assert "EXECUTION_COVERAGE_NOT_PUBLISHED" in result["sections"]["achievements"]["limitations"]
    fact["event_occurred_at"] = "2026-07-20"
    outside = composer.compose_weekly_brief_v2(generated_at="2026-08-01T00:00:00Z")
    assert outside["sections"]["achievements"]["items"] == []


def test_explicit_baseline_must_be_same_scope_and_version(monkeypatch) -> None:
    monkeypatch.setattr(composer, "active_project_manifest", lambda **_kwargs: _manifest())
    monkeypatch.setattr(composer, "latest_assessments", lambda **_kwargs: [])
    monkeypatch.setattr(composer, "current_attention", lambda **_kwargs: {"items": [], "reconciliation_coverage": {"status": "complete"}})
    monkeypatch.setattr(composer, "list_action_records", lambda **_kwargs: {"items": [], "coverage": {"state": "complete", "limitation_codes": []}})
    monkeypatch.setattr(composer, "list_latest_execution_facts", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(composer.snapshot_repository, "load_confirmed_snapshot", lambda *_args, **_kwargs: {"snapshot_id": "weekly-brief-snapshot-other", "scope_fingerprint": "wrong", "comparison_rule_version": "weekly-brief-comparison-v2", "contract_version": "weekly-brief-v2"})
    result = composer.compose_weekly_brief_v2(generated_at="2026-08-01T00:00:00Z", baseline_snapshot_id="weekly-brief-snapshot-other")
    assert result["comparison"]["state"] == "not_available"
    assert result["sections"]["changes_since_previous_snapshot"]["limitations"] == ["WEEKLY_BRIEF_BASELINE_INVALID"]
    assert "capture_candidate" not in result["snapshot"]


def test_adapter_rehearses_b2_preview_confirm_with_exact_recomposition(monkeypatch, isolated_db) -> None:
    init_db(quiet=True)
    monkeypatch.setattr(composer, "active_project_manifest", lambda **_kwargs: _manifest())
    monkeypatch.setattr(composer, "latest_assessments", lambda **_kwargs: [])
    monkeypatch.setattr(composer, "current_attention", lambda **_kwargs: {"items": [], "reconciliation_coverage": {"status": "complete"}})
    monkeypatch.setattr(composer, "list_action_records", lambda **_kwargs: {"items": [], "coverage": {"state": "complete", "limitation_codes": []}})
    monkeypatch.setattr(composer, "list_latest_execution_facts", lambda *_args, **_kwargs: [])
    adapter = composer.WeeklyBriefQueryAdapter(db_path=isolated_db)
    result = adapter.compose(generated_at="2026-08-01T00:00:00Z")
    candidate = result["snapshot"]["capture_candidate"]
    service = WeeklyBriefSnapshotService(query_lookup=adapter.query_lookup, recompose=adapter.recompose, db_path=isolated_db, clock=lambda: "2026-08-01T00:00:00Z")
    preview = service.preview(candidate=candidate, actor_id="actor-synthetic-001", idempotency_key="b3-adapter-synthetic-001")
    assert preview["status"] == "previewed"
    assert service.confirm(operation_id=preview["operation_id"], confirmation_token=preview["confirmation_token"])["status"] == "confirmed"


def test_attention_reader_truncation_is_never_treated_as_complete(monkeypatch) -> None:
    monkeypatch.setattr(composer, "active_project_manifest", lambda **_kwargs: _manifest())
    monkeypatch.setattr(composer, "latest_assessments", lambda **_kwargs: [])
    monkeypatch.setattr(composer, "list_action_records", lambda **_kwargs: {"items": [], "coverage": {"state": "complete", "limitation_codes": []}})
    monkeypatch.setattr(composer, "list_latest_execution_facts", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(composer, "current_attention", lambda **_kwargs: {"items": [], "summary": {"matched_count": 201, "returned_count": 200, "truncated": True}, "reconciliation_coverage": {"status": "complete"}})
    result = composer.compose_weekly_brief_v2(generated_at="2026-08-01T00:00:00Z")
    section = result["sections"]["highest_attention_signals"]
    assert section["availability"] == "partial"
    assert "ATTENTION_RESULT_TRUNCATED" in section["limitations"]
    assert result["snapshot"]["capture_candidate"]["section_coverage"]["attention"] == "partial"


def test_resource_and_execution_statements_keep_exact_public_evidence_ids() -> None:
    resource = composer._resource_evidence_ids({"project_id": "project-synthetic-001", "evidence": {"allocation": {"publication_id": "workforce-publication-synthetic-001"}, "capacity_derivations": [{"derivation_id": "capacity-derivation-synthetic-001"}]}})
    execution = composer._execution_evidence_ids({"fact_id": "execution-fact-synthetic-001", "derivation_run_id": "execution-run-synthetic-001", "input_ids": [{"input_kind": "milestone", "input_id": "milestone-synthetic-001"}]})
    assert resource == ["capacity-derivation-synthetic-001", "project-synthetic-001", "workforce-publication-synthetic-001"]
    assert execution == ["execution-fact-synthetic-001", "execution-run-synthetic-001", "milestone-milestone-synthetic-001"]


def test_section_items_project_typed_reference_chains(monkeypatch) -> None:
    monkeypatch.setattr(composer, "active_project_manifest", lambda **_kwargs: _manifest())
    monkeypatch.setattr(composer, "latest_assessments", lambda **_kwargs: [{"project_id": "project-synthetic-001", "assessment_run_id": "health-run-synthetic-001", "state": "red"}])
    monkeypatch.setattr(composer, "current_attention", lambda **_kwargs: {"items": [{"attention_id": "attention-synthetic-001", "severity": "high", "rule_key": "project-health-attention", "rule_version": "v1", "subject": {"id": "project-synthetic-001"}, "project_association": {"state": "known", "project_id": "project-synthetic-001"}}], "reconciliation_coverage": {"status": "complete"}})
    monkeypatch.setattr(composer, "list_action_records", lambda **_kwargs: {"items": [{"action_id": "action-synthetic-001", "severity": "high", "follow_up_reasons": ["overdue"], "project_association": {"state": "known", "project_id": "project-synthetic-001"}}], "coverage": {"state": "complete", "limitation_codes": []}})
    monkeypatch.setattr(composer, "list_latest_execution_facts", lambda *_args, **_kwargs: [])
    result = composer.compose_weekly_brief_v2(generated_at="2026-08-01T00:00:00Z")
    assert result["sections"]["overall_health"]["items"][0]["fact_refs"]
    assert result["sections"]["highest_attention_signals"]["items"][0]["signal_refs"]
    assert result["sections"]["next_actions"]["items"][0]["recommendation_refs"]


def test_result_fingerprint_covers_nonstatement_structured_drift(monkeypatch) -> None:
    monkeypatch.setattr(composer, "active_project_manifest", lambda **_kwargs: _manifest())
    monkeypatch.setattr(composer, "latest_assessments", lambda **_kwargs: [{"project_id": "project-synthetic-001", "assessment_run_id": "health-run-synthetic-001", "state": "green"}])
    monkeypatch.setattr(composer, "current_attention", lambda **_kwargs: {"items": [], "reconciliation_coverage": {"status": "complete"}})
    monkeypatch.setattr(composer, "list_action_records", lambda **_kwargs: {"items": [], "coverage": {"state": "complete", "limitation_codes": []}})
    monkeypatch.setattr(composer, "list_latest_execution_facts", lambda *_args, **_kwargs: [])
    composed = composer.compose_weekly_brief_v2(generated_at="2026-08-01T00:00:00Z")
    candidate = composed["snapshot"]["capture_candidate"]
    assert candidate["result_manifest"]
    assert composed["sections"]["overall_health"]["items"][0]["fact_refs"]
    monkeypatch.setattr(composer, "latest_assessments", lambda **_kwargs: [{"project_id": "project-synthetic-001", "assessment_run_id": "health-run-synthetic-002", "state": "green"}])
    changed = composer.compose_weekly_brief_v2(generated_at="2026-08-01T00:00:00Z")["snapshot"]["capture_candidate"]
    assert _normalized(candidate)["result_fingerprint"] != _normalized(changed)["result_fingerprint"]


def test_result_manifest_rejects_nested_or_sensitive_payloads(monkeypatch) -> None:
    monkeypatch.setattr(composer, "active_project_manifest", lambda **_kwargs: _manifest())
    monkeypatch.setattr(composer, "latest_assessments", lambda **_kwargs: [])
    monkeypatch.setattr(composer, "current_attention", lambda **_kwargs: {"items": [], "reconciliation_coverage": {"status": "complete"}})
    monkeypatch.setattr(composer, "list_action_records", lambda **_kwargs: {"items": [], "coverage": {"state": "complete", "limitation_codes": []}})
    monkeypatch.setattr(composer, "list_latest_execution_facts", lambda *_args, **_kwargs: [])
    candidate = composer.compose_weekly_brief_v2(generated_at="2026-08-01T00:00:00Z")["snapshot"]["capture_candidate"]
    invalid = {**candidate, "result_manifest": {"raw_payload": "secret"}}
    try:
        _normalized(invalid)
    except ValueError:
        pass
    else:
        raise AssertionError("nested result manifest must be rejected")
