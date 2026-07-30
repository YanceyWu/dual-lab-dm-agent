# Copilot 5.4 Continuation Kit

Use this kit to continue Delivery Intelligence work after a higher-capability
architecture session. It is a process contract, not an implementation
authorization. `AGENTS.md` and `PROGRESS.md` remain authoritative when they
conflict with this document.

## Current starting point

- Trusted current state: read `PROGRESS.md`, then verify branch, exact HEAD,
  and a clean worktree yourself.
- Current next gate: Phase 5 Resource Intelligence design review.
- Current design: `architecture/12_PHASE_5_RESOURCE_INTELLIGENCE_DESIGN.md`.
- Do not implement Phase 5 or register an implementation pack until the owner
  explicitly approves that design and authorizes one named batch.

## Non-negotiable operating sequence

1. Read `AGENTS.md`, `PROGRESS.md`, the active phase design, implementation
   pack if registered, and `implementation-packs/INDEX.md`.
2. Run `git branch --show-current`, `git rev-parse HEAD`, and `git status
   --short`. Stop if the branch, baseline, or uncommitted changes do not match
   the task handoff.
3. Restate the approved batch, non-goals, owner module, allowed dependencies,
   validation commands, and stop gate before editing.
4. Inspect the real schema, call paths, and tests named by the design. Do not
   invent file names or use a design statement as evidence of implementation.
5. Implement one bounded slice only. Never begin the next batch because tests
   pass.
6. Run focused synthetic tests, then `make validate`; run
   `make rehearse-release` whenever schema, import, migration, packaging, or
   installed behavior changes.
7. Perform a fresh, read-only review using
   `templates/COPILOT_READ_ONLY_REVIEW_TEMPLATE.md`. Correct accepted findings
   and repeat validation/review.
8. Update `PROGRESS.md`, stage explicit filenames only, commit locally, and
   stop. Push, merge, tag, release, deployment, connector, and real-data work
   each require their own explicit owner authorization.

## Scope firewall

Never infer approval for:

- a later batch, phase, public interface, Attention producer, or legacy
  replacement;
- `pending_decision_attention` activation;
- live connector access, real data, operational configuration, or active
  database migration;
- push, PR, merge, tag, release, or deployment.

Use only synthetic stable anonymous identifiers. Keep missing, stale, partial,
or conflicting evidence explicit; do not convert it to zero, green, safe, or
available. All business writes remain propose → preview → explicit confirm →
persist.

## Task templates

Copy the relevant template verbatim into a new Copilot Chat, replace only the
bracketed fields, and attach the named files if the workspace is not open:

- `templates/COPILOT_DESIGN_TASK_TEMPLATE.md`
- `templates/COPILOT_IMPLEMENTATION_TASK_TEMPLATE.md`
- `templates/COPILOT_READ_ONLY_REVIEW_TEMPLATE.md`
- `templates/COPILOT_PROMOTION_TASK_TEMPLATE.md`

Use a new chat for read-only review so the reviewer does not rely on the
implementation chat's claims. Existing prompts
`prompts/INTERNAL_IMPLEMENTATION_ENGINEER.md` and
`prompts/INTERNAL_VALIDATION_REVIEWER.md` remain useful role instructions.

## Completion report required in every implementation task

Do not say a batch is complete until validation and review are complete. Report
in exactly this order:

1. what changed and why;
2. usable functionality and how to use it;
3. effect on existing modules, data, and compatibility;
4. intentionally excluded scope and next gate;
5. tests and review evidence;
6. commit and push status.

## Model-quality safeguards

- Prefer small patches and focused tests over broad rewrites.
- Require evidence from source/schema/tests for every claim; mark unknown facts
  as `UNKNOWN`.
- Use `rg` for discovery and `apply_patch` for edits.
- Do not stage broad directories; inspect staged filenames and `git diff
  --cached --check` before committing.
- A passing narrow test does not prove a broad contract. Match the test scope to
  the approved acceptance criterion.
