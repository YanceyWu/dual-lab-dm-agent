# Copilot implementation task

You are authorized to implement **only `[PHASE] [BATCH] [CAPABILITY]`** under
`[DESIGN]` and `[IMPLEMENTATION PACK]`. Do not begin any later batch.

Required preflight: read `AGENTS.md`, `PROGRESS.md`, the named design/pack, and
`implementation-packs/INDEX.md`; verify branch/HEAD/clean worktree; inspect the
real owner module, schema, call path, and focused tests.

Scope: `[EXACT APPROVED OUTCOME]`.
Owner module: `[OWNER]`; allowed dependencies: `[DEPENDENCIES]`.
Forbidden: `[LIST]`, all live connectors/real data, and all unapproved public
interfaces or writes.

Implement only deterministic, synthetic-data behavior. Preserve legacy
contracts. Add focused tests for success, missing/stale/partial/conflicting
data, replay/concurrency where applicable, and compatibility. Run focused tests
then `make validate`; also run `make rehearse-release` if schema/import/migration
or installed behavior changes.

Perform a separate read-only review before claiming completion. Update
`PROGRESS.md`, stage explicit filenames, commit locally, do not push, and report
the six mandatory completion sections from the Continuation Kit.
