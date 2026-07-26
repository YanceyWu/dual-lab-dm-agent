# Source Portability Decision

Status: `PORTABLE CANDIDATE — AUTOMATED GATES REQUIRED FOR EVERY CHANGE`
Last updated: 2026-07-26

## Current decision

The tracked runtime, tests, generic configuration examples, synthetic sample
data, repository tools, architecture, and operating documentation comprise the
portable release candidate on `codex/ip-000-baseline-safety`.

This classification applies only to reviewed Git-tracked content. It does not
approve any work-computer file, ignored file, company-derived value, operational
record, local configuration, connector payload, or test evidence.

## Portable candidate units

| Unit | Decision | Required continuing evidence |
| --- | --- | --- |
| Runtime package and CLI | `PORTABLE` | Isolated tests, Ruff, compilation, manual terminology review |
| Database bootstrap and migrations | `PORTABLE` | Synthetic legacy migration, integrity, view, aggregate, and rollback rehearsal |
| Dashboard | `PORTABLE` | Packaged-asset check, loopback default, write-boundary tests |
| Generic connectors and contracts | `PORTABLE` | Empty local defaults, safe errors, offline contract tests |
| Tests and fixtures | `PORTABLE` | Temporary database, denied network, synthetic-only values |
| Sample data | `PORTABLE` | Synthetic-data checker and fictional reserved identifiers |
| Agent and operator documentation | `PORTABLE` | No company context; commands must match the current runtime |
| Generic configuration examples | `PORTABLE` | Empty endpoints and credentials; example-only identifiers |

## Permanently local or excluded

- company source code and company-specific connector adaptations;
- operational databases and every database copy;
- raw exports, imports, downloaded documents, logs, and screenshots;
- credentials, tokens, cookies, authentication caches, endpoints, and cloud IDs;
- employee, project, customer, vendor, issue, or contract records;
- company configuration and internal mappings;
- internal test evidence containing real names, identifiers, paths, or values.

These units must remain ignored or outside the repository. Repository privacy
does not change this rule.

## Required gate

Before staging, committing, transferring, tagging, or publishing a changed
candidate, run from the repository root:

```bash
make validate
make rehearse-release
```

The automated gate is necessary but not sufficient. Review changed text and
paths manually, stage exact intended files, and stop when classification is
uncertain. Use `UNKNOWN` rather than assuming a company-derived artifact is
portable.

## Work-computer rule

Real-environment validation stays on the work computer. Only sanitized
pass/fail/blocked/partial outcomes, generic categories, non-sensitive counts or
ranges, and the candidate commit/tag may leave that environment when policy
permits. Never copy raw logs, records, screenshots, endpoints, identifiers, or
configuration back into this repository.
