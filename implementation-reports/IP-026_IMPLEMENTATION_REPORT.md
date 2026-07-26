# IP-026 Implementation Report

Status: `VALIDATION GREEN — TAG AND REAL UAT PENDING`
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

Candidate commit `9123288` is pushed on the independent branch. GitHub Actions
run `30186840298` passed both test suites, then failed lint in both Python jobs:
CI resolved Ruff `0.16.0`, while local validation used Ruff `0.15.22`. The
unversioned CI dependency therefore applied a different default lint contract
and produced 179 findings.

The approved repair pins build `1.5.0`, poetry-core `2.4.1`, pytest `9.1.1`,
and Ruff `0.15.22` in one validation requirements file. CI installs that
contract, the validator fails on a version mismatch, and Ruff rule families are
explicit in `pyproject.toml`. Local revalidation passed with 115 runtime tests,
21 repository-tool tests (19 subtests), package build/install, isolated
database upgrade, and rollback.

The repair was committed and pushed as `982d027`. GitHub Actions run
`30186978361` passed the complete validation and release rehearsal on Python
3.10 and 3.12.

## Remaining gates

1. Explicit owner authorization to create/push `v0.2.0-rc.1`.
2. Work-computer backup, isolated operational-database rehearsal, and
   IP-022-to-IP-026 real-environment UAT.

No tag, package publication, deployment, connector call, active-database
migration, or merge into `main` was performed.
