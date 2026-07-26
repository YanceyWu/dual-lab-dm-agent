# Release Engineering

## Candidate identity

The current package candidate is:

- Python package version: `0.2.0rc1`
- CLI identity: `pm version`
- Git tag form: `v0.2.0-rc.1`
- Candidate branch: `codex/ip-000-baseline-safety`

Package versions use PEP 440 form while Git tags use a readable SemVer-style
release-candidate suffix. Increment `rcN` for candidate-only corrections,
`0.2.x` for backward-compatible fixes after release, and the minor version for
new compatible capability batches.

## Unified local validation

From the repository root:

```bash
make validate
make rehearse-release
```

From `src/`, the equivalent commands are:

```bash
make -f ../Makefile validate
make -f ../Makefile rehearse-release
```

`make validate` prints the Git commit plus whether uncommitted changes are part
of the tested source. It performs repository-boundary and synthetic-data checks,
runtime and tool tests, full portable Ruff, compilation, diff hygiene, and a
temporary wheel/sdist build with package metadata and Dashboard asset checks.

`make rehearse-release` builds and installs the wheel into a temporary isolated
target, upgrades a temporary copy of the synthetic legacy database, checks
integrity, foreign keys, views, token schema, and aggregate counts, and proves
the rollback copy matches the original hash. It never uses an active database.

## Candidate workflow

1. Confirm only intended portable files are changed.
2. Run `make validate` and `make rehearse-release`.
3. Commit the complete candidate scope and push the independent branch.
4. Wait for GitHub Actions to pass for the exact pushed commit.
5. Confirm `git status --short` is empty and record:

   ```bash
   git rev-parse HEAD
   git show -s --format=%cI HEAD
   ```

6. With explicit owner authorization, create and push the annotated candidate
   tag:

   ```bash
   git tag -a v0.2.0-rc.1 -m "ai-pm-agent 0.2.0rc1 release candidate"
   git push origin v0.2.0-rc.1
   ```

7. On the work computer, create `pm backup create --label
   before-v0.2.0-rc.1`, repeat the isolated database-copy rehearsal from the
   real-environment UAT runbook, then install and test the exact tagged
   candidate.
8. Record only sanitized pass/fail evidence and the exact commit/tag. Do not
   copy operational records, logs, screenshots, endpoints, or configuration
   back to this repository.

The tag identifies a test candidate; it is not a production promotion and does
not authorize a merge into `main`.

## CI boundary

GitHub Actions uses read-only repository permission and runs validation on
Python 3.10 and 3.12. CI does not connect to operational systems, create a tag,
publish a package, or deploy. A green CI run proves only portable candidate
validation for that commit; real-environment UAT remains a separate gate.

## Operational rollback

If real-environment UAT fails:

1. Stop write-capable workflows and connector syncs.
2. Record only the candidate commit/tag and a sanitized failure category.
3. Restore the local database snapshot created immediately before the upgrade.
4. Reinstall the previously approved package commit/tag.
5. Run configuration validation, `pm tool list`, and read-only smoke checks
   before resuming writes.
6. Correct the issue in a new release candidate; do not move an existing tag.
