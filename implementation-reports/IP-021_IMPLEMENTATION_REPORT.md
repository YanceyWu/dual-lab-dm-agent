# IP-021 Implementation Report

Status: `OWNER APPROVED — COMMITTED LOCALLY`
Date: 2026-07-26

## Delivered

- `connector-status-review`, `pm connector status`, and `pm connector list` now
  aggregate only portable connector metadata and local source/sync freshness.
  Runtime configuration, credentials, token files, browser profiles, and network
  readiness are not inspected.
- Offline results state that runtime probing was not performed instead of
  guessing readiness from historical sync records.
- Added `pm connector probe <connector>` as an explicit, single-connector
  runtime check with bounded JSON output.
- Atlassian OAuth refresh remains automatic during an explicit probe. Successful
  refresh is persisted and reported as `token_refreshed=true` plus
  `OAUTH_TOKEN_AUTO_REFRESHED`.
- Refresh observation is independent of the later probe result, so a refresh is
  still reported if a subsequent runtime check fails.
- Safe probe results contain status codes only; validation endpoints, cloud IDs,
  token paths, credentials, and raw exception text remain behind the local
  diagnostic boundary.

## Compatibility and safety

- Existing `pm connector validate` remains available for detailed local
  diagnostics. Its output is explicitly non-portable and must be sanitized
  before sharing.
- No schema, operational database, connector configuration, credential, token,
  or remote system was changed during implementation or tests.
- Runtime tests use synthetic validation results and fake HTTP sessions; the
  default network-denial fixture remained active.

## Validation

- Focused connector boundary suite: `5 passed`.
- Full runtime suite: `98 passed`.
- Repository tools: `18 passed, 19 subtests passed`.
- Touched-file Ruff, static compilation, portable-only source audit,
  repository-boundary check, synthetic-sample check, and diff check passed.

## Owner decision

The owner approved strictly offline status and an explicit, single-connector
probe that may automatically refresh OAuth while reporting only the refresh flag
and safe result codes.
