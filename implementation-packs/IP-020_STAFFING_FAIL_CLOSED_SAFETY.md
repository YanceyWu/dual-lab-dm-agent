# IP-020 — Staffing Fail-Closed Safety

## Goal

Prevent staffing proposals and confirmations from silently relying on invalid or
non-fresh decision facts, while preserving an explicit, auditable Delivery
Manager exception for genuinely ambiguous operating situations.

## Business decisions

- A recorded member role and requested demand role are reference context only.
  They do not exclude or rank candidates because cross-functional skills may be
  more relevant than a job-profile label.
- Non-fresh staffing sources block proposal creation by default.
- A Delivery Manager may create a proposal from non-fresh facts only by
  explicitly allowing it and recording a non-empty reason.
- HIREF represents an SFTE/STFTE charge-code authorization for one project and
  date range. It is planning context and a source of follow-up actions, not an
  intrinsic qualification of the person.
- The owner confirmed that the presence of an HIREF number means its charge code
  is usable for the recorded project and `start_date`–`end_date`; no separate
  pending/approved state is inferred.
- A missing, mismatched, expired, or partially covering HIREF does not remove a
  person from the candidate set. Covered HIREF options rank first; a selected
  option with a gap requires an explicit manager action note.
- Invalid plan versions cannot be overridden because the allocation write target
  does not exist.
- Copilot may explain an override but may not autonomously authorize or confirm
  one.

## Implemented scope

- Staffing assessment exposes `decision_ready`, structured `safety_blockers`,
  source run identity/timestamps, role reference context, and a deterministic
  decision fingerprint.
- Candidate context exposes per-month load/capacity, recorded role, skills, and
  HIREF coverage; target project context exposes its recorded technology stack.
  Role and project technology labels remain references rather than inferred hard
  compatibility rules.
- Proposal creation requires fresh resource and skill sources unless the local
  manager supplies both `--allow-non-fresh` and
  `--freshness-override-reason`.
- The override reason and acknowledged source states are retained in proposal
  evidence and the final decision log.
- Confirmation recomputes the full decision fingerprint. Changes to capacity,
  candidates, selections, plan, source state/run, role context, or rule version
  invalidate the proposal.
- Current and next/extend HIREF records are combined to evaluate continuous
  target-project coverage for the requested months.
- Selected options with missing, mismatched, or partial HIREF coverage require
  both `--acknowledge-hiref-actions` and `--hiref-action-note`. The note records
  whether the DM intends to submit/extend HIREF or change the staffing choice.
- A missing, unknown, or inconsistent plan version blocks proposal creation.
- Proposals created before this fingerprint contract must be recreated before
  confirmation.

## Acceptance scenarios

1. Assessment may explain a mathematically feasible result while
   `decision_ready=false` when sources are not fresh.
2. A non-fresh proposal without an explicit reason is blocked and writes no
   proposal or domain record.
3. A manager-authorized non-fresh proposal can be confirmed only while its
   fingerprint remains unchanged, and the exception is auditable.
4. A source run/state change after proposal creation invalidates confirmation.
5. An SFTE/STFTE member without covering HIREF remains visible, ranks after
   covered options, and requires a manager action note if selected.
6. A requested role is visible next to each recorded member role but never
   changes eligibility or ranking.
7. An unknown plan version cannot create a proposal.
8. Adjacent current and next/extend HIREF records for the target project count
   as continuous coverage; gaps and project mismatch remain explicit.

## Rollback

Revert the service, CLI, repository decision-audit extension, and these tests.
No schema migration is introduced. Existing IP-020 proposals should be cancelled
before rollback because older code does not understand their stronger
fingerprint and override evidence.
