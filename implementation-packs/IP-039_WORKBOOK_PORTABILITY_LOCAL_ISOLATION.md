# IP-039 Workbook portability and local-data isolation

Status: owner-authorized; implementation pending.

Authority: `docs/superpowers/specs/2026-08-09-ip-039-workbook-portability-local-isolation-design.md`.

## Objective

Ship the supported source preparation kit, add deterministic exports for only
the user-maintained source facts used by the Legacy release, and make
demo-to-local switching create and select a genuinely isolated local database.

## Owners and allowed dependencies

- Team/Project + Capacity/HIREF export owner: workbook onboarding; depend only
  on authoritative source facts and the existing workbook preset.
- Project Profile and JIRA/Confluence registry export owners: their existing
  source-contract capabilities; preserve their current workbook/CSV formats.
- CLI owner: existing onboarding command group; keep orchestration thin.
- Package/setup owner: lean usage-bundle builder and its generated helpers.
- Documentation/template owner: the existing workbook template, synthetic
  sample, and onboarding guidance lineage.

No schema, migration, connector, Dashboard surface, import contract, or business
write authority is in scope.

## Required behavior

1. Remove only the empty configs directory and optional workload Prompt File
   from the generated lean bundle; retain the custom agent and workspace
   instructions.
2. Add the workbook template, synthetic sample, and concise bundle guide under
   one top-level workbook directory.
3. Add explicit-path, atomic, no-overwrite-by-default exports for:
   Team/Project + Capacity/HIREF workbook, Project Profile workbook, JIRA Board
   Registry CSV, and Confluence Page Registry CSV. Every artifact must preview
   through its existing import handler.
4. Remove export dependencies on derived current-state staffing, contract
   coverage, Project Health/snapshot, freshness, sync, publication-history,
   derivation, execution-trace, and audit data. Those outputs are regenerated
   after source import and are neither exported nor export preconditions.
   The sole retained source-lineage dependency is the newest completed
   `pm onboarding` source receipt for the selected workbook plan; it preserves
   original Setup horizon and Capacity presence/source identity. Never fall
   back to an older receipt when the newest one is incomplete or corrupt.
5. Make an explicit demo-to-local transition atomically select `data/pm.db`,
   initialize and validate it, update setup state after smoke, and prove the
   demo database remains unchanged.
6. Update Copilot routing and the bundle README for source prepare/import,
   export, and local-mode transition.

## Stop conditions

- Fail closed rather than guessing which active plan or incomplete source scope
  to export, but do not block valid source export because derived publications
  are absent, stale, or from another generation.
- Do not inspect or copy real records during implementation or validation.
- Do not delete historical build products or user files.
- Stop after focused/full validation, real synthetic bundle smoke, and
  independent read-only review. Do not commit, push, tag, release, or deploy.
