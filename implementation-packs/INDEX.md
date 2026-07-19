# Implementation Pack Queue

## Purpose

This index converts the roadmap into small, ordered units that a repository-aware
implementation model can execute without making the major architecture decisions
itself.

`IP-000` through `IP-008` have complete implementation-pack documents. IP-005
through IP-008 form a locally validated staffing workflow; human-owner review
and an intentional commit remain required before G3 promotion.

## Queue

| Pack | Title | Depends on | Primary gate | Status |
| --- | --- | --- | --- | --- |
| IP-000 | Baseline, Private-State Boundary, and Regression Safety | None | G0 | READY FOR LOCAL ASSESSMENT |
| IP-001 | Unified Use Case Execution Contract | IP-000 | G1 | LOCALLY VALIDATED — OWNER REVIEW REQUIRED |
| IP-002 | Structured Copilot Tool Transport | IP-001 | G2 | IMPLEMENTED LOCALLY — G2 REVIEW REQUIRED |
| IP-003 | Evidence, Freshness, and Execution Trace Envelope | IP-001 | G2 | IMPLEMENTED LOCALLY — G2 REVIEW REQUIRED |
| IP-004 | Team Capacity Context and Copilot Playbook | IP-002, IP-003 | G2 | IMPLEMENTED LOCALLY — OWNER REVIEW REQUIRED |
| IP-005 | Canonical Staffing Read Model | G2 | G3 | IMPLEMENTED LOCALLY — G3 REVIEW REQUIRED |
| IP-006 | Demand and Staffing Feasibility Rules | IP-005 | G3 | IMPLEMENTED LOCALLY — G3 REVIEW REQUIRED |
| IP-007 | Staffing Proposal and Atomic Confirmation | IP-006 | G3 | IMPLEMENTED LOCALLY — G3 REVIEW REQUIRED |
| IP-008 | Staffing Golden Scenarios and Manager Confirmation Playbook | IP-006, IP-007 | G3 | VALIDATED LOCALLY — OWNER REVIEW REQUIRED |
| IP-009 | Project Health Context and Use Case | G3 | G4 | QUEUED |
| IP-010 | Management Attention Use Case | IP-009 | G4 | QUEUED |
| IP-011 | Weekly DM Brief Use Case | IP-009, IP-010 | G4 | QUEUED |
| IP-012 | Contract Continuity Use Case | G3 | G4 | QUEUED |
| IP-013 | Action Follow-up Use Case | G2 | G4 | QUEUED |
| IP-014 | Connector Contract Reference Migration | G4 | Connector hardening | QUEUED |
| IP-015 | Local Product Packaging and Upgrade Lifecycle | G4 | G5 | QUEUED |

## Pack sizing rule

A pack should normally change one architectural boundary or migrate one vertical
slice. Split the pack when it would:

- migrate more than one business use case;
- migrate more than one connector;
- introduce a shared framework and change business behavior together;
- require multiple independent schema migrations;
- mix write-path changes with unrelated presentation work;
- require more than one rollback strategy.

## Promotion rule

A queued pack becomes ready only after:

1. its dependencies have passed independent validation;
2. the current repository state has been assessed without edits;
3. conflicts and unknowns have been reviewed by the human owner;
4. acceptance scenarios and rollback are concrete;
5. no real data is required outside the local environment.

## Recommended immediate sequence

1. Assess, implement, and independently validate IP-000.
2. Re-assess the existing IP-001 against the current source baseline.
3. Implement and validate IP-001 using exactly one read-only reference use case.
4. Independently review and commit IP-004 before assessing IP-005.
5. Do not start the Staffing write path until IP-005 has defined canonical,
   period-aware read facts and its gate has passed.
