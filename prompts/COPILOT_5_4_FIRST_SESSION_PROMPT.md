# First Copilot 5.4 Session Prompt

Copy the text below as the first message in a new VS Code Copilot Chat opened
at this repository root.

```text
You are continuing the complete Delivery Intelligence program in the Delivery
Manager repository as a disciplined engineering agent. Do not rely on prior
chat history. Build a whole-program mental model first, but do not start
implementation yet. Phase 6 Weekly Brief v2 is the promoted local prerequisite.
Your current task is a read-only Phase 7 Forecast v1 design proposal only.

First read, in full:
1. AGENTS.md
2. PROGRESS.md
3. docs/COPILOT_5_4_PROGRAM_CONTEXT.md
4. docs/COPILOT_5_4_CONTINUATION_KIT.md
5. architecture/00_ARCHITECTURE_NORTH_STAR.md through
   architecture/05_DELIVERY_INTELLIGENCE_EVOLUTION_PLAN.md
6. architecture/06_PHASE_1_INTELLIGENCE_OUTPUT_CONTRACT_DESIGN.md through
   architecture/13_PHASE_6_WEEKLY_BRIEF_V2_DESIGN.md
7. implementation-packs/INDEX.md

Treat the Phase 0–9 roadmap as long-term context, not authorization. Treat
PROGRESS.md as the source of truth for the current gate.

Then run only read-only checks:
- git branch --show-current
- git rev-parse HEAD
- git status --short
- rg --files src/pm_agent src/tests | rg 'weekly|brief|snapshot|attention|project_health|capacity|action|decision|freshness'

Report, in Chinese and without editing files:
1. current branch, exact HEAD, and whether the worktree is clean;
2. current approved gate and the exact next action;
3. a concise Phase 0–9 map: completed/promoted, current, and planned-only
   phases, plus their key dependency relationships;
4. the actual `weekly-dm-brief`, `WeeklyReportService`, snapshot/history,
   Attention, Project Health, Resource, action, decision, and freshness call
   paths, including which are public contracts versus storage internals;
5. the verified gaps against the Phase 7 Forecast requirements (velocity
   snapshots, release forecasts, assumptions/evidence windows/confidence/error
   history, and milestone/health history reuse);
6. every action that remains unapproved;
7. a first-principles Phase 7 Forecast v1 Batch A design proposal naming the
   owning module, public inputs/output, evidence/freshness contract,
   deterministic rules, snapshot strategy, tests, rollback, non-goals, and
   separately reviewable implementation slices.

Hard boundaries:
- Do not register a Phase 7 implementation pack or edit runtime/schema/tests
  until I explicitly approve the Phase 7 design and authorize one named batch.
- Do not edit runtime/schema/tests, access a connector or real data, create an
  Attention producer, replace legacy behavior, push, merge, tag, release, or
  deploy.
- Treat missing, partial, stale, or conflicting data as explicit limitations;
  never infer zero, green, healthy, available, or safe.
- Use only stable anonymous synthetic IDs in any example.

Write the bounded Phase 7 design and update `PROGRESS.md` only after completing
the read-only inspection and gap analysis. Validate documentation, perform an
independent read-only review, commit locally, and stop for my explicit design
approval. Do not begin implementation automatically.
```

## After the first report

- If design corrections are needed, use
  `templates/COPILOT_DESIGN_TASK_TEMPLATE.md` in a new task.
- If the owner approves the Phase 7 design and authorizes Batch B, use
  `templates/COPILOT_IMPLEMENTATION_TASK_TEMPLATE.md`; fill every bracketed
  field before sending.
- Use a separate Chat with
  `templates/COPILOT_READ_ONLY_REVIEW_TEMPLATE.md` for review.
