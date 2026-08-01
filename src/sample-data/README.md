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
versioned resource capacity import, board registration, Project Health
re-import (canonical derivation plus seven-dimension assessment through the
IP-033 entry), canonical Milestone import, one deterministic derivation replay
(so Milestone facts are readable), Delivery Attention reconciliation, and a
confirmed Weekly Brief v2 snapshot.

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
(`member-synthetic-001/002`, `project-synthetic-atlas`,
`plan-synthetic-baseline-001`). It is not the legacy Excel-imported Example
organization; the versioned imports require an empty target database.

Known demo limitations: the IP-033 assessment runs before Milestone import per
the usability handoff order, so the schedule dimension is `unknown` (Milestone
facts are then exposed by the derivation replay); Quality, Resource, and
Governance observations are intentionally absent, so those dimensions remain
`not_available`.

The generated database is classified as synthetic only while every input passes
the checker and the characterization suite passes.

`json/project_health_reimport.sample.json` is the versioned Project Health
clean re-import package. It intentionally contains no Quality, Resource, or
Governance observations, so those dimensions remain `not_available`.

`json/workforce_planning_import.sample.json` is the versioned, authoritative
workforce/project/plan/monthly-allocation clean-import package. It uses only
stable synthetic identifiers and includes an explicit zero allocation so that
known zero remains distinguishable from a missing manifest record.

## Transfer status

`APPROVED_FOR_PUBLIC_TRANSFER`.

The owner approved this synthetic organization for use as the public standard
sample dataset on 2026-07-19. This approval applies only to `src/sample-data/`.
