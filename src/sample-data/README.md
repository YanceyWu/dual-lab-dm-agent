# Synthetic Sample Data

Dataset marker: `SYNTHETIC_DATASET_V1`

This directory represents the fictional organization defined in
`standards/SYNTHETIC_DATA_STANDARD.md`:

- Alex, Blair, Casey, and Drew Example;
- Project Atlas, Project Beacon, and Project Cedar;
- reserved `99`-prefixed employee and project IDs;
- `.invalid` URL and email domains;
- invented allocations, skills, milestones, risks, contracts, and change records.

The dataset was reconstructed from scratch for testing. It is not an anonymized
copy of a real organization.

## Validation

From the repository root:

```bash
python3 tools/check_synthetic_samples.py
```

## Demo database (R1 synthetic integration pipeline)

Build the demo database from a clean database:

```bash
PYTHONPATH=src src/.venv/bin/python src/scripts/load_sample_data.py --force
```

An idempotent re-run on an existing demo database (no duplicate assessments,
attention items, or snapshots):

```bash
PYTHONPATH=src src/.venv/bin/python src/scripts/load_sample_data.py --replay
```

The pipeline runs, in order: bootstrap, versioned workforce planning import,
versioned resource capacity import, board registration, deterministic
synthetic evidence seeding, canonical Milestone import, Project Health
re-import (canonical derivation plus seven-dimension assessment through the
IP-033 entry), Delivery Attention reconciliation, and a confirmed Weekly
Brief v2 snapshot.  Milestone and evidence data precede the assessment so the
demo shows real dimension states.

After a build, these commands return non-empty, contract-compliant results
for the same synthetic demo database:

```bash
export DATABASE_PATH="$PWD/src/sample-data/demo/sample_pm.db"
export PYTHONPATH="$PWD/src"
python3 -m pm_agent.cli.app tool query layered-project-health-review --project project-synthetic-atlas
python3 -m pm_agent.cli.app tool query delivery-execution-review --project project-synthetic-atlas
python3 -m pm_agent.cli.app tool query delivery-attention-center
python3 -m pm_agent.cli.app tool query resource-capacity-heatmap --param year=2026 --param month=8 --param plan_version_id=plan-synthetic-baseline-001
python3 -m pm_agent.cli.app weekly-brief query
```

The demo database contains the versioned clean-import organization
(`member-synthetic-001/002/003`, `project-synthetic-atlas`,
`project-synthetic-beacon`, `plan-synthetic-baseline-001`). It is not the
legacy Excel-imported Example organization; the versioned imports require an
empty target database.  Legacy `assignments` mirror the canonical monthly
allocations exactly (member 001 = 0.5, member 002 = 0.0, member 003 = 1.2
across both projects), so the legacy load view and the canonical capacity
facts agree.

Known demo states (deliberate mix, all honest):

- `schedule` is `red` (one critical Milestone is overdue);
- `scope` is `amber` (release scope completion is below the green minimum);
- `delivery`, `quality`, and `governance` are `not_available`: the current
  derivation has no approved producer for sprint-completion facts and the
  structured quality/governance input family is reserved;
- `resource` is `not_available`: the IP-033 assessment entry does not pass a
  capacity scope (the dedicated reader supports it; wiring is a separately
  reviewable change);
- `dependency` is `unknown`: Phase 3 proves an active link only, without
  readiness semantics.

The Delivery Attention Center demonstrates five rules (project health red,
critical milestone overdue, resource overload, overdue action, source
freshness) with eight items across both projects, the Resource Capacity
heatmap returns three known rows (member 003 overloaded `red`), and the
Weekly Brief v2 overall state is `red` with non-empty attention and
next-action sections.  Achievements appear only in queries made after the
snapshot date, per the event-window contract.

HIREF / contract-continuity demo states: member 001 has a current contract
plus a registered renewal, member 002 is expiring within 60 days without a
renewal (critical), member 003 has no current contract (missing), and one
HIREF slot is free with an open staffing placeholder.  `pm hiref summary`,
`pm hiref review`, `pm hiref slots`, `pm hiref placeholders`, and
`contract-continuity-review` all return non-empty, contract-compliant results.

The generated database is classified as synthetic only while every input passes
the checker and the characterization suite passes.

`json/project_health_reimport.sample.json` is the versioned Project Health
clean re-import package. It intentionally contains no Quality, Resource, or
Governance observations, so those dimensions remain `not_available`.

`json/workforce_planning_import.sample.json` is the versioned, authoritative
workforce/project/plan/monthly-allocation clean-import package. It uses only
stable synthetic identifiers and includes an explicit zero allocation so that
known zero remains distinguishable from a missing manifest record.

`excel/team_project_capacity_workbook_hiref_sample.xlsx` is a synthetic, valid
sample workbook for the current workbook onboarding path. It demonstrates the
B4 simplified HIREF contract: `Members.next_hiref_id`, `Allocations.hiref_id`
for open demand, and an optional `HIREF Requests` sheet that supplies the
minimum explicit slot facts still needed by retained HIREF consumers. The
header-only review template for this workbook contract lives at
`templates/team_project_capacity_workbook_template.xlsx`.

## Transfer status

`APPROVED_FOR_PUBLIC_TRANSFER`.

The owner approved this synthetic organization for use as the public standard
sample dataset on 2026-07-19. This approval applies only to `src/sample-data/`.
