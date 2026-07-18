# Dual-Lab Delivery Manager Agent

This repository is the external architecture control plane for a Delivery
Management Decision Support System developed under a one-way information-flow
constraint.

The company repository and company data never enter this repository. This
repository contains portable architecture, contracts, prompts, implementation
packs, evaluation standards, and sanitized feedback templates that can be
downloaded into the company environment.

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
  architecture, contracts, packs, tests, governance
                    |
                    | one-way approved transfer
                    v
Company Environment
  repository inspection, local adaptation, implementation, validation
                    |
                    v
Sanitized human-reviewed feedback (only when policy permits)
```

The external lab defines what the system must become. The internal model maps
that intent to the real repository and decides how to implement it locally.

## Repository map

- `architecture/`: north star, component model, domain model, decisions.
- `standards/`: use-case, connector, AI reasoning, and validation standards.
- `implementation-packs/`: bounded changes for the internal implementation model.
- `prompts/`: reusable internal architect, implementer, reviewer, and reconstruction prompts.
- `templates/`: sanitized feedback and implementation-pack templates.
- `research-input/`: manually reconstructed, sanitized facts from the company environment.

## Initial migration strategy

1. Establish behavior snapshots, execution tracing, and smoke tests.
2. Introduce one shared use-case execution contract using a read-only use case.
3. Separate user use cases, domain services, platform services, and connectors.
4. Establish the canonical delivery model without a full database rewrite.
5. Migrate staffing recommendation as the first high-value reference use case.
6. Add scenario-based evaluation before expanding internal adoption.

## Security boundary

Never commit company source code, internal names, URLs, credentials, real issue
content, employee data, customer data, internal architecture identifiers, or
screenshots captured in violation of company policy. Company policy takes
precedence over personal privacy settings and repository visibility.

