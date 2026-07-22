# IP-008 G3 Validation Report

Status: `G3 TECHNICALLY VALIDATED — COMMITTED AND PUSHED — OWNER SIGN-OFF PENDING`
Date: 2026-07-22 (implementation completed 2026-07-19)

## G3 checklist

| Criterion | Evidence |
| --- | --- |
| Query/assessment performs no staffing write | `pm staffing assess` and feasibility scenarios are read-only. |
| Every staffing write has a confirmed proposal | Planned assignments/monthly allocations are only created in proposal confirmation. |
| No partial assignment without a decision record | One SQLite transaction writes assignments, allocations, decision log, and proposal status. |
| Repeated confirmation is idempotent | Synthetic idempotency scenario passes. |
| Cancellation/rejection leaves domain state unchanged | Synthetic cancel/reject scenarios pass. |
| Legacy behavior remains available | Existing allocation, contract, CLI, Dashboard, and full runtime regression tests pass. |
| Broad synthetic scenarios | 23 staffing scenarios cover time, effort, skills, contract, capacity, split demand, source states, expiry, and changed facts. |

## Manager workflow

```bash
pm staffing assess --project <id> --start 2026-08 --end 2026-08 --effort 0.6 --skills python --maximum-people 2
pm staffing propose --project <id> --start 2026-08 --end 2026-08 --effort 0.6 --skills python --maximum-people 2
pm staffing preview <proposal-id>
pm staffing confirm <proposal-id> --token <confirmation-token>
```

`cancel` and `reject` are available only while a proposal is unconfirmed. The
commands emit structured JSON and are intended for an explicit local manager
action; they are not a write-capable Copilot transport.

## Validation

- Staffing golden scenario file: `23 passed`.
- Full runtime suite: `77 passed`.
- Repository tool suite: `18 passed, 19 subtests passed`.
- Static compilation, portable-only audit, repository-boundary check,
  synthetic-sample check, and diff check: passed.

## Remaining operational responsibility

The implementation was committed and pushed in `3873edb` after the original
validation. A human owner must still approve the manager-facing confirmation
workflow before treating G3 as operationally promoted. A confirmed planned
allocation remains a meaningful local domain change and requires an explicit
manager reversal if it must be undone.
