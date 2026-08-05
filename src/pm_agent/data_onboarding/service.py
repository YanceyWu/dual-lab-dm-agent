"""Shared profile/preview/confirm service for structured data onboarding."""

from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from pm_agent.data_onboarding.models import DomainLinkRecord, SourceProfileRecord, SourceProfileUpsert
from pm_agent.data_onboarding import repository
from pm_agent.data_onboarding.registry import get_handler
from pm_agent.rules.identity import slugify_text


def save_source_profile(
    *,
    profile_key: str,
    source_type: str,
    source_locator: str,
    display_name: str = "",
    mapping_preset_id: str = "",
    member_key_type: str = "",
    project_key_type: str = "",
    baseline_source: str = "",
    adjustment_source: str = "",
    conflict_policy: str = "",
    plan_naming_policy: str = "",
    status: str = "active",
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    normalized_key = _normalize_profile_key(profile_key)
    normalized_source_type = (source_type or "").strip().lower()
    if not normalized_source_type:
        raise ValueError("DATA_ONBOARDING_SOURCE_TYPE_REQUIRED")
    handler = get_handler(normalized_source_type)
    draft = SourceProfileUpsert(
        profile_id=f"data-onboarding-profile-{normalized_key}",
        profile_key=normalized_key,
        display_name=display_name.strip() or normalized_key,
        source_type=normalized_source_type,
        source_locator=source_locator.strip(),
        mapping_preset_id=mapping_preset_id.strip(),
        member_key_type=member_key_type.strip(),
        project_key_type=project_key_type.strip(),
        baseline_source=baseline_source.strip(),
        adjustment_source=adjustment_source.strip(),
        conflict_policy=conflict_policy.strip(),
        plan_naming_policy=plan_naming_policy.strip(),
        source_options={},
        status=_normalize_profile_status(status),
    )
    saved = repository.save_profile(
        handler.validate_profile(draft),
        db_path=db_path,
    )
    return {"status": "saved", "profile": _serialize_profile(saved)}


def show_source_profile(
    profile_key: str, *, db_path: str | Path | None = None
) -> dict[str, Any]:
    profile = repository.load_profile(_normalize_profile_key(profile_key), db_path=db_path)
    if profile is None:
        raise ValueError("DATA_ONBOARDING_PROFILE_NOT_FOUND")
    return {"status": "success", "profile": _serialize_profile(profile)}


def list_source_profiles(
    *, status: str | None = None, db_path: str | Path | None = None
) -> dict[str, Any]:
    normalized_status = _normalize_profile_status(status) if status else None
    profiles = repository.list_profiles(status=normalized_status, db_path=db_path)
    return {
        "status": "success",
        "profiles": [_serialize_profile(profile) for profile in profiles],
    }


def preview_source_profile(
    profile_key: str, *, db_path: str | Path | None = None
) -> dict[str, Any]:
    profile = _load_active_profile(profile_key, db_path=db_path)
    handler = get_handler(profile.source_type)
    profile_payload = _serialize_profile(profile)
    run_id = f"data-onboarding-run-{uuid4().hex}"
    source_identity_before = handler.build_source_identity(profile)
    source_preview = handler.preview(profile, run_id=run_id, db_path=db_path)
    source_identity_after = handler.build_source_identity(profile)
    source_changed_during_preview = source_identity_before != source_identity_after
    if source_changed_during_preview:
        handler.release_run(run_id, db_path=db_path)
        source_identity = source_identity_after
        source_preview = _build_source_changed_preview(
            profile_payload.get("mapping_preset")
        )
    else:
        source_identity = source_identity_after
    preview_fingerprint = _fingerprint(
        {
            "profile": _profile_binding(profile_payload),
            "source_identity": source_identity,
            "source_preview": source_preview,
        }
    )
    existing = None
    if not source_changed_during_preview:
        existing = repository.find_run_by_fingerprint(
            profile.profile_id,
            preview_fingerprint,
            db_path=db_path,
        )
    if existing is not None and _should_reuse_existing_preview(existing):
        handler.release_run(run_id, db_path=db_path)
        return _preview_response_from_run(existing)
    preview_payload = _build_preview_payload(
        run_id=run_id,
        profile_payload=profile_payload,
        source_identity=source_identity,
        source_preview=source_preview,
        preview_fingerprint=preview_fingerprint,
        planned_operations=handler.planned_operations(source_preview),
        coverage=handler.coverage_summary(source_preview),
    )
    repository.create_run(
        run_id=run_id,
        profile=profile,
        profile_snapshot=profile_payload,
        source_identity=source_identity,
        preview_fingerprint=preview_fingerprint,
        source_preview=source_preview,
        preview_payload=preview_payload,
        status=_stored_run_status(source_preview),
        created_at=_utc_now(),
        failure_code=_preview_failure_code(source_preview),
        db_path=db_path,
    )
    if str(source_preview.get("status", "rejected")) == "rejected":
        handler.release_run(run_id, db_path=db_path)
    return preview_payload


def confirm_onboarding_run(
    run_id: str,
    *,
    recover_running: bool = False,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    run = repository.load_run(run_id, db_path=db_path)
    if run is None:
        raise ValueError("DATA_ONBOARDING_RUN_NOT_FOUND")
    run_status = str(run["status"])
    recovered_running = False
    if run_status == "completed":
        return _confirmed_response_from_run(run)
    if run_status == "running":
        if not recover_running:
            raise ValueError("DATA_ONBOARDING_RUN_IN_PROGRESS")
        if not repository.has_running_attempt(run_id, db_path=db_path):
            run = repository.load_run(run_id, db_path=db_path)
            if run is None:
                raise ValueError("DATA_ONBOARDING_RUN_NOT_FOUND")
            run_status = str(run["status"])
        else:
            repository.recover_running_run(
                run_id=run_id,
                failure_code="DATA_ONBOARDING_PREVIOUS_RUNNING_ATTEMPT_RECOVERED",
                finished_at=_utc_now(),
                db_path=db_path,
            )
            run = repository.load_run(run_id, db_path=db_path)
            if run is None:
                raise ValueError("DATA_ONBOARDING_RUN_NOT_FOUND")
            run_status = str(run["status"])
            recovered_running = True
    if run_status == "rejected":
        raise ValueError("DATA_ONBOARDING_RUN_NOT_CONFIRMABLE")
    resume_partial = run_status == "partially_completed"
    profile = repository.load_profile(str(run["profile_key"]), db_path=db_path)
    if profile is None:
        raise ValueError("DATA_ONBOARDING_PROFILE_NOT_FOUND")
    handler = get_handler(str(run["source_type"]))
    source_preview = _load_payload(str(run["source_preview_json"]))
    stored_profile_payload = _load_payload(str(run["profile_snapshot_json"]))
    live_profile_payload = _serialize_profile(profile)
    expected_revision = _preview_revision(source_preview)
    if resume_partial and _profile_binding(live_profile_payload) != _profile_binding(
        stored_profile_payload
    ):
        return _build_partial_retry_blocked_payload(
            run,
            stale_code="DATA_ONBOARDING_PROFILE_CHANGED",
            stale_message="Profile definition changed after partial publish; preview again before retry.",
        )
    started_at = _utc_now()
    attempt_id = repository.start_run_attempt(run_id, started_at=started_at, db_path=db_path)
    claimed_revision = None if resume_partial else expected_revision
    try:
        if _profile_binding(live_profile_payload) != _profile_binding(stored_profile_payload):
            finished_at = _utc_now()
            rejected_payload = _build_stale_preview_payload(
                run_id=run_id,
                profile_payload=stored_profile_payload,
                source_identity=_load_payload(str(run["source_identity_json"])),
                source_preview=source_preview,
                preview_fingerprint=str(run["preview_fingerprint"]),
                stale_code="DATA_ONBOARDING_PROFILE_CHANGED",
                stale_message="Profile definition changed after preview; preview again before confirm.",
            )
            repository.finish_run(
                run_id=run_id,
                attempt_id=attempt_id,
                run_status="rejected",
                confirm_payload=rejected_payload,
                failure_code="DATA_ONBOARDING_PROFILE_CHANGED",
                finished_at=finished_at,
                links=[],
                profile_key=None,
                db_path=db_path,
            )
            handler.release_run(run_id, db_path=db_path)
            return rejected_payload
        if claimed_revision is not None:
            if recovered_running and profile.current_revision == expected_revision:
                claimed_revision = None
            else:
                repository.claim_profile_revision(
                    profile_key=profile.profile_key,
                    expected_revision=expected_revision,
                    db_path=db_path,
                )
        source_result = handler.confirm(profile, source_preview, db_path=db_path)
        links = handler.publication_links(source_result)
        finished_at = _utc_now()
        confirm_payload = _build_confirm_payload(
            run_id=run_id,
            profile_payload=_load_payload(str(run["profile_snapshot_json"])),
            source_identity=_load_payload(str(run["source_identity_json"])),
            source_preview=source_preview,
            source_result=source_result,
            published_operations=[_serialize_link(link) for link in links],
            preview_fingerprint=str(run["preview_fingerprint"]),
        )
        final_status = _final_run_status(str(source_result.get("status", "failed")))
        if (
            claimed_revision is not None
            and final_status == "rejected"
            and not _has_published_side_effects(links)
        ):
            repository.restore_profile_revision(
                profile_key=profile.profile_key,
                claimed_revision=expected_revision,
                db_path=db_path,
            )
        repository.finish_run(
            run_id=run_id,
            attempt_id=attempt_id,
            run_status=final_status,
            confirm_payload=confirm_payload,
            failure_code="" if final_status == "completed" else _failure_code_from_result(source_result),
            finished_at=finished_at,
            links=links,
            profile_key=profile.profile_key if final_status == "completed" else None,
            db_path=db_path,
        )
        if final_status in {"completed", "rejected"}:
            handler.release_run(run_id, db_path=db_path)
        return confirm_payload
    except ValueError as exc:
        if str(exc) == "DATA_ONBOARDING_PROFILE_REVISION_CONFLICT":
            finished_at = _utc_now()
            rejected_payload = _build_stale_preview_payload(
                run_id=run_id,
                profile_payload=stored_profile_payload,
                source_identity=_load_payload(str(run["source_identity_json"])),
                source_preview=source_preview,
                preview_fingerprint=str(run["preview_fingerprint"]),
                stale_code="DATA_ONBOARDING_PROFILE_REVISION_CONFLICT",
                stale_message="Profile revision changed after preview; preview again before confirm.",
            )
            repository.finish_run(
                run_id=run_id,
                attempt_id=attempt_id,
                run_status="rejected",
                confirm_payload=rejected_payload,
                failure_code=str(exc),
                finished_at=finished_at,
                links=[],
                profile_key=None,
                db_path=db_path,
            )
            handler.release_run(run_id, db_path=db_path)
            return rejected_payload
        if claimed_revision is not None:
            repository.restore_profile_revision(
                profile_key=profile.profile_key,
                claimed_revision=expected_revision,
                db_path=db_path,
            )
        repository.fail_attempt(
            run_id=run_id,
            attempt_id=attempt_id,
            failure_code=_failure_code(exc),
            finished_at=_utc_now(),
            db_path=db_path,
        )
        raise
    except RuntimeError as exc:
        if claimed_revision is not None:
            repository.restore_profile_revision(
                profile_key=profile.profile_key,
                claimed_revision=expected_revision,
                db_path=db_path,
            )
        repository.fail_attempt(
            run_id=run_id,
            attempt_id=attempt_id,
            failure_code=_failure_code(exc),
            finished_at=_utc_now(),
            db_path=db_path,
        )
        raise
    except Exception as exc:
        if claimed_revision is not None:
            repository.restore_profile_revision(
                profile_key=profile.profile_key,
                claimed_revision=expected_revision,
                db_path=db_path,
            )
        failure_code = _failure_code(exc)
        repository.fail_attempt(
            run_id=run_id,
            attempt_id=attempt_id,
            failure_code=failure_code,
            finished_at=_utc_now(),
            db_path=db_path,
        )
        raise RuntimeError(failure_code) from exc


def show_onboarding_run(
    run_id: str, *, db_path: str | Path | None = None
) -> dict[str, Any]:
    run = repository.load_run(run_id, db_path=db_path)
    if run is None:
        raise ValueError("DATA_ONBOARDING_RUN_NOT_FOUND")
    confirm_payload = _load_payload(str(run["confirm_json"]))
    payload = confirm_payload or _load_payload(str(run["preview_json"]))
    links = [_deserialize_link(item) for item in repository.load_links(run_id, db_path=db_path)]
    return {
        "status": "success",
        "run": {
            "run_id": run_id,
            "state": str(run["status"]),
            "created_at": str(run["created_at"]),
            "completed_at": str(run["completed_at"]) or None,
            "failure_code": str(run["failure_code"]) or None,
            "profile_key": str(run["profile_key"]),
            "source_type": str(run["source_type"]),
            "payload": payload,
            "domain_links": links,
        },
    }


def _normalize_profile_key(value: str) -> str:
    normalized = slugify_text((value or "").strip())
    if not normalized:
        raise ValueError("DATA_ONBOARDING_PROFILE_KEY_INVALID")
    return normalized


def _normalize_profile_status(value: str | None) -> str:
    normalized = (value or "active").strip().lower()
    if normalized not in {"active", "inactive"}:
        raise ValueError("DATA_ONBOARDING_PROFILE_STATUS_INVALID")
    return normalized


def _serialize_profile(profile: SourceProfileRecord) -> dict[str, Any]:
    handler = get_handler(profile.source_type)
    payload = {
        "profile_id": profile.profile_id,
        "profile_key": profile.profile_key,
        "display_name": profile.display_name,
        "source_type": profile.source_type,
        "source_locator": profile.source_locator,
        "mapping_preset_id": profile.mapping_preset_id,
        "member_key_type": profile.member_key_type,
        "project_key_type": profile.project_key_type,
        "baseline_source": profile.baseline_source,
        "adjustment_source": profile.adjustment_source,
        "conflict_policy": profile.conflict_policy,
        "plan_naming_policy": profile.plan_naming_policy,
        "source_options": copy.deepcopy(profile.source_options),
        "current_revision": profile.current_revision,
        "status": profile.status,
        "last_successful_run_id": profile.last_successful_run_id or None,
        "last_successful_run_at": profile.last_successful_run_at or None,
        "created_at": profile.created_at,
        "updated_at": profile.updated_at,
    }
    payload.update(handler.profile_metadata(profile))
    return payload


def _load_active_profile(
    profile_key: str, *, db_path: str | Path | None = None
) -> SourceProfileRecord:
    profile = repository.load_profile(_normalize_profile_key(profile_key), db_path=db_path)
    if profile is None:
        raise ValueError("DATA_ONBOARDING_PROFILE_NOT_FOUND")
    if profile.status != "active":
        raise ValueError("DATA_ONBOARDING_PROFILE_INACTIVE")
    return profile


def _preview_response_from_run(run: dict[str, Any]) -> dict[str, Any]:
    status = str(run["status"])
    if status in {"completed", "partially_completed"}:
        payload = _confirmed_response_from_run(run)
        if payload.get("status") == "completed":
            payload["status"] = "already_completed"
        return payload
    if status == "rejected":
        confirm_payload = _load_payload(str(run["confirm_json"]))
        if confirm_payload:
            replay = dict(confirm_payload.get("replay_identity", {}))
            replay["idempotent"] = True
            confirm_payload["replay_identity"] = replay
            return confirm_payload
    payload = _load_payload(str(run["preview_json"]))
    replay = dict(payload.get("replay_identity", {}))
    replay["idempotent"] = True
    payload["replay_identity"] = replay
    if status == "running":
        payload["status"] = "in_progress"
    elif status == "failed":
        payload["status"] = "retryable"
    return payload


def _confirmed_response_from_run(run: dict[str, Any]) -> dict[str, Any]:
    payload = _load_payload(str(run["confirm_json"]))
    replay = dict(payload.get("replay_identity", {}))
    replay["idempotent"] = True
    payload["replay_identity"] = replay
    return payload


def _build_preview_payload(
    *,
    run_id: str,
    profile_payload: dict[str, Any],
    source_identity: dict[str, Any],
    source_preview: dict[str, Any],
    preview_fingerprint: str,
    planned_operations: list[dict[str, Any]],
    coverage: dict[str, Any],
) -> dict[str, Any]:
    package_ids = [
        str(item["package_id"])
        for item in planned_operations
        if "package_id" in item
    ]
    return {
        "status": str(source_preview.get("status", "rejected")),
        "run_id": run_id,
        "profile": profile_payload,
        "source": source_identity,
        "source_contract": copy.deepcopy(source_preview.get("source_contract")),
        "plan_version": source_preview.get("plan_version"),
        "revision_candidate": source_preview.get("revision"),
        "blockers": list(source_preview.get("blockers", [])),
        "warnings": list(source_preview.get("warnings", [])),
        "conflicts": list(source_preview.get("conflicts", [])),
        "counts": dict(source_preview.get("counts", {})),
        "coverage": coverage,
        "planned_domain_operations": planned_operations,
        "confirmation_required": _confirmation_required(
            str(source_preview.get("status", "rejected"))
        ),
        "replay_identity": {
            "preview_fingerprint": preview_fingerprint,
            "planned_package_ids": package_ids,
            "idempotent": False,
        },
    }


def _build_confirm_payload(
    *,
    run_id: str,
    profile_payload: dict[str, Any],
    source_identity: dict[str, Any],
    source_preview: dict[str, Any],
    source_result: dict[str, Any],
    published_operations: list[dict[str, Any]],
    preview_fingerprint: str,
) -> dict[str, Any]:
    completed_operation_count = sum(
        item["status"] == "completed" for item in published_operations
    )
    rejected_operation_count = sum(
        item["status"] == "rejected" for item in published_operations
    )
    return {
        "status": str(source_result.get("status", "failed")),
        "run_id": run_id,
        "profile": profile_payload,
        "source": source_identity,
        "source_contract": copy.deepcopy(
            source_result.get("source_contract", source_preview.get("source_contract"))
        ),
        "plan_version": source_preview.get("plan_version"),
        "applied_revision": source_preview.get("revision"),
        "blockers": list(source_result.get("blockers", source_preview.get("blockers", []))),
        "warnings": list(source_result.get("warnings", source_preview.get("warnings", []))),
        "conflicts": list(source_result.get("conflicts", source_preview.get("conflicts", []))),
        "publish_summary": {
            "completed_operation_count": completed_operation_count,
            "rejected_operation_count": rejected_operation_count,
            "partial_publication": str(source_result.get("status")) == "partially_completed",
        },
        "published_domain_operations": published_operations,
        "coverage": {
            item["capability"]: item["details"].get("report", {}).get("coverage", {})
            for item in published_operations
        },
        "replay_identity": {
            "preview_fingerprint": preview_fingerprint,
            "idempotent": bool(
                source_result.get("domain_result", {}).get("idempotent", False)
            ),
        },
    }


def _build_stale_preview_payload(
    *,
    run_id: str,
    profile_payload: dict[str, Any],
    source_identity: dict[str, Any],
    source_preview: dict[str, Any],
    preview_fingerprint: str,
    stale_code: str,
    stale_message: str,
) -> dict[str, Any]:
    blockers = list(source_preview.get("blockers", []))
    blockers.append(
        {
            "severity": "blocker",
            "code": stale_code,
            "message": stale_message,
            "location": "profile",
        }
    )
    return {
        "status": "rejected",
        "run_id": run_id,
        "profile": profile_payload,
        "source": source_identity,
        "source_contract": copy.deepcopy(source_preview.get("source_contract")),
        "plan_version": source_preview.get("plan_version"),
        "applied_revision": source_preview.get("revision"),
        "blockers": blockers,
        "warnings": list(source_preview.get("warnings", [])),
        "conflicts": list(source_preview.get("conflicts", [])),
        "publish_summary": {
            "completed_operation_count": 0,
            "rejected_operation_count": 1,
            "partial_publication": False,
        },
        "published_domain_operations": [],
        "coverage": {},
        "replay_identity": {
            "preview_fingerprint": preview_fingerprint,
            "idempotent": False,
        },
    }


def _build_source_changed_preview(mapping_preset: object) -> dict[str, Any]:
    return {
        "status": "rejected",
        "source_contract": (
            {
                "mapping_preset": copy.deepcopy(mapping_preset),
                "resolution": None,
            }
            if mapping_preset is not None
            else None
        ),
        "blockers": [
            {
                "severity": "blocker",
                "code": "DATA_ONBOARDING_SOURCE_CHANGED_DURING_PREVIEW",
                "message": "Source content changed during preview; run preview again.",
                "location": "source",
            }
        ],
        "warnings": [],
        "conflicts": [],
        "counts": {},
    }


def _build_partial_retry_blocked_payload(
    run: dict[str, Any],
    *,
    stale_code: str,
    stale_message: str,
) -> dict[str, Any]:
    payload = _confirmed_response_from_run(run)
    blockers = list(payload.get("blockers", []))
    blockers.append(
        {
            "severity": "blocker",
            "code": stale_code,
            "message": stale_message,
            "location": "profile",
        }
    )
    payload["status"] = "partially_completed"
    payload["blockers"] = blockers
    payload["retry_blocked"] = True
    return payload


def _preview_failure_code(source_preview: dict[str, Any]) -> str:
    if str(source_preview.get("status")) != "rejected":
        return ""
    blockers = source_preview.get("blockers", [])
    if isinstance(blockers, list) and blockers:
        first = blockers[0]
        if isinstance(first, dict) and "code" in first:
            return str(first["code"])
    conflicts = source_preview.get("conflicts", [])
    if isinstance(conflicts, list) and conflicts:
        first = conflicts[0]
        if isinstance(first, dict) and "conflict_code" in first:
            return str(first["conflict_code"])
    return "DATA_ONBOARDING_PREVIEW_REJECTED"


def _preview_revision(source_preview: dict[str, Any]) -> int:
    revision = source_preview.get("revision")
    if not isinstance(revision, int):
        raise ValueError("DATA_ONBOARDING_PREVIEW_REVISION_MISSING")
    return revision


def _final_run_status(status: str) -> str:
    if status in {"completed", "partially_completed", "rejected"}:
        return status
    return "failed"


def _failure_code(exc: Exception) -> str:
    if isinstance(exc, (ValueError, RuntimeError)):
        return str(exc)
    return "DATA_ONBOARDING_CONFIRMATION_FAILED"


def _failure_code_from_result(source_result: dict[str, Any]) -> str:
    status = str(source_result.get("status", "failed"))
    if status == "rejected":
        return _preview_failure_code(source_result)
    if status == "failed":
        failure_code = source_result.get("failure_code")
        if isinstance(failure_code, str) and failure_code:
            return failure_code
        return "DATA_ONBOARDING_CONFIRMATION_FAILED"
    if status == "partially_completed":
        for item in ("capacity_result", "workforce_result"):
            result = source_result.get(item)
            if isinstance(result, dict) and result.get("failure_code"):
                return str(result["failure_code"])
        return "DATA_ONBOARDING_PARTIAL_COMPLETION"
    return "DATA_ONBOARDING_CONFIRMATION_FAILED"


def _profile_binding(profile_payload: dict[str, Any]) -> dict[str, Any]:
    return {
        key: copy.deepcopy(profile_payload.get(key))
        for key in (
            "profile_key",
            "source_type",
            "source_locator",
            "mapping_preset_id",
            "member_key_type",
            "project_key_type",
            "baseline_source",
            "adjustment_source",
            "conflict_policy",
            "plan_naming_policy",
            "source_options",
            "status",
        )
    }


def _has_published_side_effects(links: list[DomainLinkRecord]) -> bool:
    return any(
        link.status == "completed" or bool(link.domain_publication_id)
        for link in links
    )


def _should_reuse_existing_preview(run: dict[str, Any]) -> bool:
    preview_payload = _load_payload(str(run["preview_json"]))
    preview_status = str(preview_payload.get("status", ""))
    if preview_status in {"in_progress", "retryable"}:
        return False
    if str(run["status"]) != "rejected":
        return True
    return str(run["failure_code"]) not in {
        "DATA_ONBOARDING_PROFILE_CHANGED",
        "DATA_ONBOARDING_PROFILE_REVISION_CONFLICT",
    }


def _stored_run_status(source_preview: dict[str, Any]) -> str:
    preview_status = str(source_preview.get("status", "rejected"))
    if preview_status == "rejected":
        return "rejected"
    return "previewed"


def _confirmation_required(status: str) -> bool:
    return status in {"previewed", "retryable", "already_completed"}


def _serialize_link(link: DomainLinkRecord) -> dict[str, Any]:
    return {
        "capability": link.capability_key,
        "status": link.status,
        "domain_session_id": link.domain_session_id or None,
        "domain_publication_id": link.domain_publication_id or None,
        "domain_plan_version_id": link.domain_plan_version_id or None,
        "details": copy.deepcopy(link.details),
    }


def _deserialize_link(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "capability": str(row["capability_key"]),
        "status": str(row["status"]),
        "domain_session_id": str(row["domain_session_id"]) or None,
        "domain_publication_id": str(row["domain_publication_id"]) or None,
        "domain_plan_version_id": str(row["domain_plan_version_id"]) or None,
        "details": _load_payload(str(row["details_json"])),
        "created_at": str(row["created_at"]),
    }


def _load_payload(value: str) -> dict[str, Any]:
    loaded = json.loads(value)
    return loaded if isinstance(loaded, dict) else {}


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
