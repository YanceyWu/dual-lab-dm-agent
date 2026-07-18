# Connector Standard

## Responsibility

A connector acquires source data, records provenance and synchronization state,
performs source-level parsing, and maps observations toward canonical contracts.
It does not own project-health judgment, staffing rules, allocation scoring, or
management recommendations.

## Required contract

Every connector defines:

- stable connector ID and supported source type;
- authentication and authorization boundary;
- acquisition mode and incremental-sync behavior;
- raw-record and provenance format;
- mapping result, validation errors, and unknown fields;
- retry, timeout, rate-limit, and partial-failure behavior;
- freshness and last-success metadata;
- idempotency and duplicate-handling rules;
- sanitized fixtures and contract tests.

## Boundary rules

- Use cases and domain services do not know source URLs or authentication.
- Raw source shapes do not become the public domain API.
- Source records remain traceable after canonical mapping.
- Connector failures return explicit status; they are not converted into empty
  business facts.
- Adding a connector must not require edits to unrelated business use cases.
- Credentials and unrestricted raw payloads must not enter logs or model context.
