# Delivery Manager Roadmap

Status: `0.2.0rc1 PORTABLE CANDIDATE — REAL-ENVIRONMENT UAT PENDING`
Last updated: 2026-07-26

This roadmap begins from the current release candidate. Earlier IP migration
sequences are historical evidence, not work still waiting to start.

## Stage 1 — Candidate context cleanup

Goal: ensure the work-computer model sees only current operating, validation,
and safety instructions.

Exit criteria:

- obsolete baseline, migration, and release-readiness files are removed;
- `README.md`, `PROGRESS.md`, portability status, and Agent instructions agree;
- historical implementation material has an explicit owner disposition;
- reference checks, `make validate`, and `make rehearse-release` pass;
- cleanup is reviewed and pushed to the independent branch.

## Stage 2 — Immutable candidate

Goal: make the exact validated source reproducible.

Exit criteria:

- GitHub Actions is green for the exact cleanup commit;
- the working tree is clean;
- the owner explicitly authorizes annotated tag `v0.2.0-rc.1`;
- the immutable tag is pushed without moving or recreating it.

The tag is a test candidate, not production approval and not authorization to
merge into `main`.

## Stage 3 — Work-computer migration rehearsal

Goal: prove that the candidate can upgrade the real schema safely without first
touching the active database.

Follow `docs/REAL_ENVIRONMENT_UAT_RUNBOOK.md`.

Exit criteria:

- a local backup exists;
- migration runs only on an isolated database copy;
- integrity and foreign-key checks pass;
- dependent views remain queryable;
- confirmation tokens use only the hash column;
- pre/post aggregate counts are unchanged;
- no raw data or evidence leaves the approved environment.

## Stage 4 — Controlled real-environment UAT

Goal: validate the actual operating workflow using approved local data and
configuration.

Validate in this order:

1. configuration and portable connector contracts;
2. structured read-only use cases and failure behavior;
3. one approved connector probe/sync at a time;
4. staffing assess/propose/preview/cancel;
5. staffing confirmation only with authorized manager approval;
6. Dashboard read paths, write preview/confirm/replay protection, and loopback
   binding.

Any credential exposure, raw error, unexpected scope, integrity failure,
changed aggregate, non-fresh decision input, or confirmation mismatch is a stop
condition.

## Stage 5 — Candidate decision

After sanitized UAT evidence:

- promote the candidate for local operational use when all gates pass; or
- record a sanitized defect category, restore the previous local version and
  database backup, and create a new `rcN` candidate.

Do not move an existing tag, publish automatically, or merge into `main`.

## Post-0.2 iteration themes

Do not register new implementation packs until real UAT and user feedback show
which problem is material. Candidate themes are:

- data-quality diagnostics that identify missing/stale inputs without exposing
  records;
- connector reliability, retry visibility, and operator recovery;
- shorter natural-language paths for recurring DM decisions;
- clearer comparison of staffing alternatives and HIREF actions;
- operational observability using safe aggregate metadata;
- reducing remaining legacy CLI/Dashboard compatibility paths.

Prioritize by decision value, user friction, failure risk, and evidence from
real use—not by architectural novelty.
