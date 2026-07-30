# Copilot read-only review task

Review `[PHASE] [BATCH]` at `[BRANCH / HEAD]`. Do not edit files, run writes,
push, or advance any gate.

Read `AGENTS.md`, `PROGRESS.md`, `[DESIGN]`, `[PACK]`, relevant schema/call
paths/tests, and the complete diff from `[BASELINE]`. Verify all claimed test
commands independently where practical.

Return findings by severity with exact evidence. Check: approved scope;
dependency direction/module ownership; clean re-import; preview-confirm writes;
missing/stale/partial/conflicting behavior; synthetic-data boundary; legacy and
`UseCaseResult 1.0` compatibility; no unapproved Attention/connector/public
interface; test adequacy; rollback; documentation/Git accuracy.

Conclude `PASS`, `PASS_WITH_ACTIONS`, or `FAIL`. Do not claim owner acceptance;
only the owner may accept a review or authorize the next gate.
