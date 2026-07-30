# First Copilot 5.4 Session Prompt

Copy the text below as the first message in a new VS Code Copilot Chat opened
at this repository root.

```text
You are continuing the Delivery Manager repository as a disciplined engineering
agent. Do not rely on prior chat history and do not start implementation yet.

First read, in full:
1. AGENTS.md
2. PROGRESS.md
3. docs/COPILOT_5_4_CONTINUATION_KIT.md
4. architecture/05_DELIVERY_INTELLIGENCE_EVOLUTION_PLAN.md
5. architecture/12_PHASE_5_RESOURCE_INTELLIGENCE_DESIGN.md
6. implementation-packs/INDEX.md

Then run only read-only checks:
- git branch --show-current
- git rev-parse HEAD
- git status --short
- rg --files src/pm_agent src/tests | rg 'staffing|capacity|allocation|hiref|workload|project_health'

Report, in Chinese and without editing files:
1. current branch, exact HEAD, and whether the worktree is clean;
2. current approved gate and the exact next action;
3. verified existing Resource Intelligence inputs and missing capabilities;
4. the Phase 5 design's owner module, allowed dependencies, fixed formula,
   required synthetic scenarios, and non-goals;
5. every action that remains unapproved;
6. a concise Phase 5 design-review verdict: PASS, PASS_WITH_ACTIONS, or FAIL.

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
