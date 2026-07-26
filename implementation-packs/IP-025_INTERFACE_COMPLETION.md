# IP-025 — Interface Completion

## Business goal

Give Copilot, CLI, and Dashboard one consistent read-only application contract
without forcing a one-time Dashboard rewrite.

## Interface contract

- `pm tool query` accepts repeatable generic `--param key=value` values and
  retains the existing convenience options.
- Generic values use JSON scalar/object/array decoding; invalid types and
  unknown fields remain executor errors.
- Duplicate generic keys or collisions with convenience options are rejected.
- Dashboard exposes a generic read-only structured query endpoint returning the
  complete `UseCaseResult`.
- Write-capable descriptors cannot use the generic Dashboard query route.
- Existing Dashboard routes remain compatible, while response headers identify
  direct-SQL legacy reads and result projections.
- Interface-equivalence tests compare status, data, evidence, freshness,
  warnings, and contract version.

## Migration and rollback

The generic CLI option and Dashboard endpoint are additive. Existing fixed CLI
options and Dashboard payloads remain available. Rollback removes the additive
surfaces and legacy markers without changing use cases or stored data.
