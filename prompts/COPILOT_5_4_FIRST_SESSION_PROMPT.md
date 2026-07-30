# First Copilot 5.4 Session Prompt

Copy the text below as the first message in a new VS Code Copilot Chat opened
at this repository root.

```text
You are continuing the complete Delivery Intelligence program in the Delivery
Manager repository as a disciplined engineering agent. Do not rely on prior
chat history. Build a whole-program mental model first, but do not start
implementation yet.

First read, in full:
1. AGENTS.md
2. PROGRESS.md
3. docs/COPILOT_5_4_PROGRAM_CONTEXT.md
4. docs/COPILOT_5_4_CONTINUATION_KIT.md
5. architecture/00_ARCHITECTURE_NORTH_STAR.md through
   architecture/05_DELIVERY_INTELLIGENCE_EVOLUTION_PLAN.md
6. architecture/06_PHASE_1_INTELLIGENCE_OUTPUT_CONTRACT_DESIGN.md through
   architecture/12_PHASE_5_RESOURCE_INTELLIGENCE_DESIGN.md
7. implementation-packs/INDEX.md

Treat the Phase 0–9 roadmap as long-term context, not authorization. Treat
PROGRESS.md as the source of truth for the current gate.

Then run only read-only checks:
- git branch --show-current
- git rev-parse HEAD
- git status --short
- rg --files src/pm_agent src/tests | rg 'staffing|capacity|allocation|hiref|workload|project_health'

Report, in Chinese and without editing files:
1. current branch, exact HEAD, and whether the worktree is clean;
2. current approved gate and the exact next action;
3. a concise Phase 0–9 map: completed/promoted, current, and planned-only
   phases, plus their key dependency relationships;
4. verified existing Resource Intelligence inputs and missing capabilities;
5. the Phase 5 design's owner module, allowed dependencies, fixed formula,
   required synthetic scenarios, and non-goals;
6. every action that remains unapproved;
7. a concise Phase 5 design-review verdict: PASS, PASS_WITH_ACTIONS, or FAIL.

Hard boundaries:
- Do not implement Phase 5 Batch B or register an implementation pack unless I
  explicitly approve the Phase 5 design and authorize Batch B.
- Do not edit runtime/schema/tests, access a connector or real data, create an
  Attention producer, replace legacy behavior, push, merge, tag, release, or
  deploy.
- Treat missing, partial, stale, or conflicting data as explicit limitations;
  never infer zero, green, healthy, available, or safe.
- Use only stable anonymous synthetic IDs in any example.

After I review your report, wait for my explicit next instruction.
```

## After the first report

- If design corrections are needed, use
  `templates/COPILOT_DESIGN_TASK_TEMPLATE.md` in a new task.
- If the owner approves the design and authorizes Batch B, use
  `templates/COPILOT_IMPLEMENTATION_TASK_TEMPLATE.md`; fill every bracketed
  field before sending.
- Use a separate Chat with
  `templates/COPILOT_READ_ONLY_REVIEW_TEMPLATE.md` for review.
