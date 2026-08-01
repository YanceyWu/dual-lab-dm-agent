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

Build the demo database:

```bash
PYTHONPATH=src src/.venv/bin/python src/scripts/load_sample_data.py --force
```

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
