# IP-022 — Dashboard Write Boundary

## Business goal

Prevent a Dashboard click or unconfirmed HTTP request from directly starting a
networked JIRA synchronization or exposing connector details.

## Required workflow

```text
preview exact target scope
  -> explicit user confirmation
  -> one-time token claim
  -> bounded sync
  -> safe result and durable audit state
```

## Contracts and constraints

- The preview performs no connector call.
- Confirmation requires the preview execution ID and short-lived token.
- Tokens are stored only as hashes and cannot be replayed.
- The confirmed scope is immutable and contains only active board IDs selected
  during preview.
- Browser results contain safe codes, counts, board IDs, and execution ID; raw
  errors, URLs, tokens, paths, and logs are excluded.
- Dashboard binding remains loopback-only unless the operator explicitly enables
  a non-loopback host.
- The sync updates local snapshots and does not modify remote JIRA records.

## Acceptance and rollback

Tests cover preview-without-write, exact stale scope, explicit confirmation,
replay rejection, safe connector failure, and non-loopback opt-in. Rollback
removes the additive operation-audit table, boundary helper, two-stage endpoint,
and UI confirmation flow; connector implementations and existing snapshots are
unchanged.
