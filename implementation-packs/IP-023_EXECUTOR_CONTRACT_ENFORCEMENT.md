# IP-023 — Executor Contract Enforcement

## Business goal

Make the shared executor the authoritative validation boundary so Copilot, CLI,
and Dashboard cannot silently reinterpret invalid inputs.

## Contract

- Reject unsupported contract versions.
- Reject unknown, missing, mistyped, empty, overlong, out-of-range, and
  non-enumerated parameters before invoking a handler.
- Determine read-only/write-capable mode from the registered descriptor, never
  from the presence of a confirmation token.
- Return stable structured warning codes without raw exception text.
- Preserve correlation ID and generate an execution ID for every result.

## Acceptance and rollback

Tests prove invalid input never invokes the use case, `days=9999` is rejected,
unknown parameters are rejected, token presence cannot change read-only mode,
unsupported versions fail safely, and internal exceptions are classified
without leakage. Rollback restores permissive executor dispatch and prior string
warnings without changing stored business data.
