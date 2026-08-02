"""R5: automated cross-capability integration test over the R2 demo chain."""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from pm_agent.config import settings
from pm_agent.use_cases import use_case_executor
from pm_agent.use_cases.service import UseCaseRequest

ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
ATLAS = "project-synthetic-atlas"
SNAPSHOT_KEY = "r5-integration-brief-001"
CHANGE_KEYS = (
    "created_count",
    "updated_count",
    "cleared_count",
    "reopened_count",
    "lifecycle_count",
    "disabled_count",
    "limited_count",
)


def _environment(db_path: Path) -> dict[str, str]:
    return {
        "PATH": os.environ.get("PATH", ""),
        "PYTHONPATH": str(ROOT),
        "DATABASE_PATH": str(db_path),
        "PYTHONDONTWRITEBYTECODE": "1",
    }


def _script(db_path: Path, *arguments: str) -> str:
    result = subprocess.run(
        [PYTHON, *arguments],
        cwd=ROOT,
        env=_environment(db_path),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise AssertionError(
            f"command failed rc={result.returncode}: {arguments[:2]}\n"
            f"stderr: {result.stderr[-2000:]}\nstdout: {result.stdout[-500:]}"
        )
    return result.stdout


def _cli_json(db_path: Path, *arguments: str) -> dict:
    return json.loads(_script(db_path, "-m", "pm_agent.cli.app", *arguments))


@pytest.fixture(scope="module")
def chain_db(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Build the complete R2 chain on an empty temporary database."""
    db_path = tmp_path_factory.mktemp("usability-chain") / "chain.db"
    _script(db_path, "scripts/init_db.py")
    _script(
        db_path,
        "scripts/import_workforce_planning.py",
        "--file",
        str(ROOT / "sample-data/json/workforce_planning_import.sample.json"),
        "--confirm",
    )
    _script(
        db_path,
        "scripts/import_resource_capacity.py",
        "--file",
        str(ROOT / "sample-data/json/resource_capacity_import.sample.json"),
        "--confirm",
    )
    _script(
        db_path,
        "scripts/import_jira_boards.py",
        "--file",
        str(ROOT / "sample-data/csv/jira_board_configs.sample.csv"),
    )
    _script(db_path, "scripts/seed_demo_evidence.py")
    _script(
        db_path,
        "scripts/import_milestones.py",
        "--file",
        str(ROOT / "sample-data/json/milestone_import.sample.json"),
        "--confirm",
    )
    health = json.loads(
        _script(
            db_path,
            "scripts/import_project_health.py",
            "--file",
            str(ROOT / "sample-data/json/project_health_reimport.sample.json"),
            "--confirm",
        )
    )
    assert health["report"]["assessment_state"] == "completed"
    preview = _cli_json(db_path, "attention", "reconcile-preview")
    assert preview["status"] == "proposed"
    confirmed = _cli_json(
        db_path,
        "attention",
        "confirm",
        preview["operation_id"],
        "--token",
        preview["confirmation_token"],
    )
    assert confirmed["status"] == "success"
    return db_path


@pytest.fixture
def chain_db_copy(chain_db: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "chain.db"
    shutil.copy2(chain_db, db_path)
    monkeypatch.setattr(settings, "database_path", str(db_path))
    return db_path


def _count(db_path: Path, table: str) -> int:
    with sqlite3.connect(db_path) as connection:
        return connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]


def test_chain_assessment_is_readable_and_execution_review_is_nonempty(
    chain_db_copy: Path,
) -> None:
    layered = use_case_executor.execute(
        UseCaseRequest(
            use_case_id="layered-project-health-review",
            parameters={"project_id": ATLAS},
        )
    )
    assert layered.status == "success"
    assert layered.data["assessments"]
    assert layered.data["assessments"][0]["state"] == "red"

    execution = use_case_executor.execute(
        UseCaseRequest(
            use_case_id="delivery-execution-review",
            parameters={"project_id": ATLAS},
        )
    )
    assert execution.status == "success"
    assert execution.data["sprint_execution"]
    assert execution.data["release_milestone"]


def test_chain_attention_reconciliation_exposes_center_coverage(
    chain_db_copy: Path,
) -> None:
    center = use_case_executor.execute(
        UseCaseRequest(use_case_id="delivery-attention-center")
    )
    assert center.status == "success"
    assert center.data["reconciliation_coverage"]["status"] in {"complete", "partial"}
    assert center.data["reconciliation_coverage"]["finished_at"]
    assert len(center.data["items"]) >= 5
    assert len({item["rule_key"] for item in center.data["items"]}) >= 4

    repeat = _cli_json(chain_db_copy, "attention", "reconcile-preview")
    assert repeat["status"] == "proposed"
    assert repeat["proposed"]["candidate_count"] >= 1
    assert all(repeat["proposed"].get(key, 0) == 0 for key in CHANGE_KEYS)


def test_chain_weekly_brief_composes_and_snapshot_preview_confirm_is_idempotent(
    chain_db_copy: Path,
) -> None:
    brief = use_case_executor.execute(
        UseCaseRequest(
            contract_version="2.0",
            use_case_id="weekly-dm-brief-v2",
            parameters={},
        )
    )
    assert brief.status == "success"
    assert brief.data["summary"]["project_count"] >= 1
    assert brief.data["sections"]["overall_health"]["availability"] in {
        "partial",
        "available",
    }
    assert brief.data["sections"]["highest_attention_signals"]["items"]

    query = _cli_json(chain_db_copy, "weekly-brief", "query")
    candidate = json.dumps(
        query["data"]["snapshot"]["capture_candidate"],
        ensure_ascii=False,
    )
    candidate_path = chain_db_copy.parent / "candidate.json"
    candidate_path.write_text(candidate, encoding="utf-8")
    recompose_check = json.loads(
        _script(
            chain_db_copy,
            "-c",
            (
                "import json;"
                "from pm_agent.weekly_brief.composer import compose_weekly_brief_v2;"
                "from pm_agent.weekly_brief.snapshots import _normalized;"
                f"c=json.load(open('{candidate_path}'));"
                "r=compose_weekly_brief_v2(generated_at=c['input']['as_of'])"
                "['snapshot']['capture_candidate'];"
                "n1=_normalized(c); n2=_normalized(r);"
                "print(json.dumps({'equal': n1 == n2, "
                "'missing': sorted(set(n1) - set(n2)) if n1 != n2 else []}))"
            ),
        )
    )
    assert recompose_check["equal"] is True
    preview = json.loads(
        _script(
            chain_db_copy,
            "-c",
            (
                "import json;"
                "from pm_agent.weekly_brief.operations import preview_capture;"
                f"c=json.load(open('{candidate_path}'));"
                "r=preview_capture(candidate=c,actor_id='copilot',"
                "idempotency_key='r5-integration-brief-001');"
                "print(json.dumps(r,sort_keys=True))"
            ),
        )
    )
    assert preview["status"] == "previewed"
    confirmed = json.loads(
        _script(
            chain_db_copy,
            "-c",
            (
                "import json;"
                "from pm_agent.weekly_brief.operations import confirm_capture;"
                f"r=confirm_capture(operation_id='{preview['operation_id']}',"
                f"confirmation_token='{preview['confirmation_token']}');"
                "print(json.dumps(r,sort_keys=True))"
            ),
        )
    )
    assert confirmed["status"] == "confirmed"
    # Reusing the pre-snapshot candidate is now stale by design: the composer
    # recomposes with the newly confirmed snapshot as baseline, so the same
    # candidate no longer matches and the preview rejects it.
    stale_repeat = json.loads(
        _script(
            chain_db_copy,
            "-c",
            (
                "import json;"
                "from pm_agent.weekly_brief.operations import preview_capture;"
                f"c=json.load(open('{candidate_path}'));"
                "r=preview_capture(candidate=c,actor_id='copilot',"
                "idempotency_key='r5-integration-brief-001');"
                "print(json.dumps(r,sort_keys=True))"
            ),
        )
    )
    assert stale_repeat["status"] == "failed"
    assert stale_repeat["warnings"] == ["WEEKLY_BRIEF_CAPTURE_CANDIDATE_INVALID"]
    # A fresh composition now carries the baseline; a second capture works and
    # the brief exposes changes since the previous snapshot.
    fresh_query = _cli_json(chain_db_copy, "weekly-brief", "query")
    fresh_candidate = fresh_query["data"]["snapshot"]["capture_candidate"]
    assert fresh_candidate["baseline_snapshot_id"]
    fresh_path = chain_db_copy.parent / "fresh-candidate.json"
    fresh_path.write_text(json.dumps(fresh_candidate, ensure_ascii=False), encoding="utf-8")
    second_preview = json.loads(
        _script(
            chain_db_copy,
            "-c",
            (
                "import json;"
                "from pm_agent.weekly_brief.operations import preview_capture;"
                f"c=json.load(open('{fresh_path}'));"
                "r=preview_capture(candidate=c,actor_id='copilot',"
                "idempotency_key='r5-integration-brief-002');"
                "print(json.dumps(r,sort_keys=True))"
            ),
        )
    )
    assert second_preview["status"] == "previewed"
    second_confirmed = json.loads(
        _script(
            chain_db_copy,
            "-c",
            (
                "import json;"
                "from pm_agent.weekly_brief.operations import confirm_capture;"
                f"r=confirm_capture(operation_id='{second_preview['operation_id']}',"
                f"confirmation_token='{second_preview['confirmation_token']}');"
                "print(json.dumps(r,sort_keys=True))"
            ),
        )
    )
    assert second_confirmed["status"] == "confirmed"
    brief_after_baseline = use_case_executor.execute(
        UseCaseRequest(
            contract_version="2.0",
            use_case_id="weekly-dm-brief-v2",
            parameters={},
        )
    )
    assert brief_after_baseline.status == "success"
    assert (
        brief_after_baseline.data["sections"]["changes_since_previous_snapshot"][
            "availability"
        ]
        == "available"
    )


def test_chain_import_replay_is_idempotent(chain_db_copy: Path) -> None:
    tables = (
        "project_health_reimport_assessments",
        "execution_derivation_runs",
        "execution_milestones",
        "attention_signals",
        "action_items",
        "assignments",
        "hiref",
    )
    before = {table: _count(chain_db_copy, table) for table in tables}
    workforce = json.loads(
        _script(
            chain_db_copy,
            "scripts/import_workforce_planning.py",
            "--file",
            str(ROOT / "sample-data/json/workforce_planning_import.sample.json"),
            "--confirm",
        )
    )
    capacity = json.loads(
        _script(
            chain_db_copy,
            "scripts/import_resource_capacity.py",
            "--file",
            str(ROOT / "sample-data/json/resource_capacity_import.sample.json"),
            "--confirm",
        )
    )
    health = json.loads(
        _script(
            chain_db_copy,
            "scripts/import_project_health.py",
            "--file",
            str(ROOT / "sample-data/json/project_health_reimport.sample.json"),
            "--confirm",
        )
    )
    milestones = json.loads(
        _script(
            chain_db_copy,
            "scripts/import_milestones.py",
            "--file",
            str(ROOT / "sample-data/json/milestone_import.sample.json"),
            "--confirm",
        )
    )
    assert workforce["status"] == "already_completed"
    assert capacity["status"] == "already_completed"
    assert health["status"] == "already_completed"
    assert milestones["status"] == "no_op"
    after = {table: _count(chain_db_copy, table) for table in tables}
    assert before == after
