# Dual-Lab Operating Model

## Constraint

Company source code, operational data, internal identifiers, and detailed
artifacts remain in the company environment. Approved external architecture
material may flow inward. Any outward feedback is optional, manually sanitized,
and subject to company policy.

## Roles

### External architecture lab

Owns the north star, principles, contracts, migration order, implementation-pack
templates, evaluation standards, and internal model prompts. It defines required
outcomes without inventing repository-specific file changes.

### Internal repository architect

Inspects the real repository, maps an implementation pack onto existing
components, identifies conflicts, proposes the minimum compatible insertion
point, and does not edit code.

### Internal implementation engineer

Implements only the bounded pack, reuses existing infrastructure, preserves
working behavior, adds focused tests, and reports deviations.

### Internal validation reviewer

Independently checks the implementation against the pack, architecture intent,
tests, behavior preservation, and rollback requirements.

## Standard flow

```text
External architecture kit and implementation pack
                    |
                    v
Internal repository assessment (no edits)
                    |
                    v
Bounded implementation and focused tests
                    |
                    v
Independent internal validation
                    |
                    v
Release or correction
                    |
                    v
Optional policy-approved sanitized feedback
```

## Governance rules

- Use strangler migration; do not rewrite the usable base.
- Define architecture intent, contracts, constraints, and acceptance criteria.
- Let the internal model decide repository-specific implementation details.
- Separate analysis, implementation, and validation into distinct runs.
- Prefer one read-only reference migration before high-value write paths.
- Use `UNKNOWN` when evidence is unavailable.
- Never treat screenshots or manual transcription as permission to bypass DLP.

## Two delivery tracks

The product track stabilizes a small set of shareable DM use cases, installation,
documentation, evidence, permissions, and user experience. The architecture track
reduces extension cost through shared use-case contracts, canonical concepts,
domain services, connector boundaries, context planning, and evaluation. Neither
track waits for the other to become perfect.
