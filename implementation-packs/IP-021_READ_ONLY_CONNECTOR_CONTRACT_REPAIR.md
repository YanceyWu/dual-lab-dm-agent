# IP-021 — Read-Only Connector Contract Repair

## Goal

Make connector status genuinely offline and side-effect free, while providing a
separate explicit runtime probe whose internal OAuth refresh remains automatic
and visible only as a safe outcome flag.

## Owner decision

- `connector-status-review`, `pm connector status`, and `pm connector list` must
  not inspect runtime configuration, credentials, endpoints, browser profiles,
  token files, or network readiness.
- A user explicitly starts runtime checking with `pm connector probe`.
- During an explicit probe, an expired Atlassian OAuth token is automatically
  refreshed and saved. The user is told that a refresh occurred, but token
  content, endpoint, cloud ID, and local token path are never returned.

## Implemented scope

- Offline status is built only from portable connector module metadata and local
  `data_sources` / `sync_runs` records.
- Runtime readiness is returned as `not_performed` / `null`, not guessed from
  historical freshness.
- `pm connector probe <jira|confluence|servicenow>` requires one explicit
  connector scope and returns bounded JSON with
  readiness, auth mode, `token_refreshed`, and safe warning/error codes.
- JIRA and Confluence auth sessions record whether the current probe refreshed
  an OAuth token.
- Raw validation details and exception text do not cross the safe probe
  boundary.
- Existing `pm connector validate` remains a local diagnostic compatibility
  command. Its detailed output is not a portable or shareable result.

## Acceptance scenarios

1. Offline status succeeds when runtime validation, token loading/saving, and
   network access are replaced with fail-fast guards.
2. Status never exposes endpoint, credential, token path, cloud ID, or raw
   error text.
3. An expired OAuth token is refreshed, persisted, used by the probe, and
   reported as `token_refreshed=true`.
4. Safe probe output reports `OAUTH_TOKEN_AUTO_REFRESHED` without returning
   token or endpoint details.
5. Failed probes return bounded error codes rather than connector exception
   strings.

## Rollback

Revert the offline status aggregator, safe probe command/result, auth refresh
flag, tests, and documentation. No schema or operational connector data is
changed by this pack.
