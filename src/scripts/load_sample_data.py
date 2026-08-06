#!/usr/bin/env python3
"""Load the committed synthetic packages into an isolated demo database.

The default build follows the versioned clean re-import path from an empty
database: bootstrap, workforce planning import, resource capacity import,
board registration (data prerequisite of the IP-033 entry), deterministic
synthetic evidence seeding, canonical Milestone import, Project Health
re-import (derivation + seven-dimension assessment), Delivery Attention
reconciliation, and a confirmed Weekly Brief v2 snapshot.  Milestone and
evidence data precede the assessment so the demo shows real dimension states
instead of an all-`unknown`/`not_available` database.

``--replay`` re-runs only the idempotent chain on an existing database and
must not create duplicate assessments, attention items, or snapshots.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).parent.parent
SAMPLE_ROOT = ROOT / "sample-data"
DEFAULT_DB = SAMPLE_ROOT / "demo" / "sample_pm.db"
BRIEF_GENERATED_AT = "2026-08-02T08:00:00Z"
BRIEF_IDEMPOTENCY_KEY = "demo-brief-2026-08-02"

sys.path.insert(0, str(ROOT))


def _run(command: list[str], env: dict[str, str]) -> None:
    subprocess.run(command, cwd=ROOT, env=env, check=True)


@contextmanager
def _database_path_override(db_path: Path):
    from pm_agent.config import settings

    original_database_path = settings.database_path
    settings.database_path = str(db_path)
    try:
        yield
    finally:
        settings.database_path = original_database_path


ONBOARDING_CHAIN = (
    (
        "demo-workforce",
        "workforce-planning-json",
        SAMPLE_ROOT / "json" / "workforce_planning_import.sample.json",
    ),
    (
        "demo-capacity",
        "resource-capacity-json",
        SAMPLE_ROOT / "json" / "resource_capacity_import.sample.json",
    ),
    (
        "demo-jira-registry",
        "jira-board-registry-csv",
        SAMPLE_ROOT / "csv" / "jira_board_configs.sample.csv",
    ),
    (
        "demo-milestones",
        "milestone-json",
        SAMPLE_ROOT / "json" / "milestone_import.sample.json",
    ),
    (
        "demo-project-health",
        "project-health-reimport-json",
        SAMPLE_ROOT / "json" / "project_health_reimport.sample.json",
    ),
)


def _run_onboarding_import(
    db_path: Path,
    *,
    profile_key: str,
    source_type: str,
    file_path: Path,
) -> None:
    from pm_agent.data_onboarding import service as onboarding_service
    from pm_agent.database.bootstrap import main as bootstrap

    resolved_path = file_path.resolve()
    print(f"Running: pm onboarding [{source_type}] {resolved_path.name}")
    with _database_path_override(db_path):
        bootstrap(quiet=True)
    onboarding_service.save_source_profile(
        profile_key=profile_key,
        source_type=source_type,
        source_locator=str(resolved_path),
        db_path=db_path,
    )
    preview = onboarding_service.preview_source_profile(profile_key, db_path=db_path)
    if preview["status"] not in {"previewed", "already_completed"}:
        raise SystemExit(
            f"Onboarding preview failed for {source_type}: {preview['status']}"
        )
    confirmed = onboarding_service.confirm_onboarding_run(
        preview["run_id"],
        db_path=db_path,
    )
    if confirmed["status"] != "completed":
        raise SystemExit(
            f"Onboarding confirm failed for {source_type}: {confirmed['status']}"
        )


def _reconcile_attention(db_path: Path) -> None:
    from pm_agent.attention import AttentionService

    service = AttentionService(db_path=db_path)
    preview = service.preview_reconciliation(actor="copilot")
    if preview["status"] != "proposed":
        raise SystemExit(f"Attention reconciliation failed: {preview}")
    changes = preview.get("proposed", {})
    change_keys = (
        "created_count",
        "updated_count",
        "cleared_count",
        "reopened_count",
        "lifecycle_count",
        "disabled_count",
        "limited_count",
    )
    if not any(changes.get(key, 0) for key in change_keys):
        print("Attention reconciliation: no changes")
        return
    confirmed = service.confirm(
        operation_id=preview["operation_id"],
        confirmation_token=preview["confirmation_token"],
    )
    print(f"Attention reconciliation confirmed: {confirmed['status']}")


def _capture_weekly_brief(db_path: Path) -> None:
    import sqlite3

    from pm_agent.weekly_brief.composer import compose_weekly_brief_v2
    from pm_agent.weekly_brief.operations import confirm_capture, preview_capture

    with sqlite3.connect(db_path) as connection:
        existing = connection.execute(
            """
            SELECT 1 FROM weekly_brief_snapshot_operations
            WHERE actor_id = ? AND idempotency_key = ? AND status = 'confirmed'
            LIMIT 1
            """,
            ("copilot", BRIEF_IDEMPOTENCY_KEY),
        ).fetchone()
    if existing:
        print("Weekly Brief v2 snapshot: already_confirmed")
        return

    composed = compose_weekly_brief_v2(
        generated_at=BRIEF_GENERATED_AT,
        db_path=db_path,
    )
    candidate = composed["snapshot"]["capture_candidate"]
    preview = preview_capture(
        candidate=candidate,
        actor_id="copilot",
        idempotency_key=BRIEF_IDEMPOTENCY_KEY,
        db_path=db_path,
    )
    if preview["status"] == "previewed":
        confirmed = confirm_capture(
            operation_id=preview["operation_id"],
            confirmation_token=preview["confirmation_token"],
            db_path=db_path,
        )
        print(f"Weekly Brief v2 snapshot: {confirmed['status']}")
    else:
        print(f"Weekly Brief v2 snapshot: {preview['status']}")


def _next_steps(db_path: Path) -> None:
    print()
    print(f"Demo DB ready: {db_path}")
    print("Verification commands (all return non-empty, contract-compliant results):")
    print(f"  DATABASE_PATH='{db_path}' python3 -m pm_agent.cli.app tool query layered-project-health-review --project project-synthetic-atlas")
    print(f"  DATABASE_PATH='{db_path}' python3 -m pm_agent.cli.app tool query delivery-execution-review --project project-synthetic-atlas")
    print(f"  DATABASE_PATH='{db_path}' python3 -m pm_agent.cli.app tool query delivery-attention-center")
    print(f"  DATABASE_PATH='{db_path}' python3 -m pm_agent.cli.app tool query resource-capacity-heatmap --param year=2026 --param month=8 --param plan_version_id=plan-synthetic-baseline-001")
    print(f"  DATABASE_PATH='{db_path}' python3 -m pm_agent.cli.app weekly-brief query")
    print(f"  DATABASE_PATH='{db_path}' python3 -m pm_agent.dashboard")


def main() -> None:
    parser = argparse.ArgumentParser(description="Load committed sample data into a demo DB")
    parser.add_argument(
        "--db",
        default=str(DEFAULT_DB),
        help="Target SQLite DB path for the demo environment",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite the demo DB if it already exists",
    )
    parser.add_argument(
        "--replay",
        action="store_true",
        help="Idempotently re-run the structured chain on an existing demo DB",
    )
    args = parser.parse_args()

    db_path = Path(args.db).resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        if args.force:
            db_path.unlink()
        elif not args.replay:
            raise SystemExit(
                f"Demo DB already exists: {db_path}\n"
                "Re-run with --force to recreate it or --replay for an "
                "idempotent re-run."
            )

    env = os.environ.copy()
    env["DATABASE_PATH"] = str(db_path)

    if not db_path.exists():
        print("Running: scripts/init_db.py")
        _run([sys.executable, "scripts/init_db.py"], env)

    for profile_key, source_type, file_path in ONBOARDING_CHAIN[:3]:
        _run_onboarding_import(
            db_path,
            profile_key=profile_key,
            source_type=source_type,
            file_path=file_path,
        )
    print("Running: scripts/seed_demo_evidence.py")
    _run([sys.executable, "scripts/seed_demo_evidence.py"], env)
    for profile_key, source_type, file_path in ONBOARDING_CHAIN[3:]:
        _run_onboarding_import(
            db_path,
            profile_key=profile_key,
            source_type=source_type,
            file_path=file_path,
        )

    _reconcile_attention(db_path)
    _capture_weekly_brief(db_path)
    _next_steps(db_path)


if __name__ == "__main__":
    main()
