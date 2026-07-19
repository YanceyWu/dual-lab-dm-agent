# Dual-Lab Delivery Manager Agent

This repository is the external architecture control plane and portable product
lab for a Delivery Management Decision Support System developed under a
restricted information-flow model.

Company-specific source, company data, credentials, internal identifiers, and
private runtime state never enter this repository. Portable product-core code,
domain models, architecture, contracts, prompts, tests, implementation packs,
and sanitized sample data may be developed and versioned here, then downloaded
into the company environment for internal integration and validation.

## Mission

Build an internally usable and shareable Delivery Manager system that:

- consolidates project, people, assignment, capacity, contract, risk, action,
  decision, and release information;
- maps source-specific records into a canonical delivery model;
- supports recurring Delivery Manager use cases;
- combines deterministic calculations with grounded model reasoning;
- evolves from the existing usable base through incremental migration.

## Dual-Lab operating model

```text
Personal AI Lab / Codex
  architecture, portable core, models, packs, tests, governance
                    |
                    | GitHub transfer of approved portable artifacts
                    v
Company Environment
  internal adapters, real data, local adaptation, validation, debugging
                    |
                    v
Sanitized human-reviewed feedback (only when policy permits)
```

The external lab may implement portable, synthetic-data-tested slices. The
internal model maps them to approved company integrations, runs real-environment
validation, and reports only policy-approved sanitized feedback.

## Repository map

- `architecture/`: north star, component model, domain model, decisions.
- `standards/`: use-case, connector, AI reasoning, and validation standards.
- `implementation-packs/`: bounded changes for the internal implementation model.
- `prompts/`: reusable internal architect, implementer, reviewer, and reconstruction prompts.
- `templates/`: sanitized feedback and implementation-pack templates.
- `research-input/`: manually reconstructed, sanitized facts from the company environment.
- `tools/`: repository-boundary and synthetic-sample preflight checks.

## Start here

1. Read `docs/DUAL_LAB_OPERATING_MODEL.md` for the one-way workflow.
2. Read `architecture/04_COPILOT_LOCAL_AGENT_ARCHITECTURE.md` for the detailed
   local product and Copilot Agent design.
3. Use `ROADMAP.md` and `implementation-packs/INDEX.md` for the gated migration
   sequence.
4. Transfer the relevant architecture kit and prompt into the company environment.
5. Run `prompts/TECHNICAL_RECONSTRUCTION_SCREENSHOT.md` internally when a
   sanitized implementation baseline is needed.
6. Use `implementation-packs/` for bounded migration work.
7. Validate every pack with the independent reviewer prompt before promotion.

## Local development safety checks

Run these before any staging or transfer:

```bash
python3 tools/check_repository_boundary.py
python3 tools/check_synthetic_samples.py
PYTHONPATH=src src/.venv/bin/python -m pytest -q src/tests
```

The current `src/` tree is intentionally transfer-quarantined. Do not narrow its
ignore rule until the relevant unit has an approval entry in
`docs/SOURCE_PORTABILITY_REVIEW.md`. The synthetic-data contract is defined in
`standards/SYNTHETIC_DATA_STANDARD.md`.

## Initial migration strategy

1. Establish behavior snapshots, execution tracing, and smoke tests.
2. Introduce one shared use-case execution contract using a read-only use case.
3. Separate user use cases, domain services, platform services, and connectors.
4. Establish the canonical delivery model without a full database rewrite.
5. Migrate staffing recommendation as the first high-value reference use case.
6. Add scenario-based evaluation before expanding internal adoption.

## Security boundary

Never commit company-specific source code, internal names, URLs, credentials,
real databases, raw exports, real issue content, employee data, customer data,
internal architecture identifiers, or screenshots captured in violation of
company policy. Portable code must use abstract connector contracts, generic
configuration, and synthetic fixtures. Company policy takes precedence over
personal privacy settings and repository visibility.
