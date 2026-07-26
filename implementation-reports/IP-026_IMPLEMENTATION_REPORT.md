# IP-026 Implementation Report

Status: `COMMITTED LOCALLY — PUSH BLOCKED BY GITHUB WORKFLOW SCOPE`
Date: 2026-07-26
Candidate package version: `0.2.0rc1`
Candidate tag: `v0.2.0-rc.1` (`NOT CREATED`)

## Implemented

- Added root-aware `make validate` and `make rehearse-release` entry points.
- Added one validation program covering boundary, synthetic-data, runtime and
  repository-tool tests, full portable Ruff, compilation, diff hygiene, and
  temporary wheel/sdist build inspection.
- Added a synthetic release rehearsal that installs the built wheel, migrates
  an isolated legacy-database copy, verifies integrity and core counts, and
  proves rollback by hash.
- Added read-only GitHub Actions validation for Python 3.10 and 3.12.
- Bumped the package/runtime version from `0.1.0` to `0.2.0rc1` and added
  `pm version`.
- Cleared all 25 full-scope Ruff findings using behavior-preserving import and
  statement-layout changes.
- Documented the candidate, tag, CI, backup, real-UAT, promotion, and rollback
  workflow.

## Local evidence

- Unified validation: passed.
- Runtime tests: 115 passed.
- Repository-tool tests: 20 passed, 19 subtests passed.
- Full portable Ruff scope: passed with zero findings.
- Repository boundary, synthetic samples, compilation, and diff check: passed.
- Built and inspected `ai_pm_agent-0.2.0rc1` wheel and sdist in a temporary
  directory.
- Wheel install, synthetic isolated-database upgrade, integrity/foreign-key
  checks, dependent views, aggregate-count preservation, and rollback hash:
  passed.

The locally validated source content is committed on the independent candidate
branch. GitHub rejected the HTTPS push because the active OAuth credential does
not have permission to create or update workflow files. Re-authentication with
workflow scope is required before GitHub Actions can validate the commit.

## Remaining gates

1. Re-authenticate GitHub access with repository and workflow scope, then push.
2. Green GitHub Actions for the exact pushed commit.
3. Explicit owner authorization to create/push `v0.2.0-rc.1`.
4. Work-computer backup, isolated operational-database rehearsal, and
   IP-022-to-IP-026 real-environment UAT.

No tag, package publication, deployment, connector call, active-database
migration, or merge into `main` was performed.
