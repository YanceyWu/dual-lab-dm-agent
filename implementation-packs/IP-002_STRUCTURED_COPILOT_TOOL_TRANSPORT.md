# IP-002 — Structured Copilot Tool Transport

## Business goal

Let a Delivery Manager use VS Code Copilot to ask a natural-language question
or issue an approved command, then receive a grounded answer from one approved
local use case. Copilot must invoke the structured, deterministic tool boundary
instead of inspecting SQLite directly or parsing human-formatted CLI output.

## Architecture intent

VS Code Copilot is the natural-language interaction and reasoning layer. It
interprets a question or command, selects an allowed operation, and constructs
a bounded structured request. The local transport is a thin adapter over the
existing application executor: it validates that request, calls the executor,
and returns the unchanged structured result. Neither Copilot nor the transport
owns business routing, workload calculation, or data persistence.

## Verified current problem indicators

- IP-001 provides a registered `team-workload-overview` implementation with a
  versioned request/result envelope.
- The CLI and Dashboard invoke the reference implementation, but no structured
  command exposes use-case discovery, schema description, or query execution
  for Copilot consumption.
- The current request does not yet declare an operation or correlation ID.

## Required outcome

Provide one VS Code Copilot-facing structured tool transport supporting only
`list`, `describe`, and `query` for the read-only reference use case. It must
support both a natural-language request and an approved command-oriented request
through the same normalized tool call, remain usable without Copilot for local
verification, and preserve the executor/result meaning used by existing
interfaces.

Reference user paths:

```text
Natural language: "Which delivery-team members have capacity?"
Approved command: request the team-workload overview for a named team
VS Code Copilot: interpret/select/normalize
Structured tool request: operation=query, use_case_id=team-workload-overview
Local executor: deterministic read-only result
VS Code Copilot: explain evidence, freshness, warnings, and uncertainty
```

The exact Copilot customization mechanism (for example, repository guidance,
a custom agent, prompt, or supported command surface) must be selected during
local discovery based on the installed VS Code Copilot capabilities. It is not
part of the application contract and must be replaceable without runtime changes.

## Required contracts

Extend the transport-neutral request only with backwards-compatible fields:

```text
contract_version: string
use_case_id: string, required for describe and query
operation: list | describe | query
actor: stable anonymous local actor identifier
parameters: object
requested_output: json
confirmation_token: absent for this pack
correlation_id: optional caller trace identifier
```

Define stable JSON schemas for:

- a use-case catalogue item: ID, contract version, supported operations,
  read/write mode, and short purpose;
- a use-case description: input parameter schema, output contract version,
  read/write mode, and known failure statuses;
- a tool response: the unchanged `UseCaseResult` plus transport validation
  errors where a use case cannot be invoked.

The response must retain the executor-generated execution ID. No transport may
invent facts, calculate workload, or turn an unavailable source into empty data.

## Mandatory constraints

- Reuse the IP-001 executor and `team-workload-overview` implementation.
- Preserve existing CLI and Dashboard behavior.
- Implement no write operation, confirmation flow, HTTP server, MCP server, or
  Copilot-specific business rule.
- Never accept database paths, connector URLs, credentials, or raw source
  payloads as tool parameters or output.
- Keep all data in synthetic fixtures during automated validation.

## Local repository discovery

Before implementation, identify and record:

- the existing CLI command registration and JSON-rendering conventions;
- the executor registration and request/result models;
- the installed VS Code Copilot customization and command capabilities, and
  existing repository instructions for Copilot behavior;
- focused test fixtures that provide temporary databases and deny network use;
- any local path that would expose private configuration or operational state.

Report a conflict and stop if a proposed transport needs a source-specific
connector, a new model runtime, a database schema migration, or a write path.

## Reference migration scope

- Add one structured local command or equivalent process-local adapter that VS
  Code Copilot can call after natural-language or command interpretation.
- Register metadata for only `team-workload-overview`.
- Route its `query` operation through the IP-001 executor.
- Add a concise portable Copilot usage policy that directs Copilot to this tool
  contract for the reference question.

## Acceptance criteria

1. `list` returns the reference use case and no private runtime data.
2. `describe` returns the published request/response contract without invoking
   a repository or connector.
3. `query` returns the same data and execution ID semantics as direct executor
   invocation.
4. Invalid operation, invalid parameters, and unknown use case return stable
   `invalid` or `unavailable` results rather than a traceback or empty data.
5. Existing CLI workload output and Dashboard JSON behavior remain equivalent.
6. The same normalized tool request is produced for an equivalent
   natural-language question and approved command-oriented request.
7. Copilot guidance prohibits direct database inspection and formatted CLI
   parsing for the migrated reference question, and requires an explicit
   uncertainty statement when the tool reports unknown, partial, or unavailable.
8. Focused transport, contract, CLI, and regression tests pass offline.

## Non-goals

- Mandatory MCP adoption or a second embedded LLM runtime.
- Dependence on one VS Code Copilot customization mechanism.
- Any write-capable operation.
- Migration of another use case.
- Evidence freshness logic beyond IP-003's envelope work.

## Test and validation requirements

- Contract tests for list, describe, query, invalid operation, unknown use case,
  and parameter validation.
- Equivalence tests showing a natural-language and command-oriented request are
  normalized to the same allowed tool call; the test uses synthetic inputs and
  does not rely on a live Copilot service.
- A synthetic successful workload query and a no-data/unavailable query.
- Regression tests for the existing CLI renderer and Dashboard endpoint.
- Static compilation, full runtime tests, repository-boundary check,
  synthetic-sample check, portable-only audit, and diff check.

## Rollback requirements

Remove the transport adapter and its registration metadata. The IP-001 executor,
legacy CLI route, Dashboard endpoint, database, and private state remain
unchanged, so rollback must require no migration or data restoration.

## Required final report

Report the actual VS Code Copilot integration surface, normalization boundary,
schemas, modules changed, reused executor, validation evidence, known
Copilot-host assumptions, residual risks, rollback, and the recommended next
pack.
