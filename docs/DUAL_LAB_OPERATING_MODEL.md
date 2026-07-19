# Dual-Lab Operating Model

## Constraint

Company-specific source code, operational data, internal identifiers, and
detailed artifacts remain in the company environment. Approved portable product
code, domain models, architecture, tests, and synthetic sample data may be
developed externally and transferred inward through GitHub. Any outward feedback
is optional, manually sanitized, and subject to company policy.

## Roles

### External architecture lab

Owns the north star, principles, contracts, migration order, implementation-pack
templates, evaluation standards, internal model prompts, and portable reference
implementations. It may implement and test source-independent slices using only
synthetic data. It does not implement company authentication, internal endpoints,
or company-specific mappings.

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
External architecture kit, portable implementation, and synthetic tests
                    |
                    v
GitHub portable branch or release artifact
                    |
                    v
Internal repository assessment (no edits)
                    |
                    v
Internal adapter integration and focused tests
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
- Develop portable core behavior externally when it can be validated with
  synthetic data and source-independent contracts.
- Keep company adapters, credentials, real configuration, operational databases,
  raw exports, and internal test evidence inside the company environment.
- Define architecture intent, contracts, constraints, and acceptance criteria.
- Let the internal model decide repository-specific implementation details.
- Separate analysis, implementation, and validation into distinct runs.
- Prefer one read-only reference migration before high-value write paths.
- Use `UNKNOWN` when evidence is unavailable.
- Never treat screenshots or manual transcription as permission to bypass DLP.

## Transfer classification

### Allowed into GitHub after review

- portable runtime and domain code;
- source-independent connector interfaces;
- generic migrations and schemas;
- Copilot instructions, playbooks, and skills;
- synthetic sample data and sanitized fixtures;
- automated tests that contain no internal identifiers;
- architecture and implementation packs.

### Company-local only

- operational databases and database copies;
- raw exports and downloaded source documents;
- credentials, tokens, cookies, and authentication caches;
- internal URLs, board/page identifiers, and system names;
- employee, project, customer, vendor, or issue records;
- company-specific connector implementations and mappings unless explicitly
  approved and sanitized;
- logs, screenshots, and test evidence containing real context.

## Two delivery tracks

The product track stabilizes a small set of shareable DM use cases, installation,
documentation, evidence, permissions, and user experience. The architecture track
reduces extension cost through shared use-case contracts, canonical concepts,
domain services, connector boundaries, context planning, and evaluation. Neither
track waits for the other to become perfect.
