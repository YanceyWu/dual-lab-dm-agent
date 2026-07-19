# IP-002 Implementation Report

Status: `IMPLEMENTED LOCALLY — G2 REMAINS BLOCKED BY IP-003`
Branch: `codex/ip-000-baseline-safety`
Date: 2026-07-19

## Outcome

Added a structured, read-only local tool transport for VS Code Copilot and
command-line verification. A Delivery Manager may ask Copilot a natural-language
workload question or use the approved command path; Copilot is instructed to
normalize either path to the same local JSON query.

The transport exposes only `list`, `describe`, and `query` for
`team-workload-overview`. It reuses the IP-001 executor and does not perform
workload calculations, inspect the database directly, or allow writes.

## Modules and assets changed

- `src/pm_agent/use_cases/service.py`: adds operation and correlation-ID fields
  to the backwards-compatible request metadata.
- `src/pm_agent/use_cases/execution.py`: adds public use-case descriptors and
  enforces allowed operations.
- `src/pm_agent/use_cases/tool_transport.py`: structured list/describe/query
  adapter over the existing executor.
- `src/pm_agent/cli/commands/tool_transport.py` and CLI wiring: `pm tool`
  JSON-only commands.
- `.github/copilot-instructions.md`: repository-wide VS Code Copilot guardrail.
- `.github/prompts/dm-workload.prompt.md`: reusable VS Code Copilot prompt for
  workload/availability questions.
- `src/tests/test_unified_use_case_contract.py`: structured transport and CLI
  equivalence coverage.

## Supported commands

```bash
pm tool list
pm tool describe team-workload-overview
pm tool query team-workload-overview [--team "Exact Team Name"]
```

## Validation

- Focused transport and CLI tests: `14 passed`.
- Full runtime test suite: `49 passed`.
- Repository tool tests: `18 passed, 19 subtests passed`.
- Static compilation, portable-only audit, repository-boundary check,
  synthetic-sample check, and `git diff --check`: passed.
- Demo smoke query through the current module entry point: passed with a
  JSON-only success result.

## Known Copilot-host assumption

VS Code supports repository custom instructions and prompt files, but their
availability/configuration depends on the user's installed Copilot setup. The
repository artifacts are portable; the structured CLI remains independently
usable if a particular Copilot customization surface changes.

The checked-in virtual environment's existing `pm` launcher was not installed
against the new working-tree package during this implementation. The documented
module entry point and automated CLI tests exercise the current code; a normal
editable install refreshes the launcher.

## Remaining risks and rollback

Natural-language interpretation remains probabilistic, so the command response
is the authoritative boundary. Remove the `pm tool` group and the `.github`
guidance artifacts to roll back IP-002; this requires no schema or data change.

## Recommended next pack

Implement IP-003 before declaring G2 complete. Freshness, assumptions,
alternatives, durable trace lookup, and evidence redaction remain outstanding.
