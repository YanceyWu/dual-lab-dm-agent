# Source Portability Review

Status: `QUARANTINED`
Applies to: the current untracked `src/` checkout
Last reviewed: 2026-07-19

## Decision

The local runtime may be developed and tested in this workspace, but the current
`src/` tree must not be staged, committed, or pushed to the public repository.
The repository-boundary preflight enforces this temporary transfer quarantine.

Synthetic assets under `src/sample-data/` are an approved transfer exception.
Additional units are approved only when separately recorded below; the runtime
tree remains quarantined until those approved paths are deliberately narrowed.

## Why the quarantine exists

Path-only inspection and prior code review found portability blockers without
reading the live database or export contents:

- a company-specific endpoint default in runtime configuration;
- company/project-specific aliases in deterministic rules;
- real-looking people, project, or source identifiers in tests or documentation;
- company configuration profiles whose external distribution is not approved;
- private runtime database and export locations, which are separately ignored.

No blocker value is reproduced in this repository document.

## Review units

Each unit must be marked `APPROVED`, `SANITIZE`, `INTERNAL_ONLY`, or `UNKNOWN`.

| Unit | Current status | Required evidence |
| --- | --- | --- |
| Runtime package | APPROVED | Portable-only audit, manual terminology review, and final G0 validation pass |
| Tests and fixtures | APPROVED | Isolated test harness and synthetic fixtures pass final G0 validation |
| Sample data | APPROVED | Owner-approved fictional organization; automated checks and demo characterization pass |
| Generic configuration bootstrap | APPROVED | Generated artifacts use generic defaults, empty endpoints, and preserve an existing `.env` by default |
| Company configuration | INTERNAL_ONLY | Retain company profiles internally |
| Current documentation | INTERNAL_ONLY | Current-state documents remain local implementation references |
| Historical documentation | INTERNAL_ONLY | Exclude unless individually reviewed and still needed |
| Connector implementation | APPROVED | Uses local configuration and local private token state; final G0 validation passes |
| Dashboard assets | APPROVED | Manual terminology scan, text audit, and loopback-only default test pass |

## Approval procedure

1. Review one unit at a time; do not approve the whole tree by assumption.
2. Replace company defaults with explicit local configuration or generic
   placeholders.
3. Replace real-looking fixtures with a documented synthetic organization.
4. Separate generic configuration examples from company-only profiles.
5. Run secret, endpoint, identifier, and repository-boundary checks.
6. Run the isolated test suite and demo workflow.
7. Record reviewer, date, scope, and evidence below.
8. Narrow or remove the transfer quarantine only for approved paths.

## Approval log

No broad runtime package approval has been granted. Only the scoped units in
this log are approved for possible transfer.

### 2026-07-19 — Synthetic sample approved

- Scope: `src/sample-data/`
- Construction: rebuilt from scratch using the fictional organization in
  `standards/SYNTHETIC_DATA_STANDARD.md`
- Automated sample check: passed
- Clean demo rebuild: passed
- Semantic characterization: passed
- Workbook render and formula-error review: passed
- Owner decision: approved as the future public repository standard sample data
- Transfer decision: `APPROVED`; quarantine narrowed only for `src/sample-data/`

### 2026-07-19 — Portable text gate passed, approval pending

- Removed instance-level ServiceNow and JIRA endpoint defaults from portable
  runtime paths.
- Made the Confluence action-tracker page and project alias groups explicit
  local configuration.
- Replaced embedded project aliases in the HIREF report path with the shared,
  configurable deterministic alignment rule.
- Rebuilt the lightweight seed and touched tests using the approved synthetic
  organization and reserved identifiers.
- Added a portable `.env.example` with empty connector endpoints, credentials,
  report IDs, and optional local alias configuration.
- Classified company configuration, historical documentation, and internal UAT
  as permanently non-portable units.
- Automated evidence: 37 runtime tests, 18 tool tests, repository boundary,
  synthetic checker, portable-only audit, demo build, seed build, and static
  compilation pass.
- Transfer decision: `NOT YET APPROVED`; manual unit review and quarantine
  narrowing remain.

### 2026-07-19 — Generic configuration bootstrap approved

- Scope: `src/pm_agent/repo_tools/bootstrap.py`, `src/.env.example`, and the
  temporary-directory bootstrap contract test.
- Manual review: generated baseline, team, and project values use the approved
  fictional organization; connector endpoints remain empty.
- Contract evidence: first-run scaffolding generates only generic defaults and
  ordinary initialization preserves an existing `.env` without reading or
  rewriting it.
- Automated evidence: focused bootstrap test passes; full isolated runtime
  suite passes with 39 tests; portable-only audit, repository-boundary check,
  synthetic-data check, static compilation, and diff check pass.
- Transfer decision: `APPROVED` for this unit only. The runtime-source
  quarantine remains in force until its approved paths are narrowed deliberately.

### 2026-07-19 — Dashboard surface approved; connector scope requires sanitization

- Dashboard scope: `src/pm_agent/dashboard/` and the dashboard CLI entrypoint.
- Manual review: no embedded concrete endpoints, email domains, or source
  identifiers were found in the dashboard surface; the dashboard text audit
  passes.
- Safety correction: the dashboard service and CLI now bind to `127.0.0.1` by
  default rather than all network interfaces; an explicit host option remains
  available for an intentional local deployment choice.
- Automated evidence: the loopback-default test passes; full isolated runtime
  suite passes with 40 tests; portable-only audit, repository-boundary check,
  synthetic-data check, static compilation, and diff check pass.
- Connector review: a source-specific Confluence synchronization branch remains
  in the connector implementation. It is classified `SANITIZE`; no connector
  source path is approved by this entry.
- Transfer decision: `APPROVED` for the dashboard scope only. The runtime-source
  quarantine remains in force until its approved paths are narrowed deliberately.

### 2026-07-19 — Connector sanitization completed

- Removed the dedicated source-specific Confluence discovery branch; status-page
  work now comes only from locally configured registry rows.
- Restricted token discovery to the runtime's local private state.
- Replaced the opaque action-tracker identifier with a generic name and added a
  local database migration that preserves existing rows.
- Replaced touched CLI examples and tests with the approved fictional language.
- Automated evidence: 42 isolated runtime tests, 18 tool tests, portable-only
  audit, repository-boundary check, synthetic-data check, and diff check pass.
- Transfer decision: `REVIEW`; complete the remaining path-level classification
  before narrowing the runtime-source quarantine.

## Non-approval

A successful test run, absence of credentials, or generic filename does not by
itself make an artifact portable. When evidence is incomplete, use `UNKNOWN` and
keep the artifact local.
