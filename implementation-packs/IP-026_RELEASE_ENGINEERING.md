# IP-026 — Release Engineering

## Business goal

Turn the independently maintained candidate branch into an identifiable,
installable, verifiable, upgradeable, and recoverable product candidate without
merging it into `main`.

## Scope

- Use package version `0.2.0rc1` and candidate tag form `v0.2.0-rc.1`.
- Provide `pm version` for installed-version identification.
- Provide one repository-root-independent `make validate` entry point.
- Validate repository boundary, synthetic samples, runtime tests, repository
  tool tests, full portable Ruff scope, compilation, diff hygiene, wheel/sdist
  build, package metadata, and packaged Dashboard assets.
- Add read-only GitHub Actions validation on supported Python versions.
- Rehearse wheel installation, isolated legacy-database upgrade, integrity
  checks, and database rollback using only synthetic data.
- Define the commit, CI, tag, backup, UAT, promotion, and rollback sequence.

## Safety constraints

- CI and local validation must not read operational configuration, credentials,
  exports, databases, or connector responses.
- Build and rehearsal artifacts exist only in temporary directories.
- CI must not publish packages, create tags, deploy, or invoke connectors.
- A release-candidate tag may point only to a clean, pushed commit whose CI
  validation passed.
- Real-environment UAT requires a local backup and isolated database-copy
  rehearsal before active-database migration.
- Release engineering does not merge or rebase this independent branch into
  `main`.

## Acceptance scenarios

1. `make validate` succeeds from the repository root and resolves the same root
   when invoked with `make -f ../Makefile validate` from `src/`.
2. The validation output identifies the current commit and whether working-tree
   changes are included.
3. Full portable Ruff scope has zero findings.
4. The built wheel and sdist both report `0.2.0rc1`; the wheel contains the
   Dashboard web entry point.
5. `pm version` reports `ai-pm-agent 0.2.0rc1`.
6. `make rehearse-release` installs the wheel into an isolated target, upgrades
   a copy of the synthetic legacy database, preserves core aggregate counts,
   passes integrity and foreign-key checks, preserves dependent views, and
   restores a rollback copy with the original hash.
7. GitHub Actions runs the same validation and rehearsal on Python 3.10 and
   3.12 with read-only repository permission.
8. No tag is created while the implementation is uncommitted, CI is unknown,
   or owner authorization is absent.

## Rollback

- Before tagging: revert the bounded IP-026 commit through a reviewed inverse
  commit; do not reset unrelated work.
- After tagging but before operational promotion: stop use of the candidate,
  keep the tag as historical evidence, and issue a new release candidate after
  correction.
- During real UAT: restore the operator-created database snapshot and reinstall
  the previously approved package commit/tag.
