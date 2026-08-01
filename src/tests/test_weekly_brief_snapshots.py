from __future__ import annotations

import sqlite3
from pathlib import Path

from pm_agent.database.bootstrap import main as init_db
from pm_agent.weekly_brief import repository
from pm_agent.weekly_brief.comparison import compare_statement_manifests
from pm_agent.weekly_brief.snapshots import WeeklyBriefSnapshotService


def _candidate(*, result_marker: str = "a") -> dict:
    return {"execution_id": "weekly-v2-execution-synthetic-001", "contract_version": "weekly-brief-v2", "comparison_rule_version": "weekly-brief-comparison-v2", "generated_at": "2026-08-01T00:00:00Z", "week_key": "2026-W31", "scope": {"project_ids": ["project-synthetic-001"]}, "input": {"as_of": "2026-08-01T00:00:00Z"}, "baseline_snapshot_id": "", "baseline_fingerprint": "", "statement_manifest": [{"identity_key": "attention:synthetic-001", "producer": "attention", "scope_fingerprint": "6aea5364bcf8ff86511c5fe530ff5228ddc8da971564ab1732e34eaf9ba554eb", "semantic_fingerprint": result_marker[0] * 64, "evidence_state_fingerprint": "e" * 64, "active_material": True, "transition_state": "active", "coverage_complete": True, "usable_evidence": True, "limited_active_proven": True}], "evidence_summary": {"producer": "synthetic-public-contract"}, "section_coverage": {"attention": "complete"}, "limitation_codes": []}


def _service(db: Path, candidate: dict, *, now: list[str] | None = None) -> WeeklyBriefSnapshotService:
    values = now or ["2026-08-01T00:00:00Z"]
    return WeeklyBriefSnapshotService(query_lookup=lambda execution_id: candidate if execution_id == candidate["execution_id"] else None, recompose=lambda _candidate: candidate, db_path=db, clock=lambda: values[0])


def test_preview_confirm_is_hashed_immutable_and_idempotent(isolated_db: Path) -> None:
    init_db(quiet=True)
    candidate = _candidate()
    service = _service(isolated_db, candidate)
    preview = service.preview(candidate=candidate, actor_id="actor-synthetic-001", idempotency_key="capture-synthetic-001")
    assert preview["status"] == "previewed"
    assert preview["confirmation_token"]
    stored = repository.load_operation(preview["operation_id"], db_path=isolated_db)
    assert stored and preview["confirmation_token"] not in str(stored.values())
    confirmed = service.confirm(operation_id=preview["operation_id"], confirmation_token=preview["confirmation_token"])
    assert confirmed["status"] == "confirmed"
    replay = service.confirm(operation_id=preview["operation_id"], confirmation_token=preview["confirmation_token"])
    assert replay["status"] == "already_confirmed"
    assert replay["confirmed_snapshot_id"] == confirmed["confirmed_snapshot_id"]
    assert repository.integrity_report(db_path=isolated_db)["state"] == "passed"


def test_capture_rejects_unknown_stale_expired_and_bad_token(isolated_db: Path) -> None:
    init_db(quiet=True)
    candidate = _candidate()
    service = _service(isolated_db, candidate)
    assert service.preview(candidate={**candidate, "execution_id": "unknown"}, actor_id="actor-synthetic-001", idempotency_key="unknown")["warnings"] == ["WEEKLY_BRIEF_CAPTURE_CANDIDATE_INVALID"]
    preview = service.preview(candidate=candidate, actor_id="actor-synthetic-001", idempotency_key="token")
    assert service.confirm(operation_id=preview["operation_id"], confirmation_token="bad")["warnings"] == ["WEEKLY_BRIEF_CAPTURE_TOKEN_INVALID"]
    stale_preview = service.preview(candidate=candidate, actor_id="actor-synthetic-001", idempotency_key="stale")
    stale = _candidate(result_marker="changed")
    stale_service = _service(isolated_db, stale)
    assert stale_service.confirm(operation_id=stale_preview["operation_id"], confirmation_token=stale_preview["confirmation_token"])["status"] == "stale"
    clock = ["2026-08-01T00:00:00Z"]
    expiry_service = _service(isolated_db, candidate, now=clock)
    expiring = expiry_service.preview(candidate=candidate, actor_id="actor-synthetic-001", idempotency_key="expired", expires_in_seconds=1)
    clock[0] = "2026-08-01T00:00:02Z"
    assert expiry_service.confirm(operation_id=expiring["operation_id"], confirmation_token=expiring["confirmation_token"])["status"] == "expired"


def test_candidate_privacy_callback_and_integrity_fail_closed(isolated_db: Path) -> None:
    init_db(quiet=True)
    candidate = _candidate()
    service = _service(isolated_db, candidate)
    for key in ("operational_name", "source_payload", "api_key"):
        altered = {**candidate, "input": {**candidate["input"], key: "secret"}}
        assert service.preview(candidate=altered, actor_id="actor-synthetic-001", idempotency_key="privacy-test")['status'] == "failed"
    failing = WeeklyBriefSnapshotService(query_lookup=lambda _execution_id: (_ for _ in ()).throw(RuntimeError("raw")), recompose=lambda _candidate: candidate, db_path=isolated_db)
    assert failing.preview(candidate=candidate, actor_id="actor-synthetic-001", idempotency_key="callback-test")["warnings"] == ["WEEKLY_BRIEF_CAPTURE_DATA_ACCESS_FAILED"]
    preview = service.preview(candidate=candidate, actor_id="actor-synthetic-001", idempotency_key="integrity-test")
    assert service.confirm(operation_id=preview["operation_id"], confirmation_token=preview["confirmation_token"])["status"] == "confirmed"
    connection = sqlite3.connect(isolated_db)
    connection.execute("UPDATE weekly_brief_snapshot_operations SET result_fingerprint=?", ["b" * 64])
    connection.commit()
    connection.close()
    assert repository.integrity_report(db_path=isolated_db)["state"] == "failed"


def test_baseline_reference_is_checked_before_capture(isolated_db: Path) -> None:
    init_db(quiet=True)
    candidate = _candidate()
    invalid = {**candidate, "baseline_snapshot_id": "weekly-brief-snapshot-missing", "baseline_fingerprint": "a" * 64}
    service = _service(isolated_db, invalid)
    assert service.preview(candidate=invalid, actor_id="actor-synthetic-001", idempotency_key="baseline-test")["status"] == "failed"


def test_invalid_evidence_envelope_is_candidate_invalid(isolated_db: Path) -> None:
    init_db(quiet=True)
    candidate = {**_candidate(), "evidence_summary": []}
    service = _service(isolated_db, candidate)
    assert service.preview(candidate=candidate, actor_id="actor-synthetic-001", idempotency_key="evidence-test")["warnings"] == ["WEEKLY_BRIEF_CAPTURE_CANDIDATE_INVALID"]


def test_unknown_top_level_capture_field_is_rejected(isolated_db: Path) -> None:
    init_db(quiet=True)
    candidate = {**_candidate(), "source_payload": "must-not-persist"}
    service = _service(isolated_db, candidate)
    assert service.preview(candidate=candidate, actor_id="actor-synthetic-001", idempotency_key="envelope-test")["warnings"] == ["WEEKLY_BRIEF_CAPTURE_CANDIDATE_INVALID"]


def test_confirm_cannot_finish_after_claim_expiry(isolated_db: Path) -> None:
    init_db(quiet=True)
    candidate = _candidate()
    clock = ["2026-08-01T00:00:00Z"]
    service = WeeklyBriefSnapshotService(query_lookup=lambda _execution_id: candidate, recompose=lambda _candidate: (clock.__setitem__(0, "2026-08-01T00:00:02Z") or candidate), db_path=isolated_db, clock=lambda: clock[0])
    preview = service.preview(candidate=candidate, actor_id="actor-synthetic-001", idempotency_key="expiry-claim-test", expires_in_seconds=1)
    assert service.confirm(operation_id=preview["operation_id"], confirmation_token=preview["confirmation_token"])["status"] == "expired"


def test_bootstrap_is_additive_and_legacy_weekly_brief_is_untouched(isolated_db: Path) -> None:
    init_db(quiet=True)
    connection = sqlite3.connect(isolated_db)
    try:
        assert connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='weekly_brief_snapshot_operations'").fetchone()
        assert connection.execute("SELECT COUNT(*) FROM weekly_brief_snapshot_operations").fetchone()[0] == 0
    finally:
        connection.close()


def test_comparison_is_fail_closed_for_missing_or_limited_evidence() -> None:
    baseline = [{"identity_key": "attention:synthetic-001", "producer": "attention", "scope_fingerprint": "scope", "semantic_fingerprint": "a", "evidence_state_fingerprint": "e1", "active_material": True, "transition_state": "active", "coverage_complete": True, "usable_evidence": True, "limited_active_proven": True}]
    continuing = [{**baseline[0], "semantic_fingerprint": "b", "evidence_state_fingerprint": "e2"}]
    assert compare_statement_manifests(baseline=baseline, current=continuing, scope_fingerprint="scope") == [{"identity_key": "attention:synthetic-001", "change_state": "continuing", "changed": True, "evidence_changed": True}]
    assert compare_statement_manifests(baseline=None, current=continuing, scope_fingerprint="scope")[0]["change_state"] == "not_comparable"
    assert compare_statement_manifests(baseline=[], current=continuing, scope_fingerprint="scope")[0]["change_state"] == "not_comparable"
    assert compare_statement_manifests(baseline=[], current=continuing, scope_fingerprint="scope", baseline_coverage={"attention": True})[0]["change_state"] == "new"
    assert compare_statement_manifests(baseline=baseline, current=[], scope_fingerprint="scope")[0]["change_state"] == "not_comparable"
    limited = [{**baseline[0], "coverage_complete": False}]
    assert compare_statement_manifests(baseline=baseline, current=limited, scope_fingerprint="scope")[0]["change_state"] == "continuing"
