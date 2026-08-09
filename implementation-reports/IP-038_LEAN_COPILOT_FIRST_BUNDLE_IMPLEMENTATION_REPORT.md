# IP-038 lean Copilot-first bundle implementation report

## What changed and why

The builder now emits one platform-neutral lean ZIP with an exact root
allowlist, one README, generated setup helpers, a generated synthetic demo DB,
and a fully pinned Python 3.12 runtime lock. It excludes Python, venvs,
wheelhouses, artifacts, metadata caches, duplicate source directories,
secondary READMEs, and VS Code launchers. Runtime configuration now resolves
`src/.env` from the runtime root rather than caller cwd.

## Use and compatibility

Open the bundle root in VS Code, select `Delivery Manager`, and explicitly ask
to install and initialize. Setup is preflighted, retry-safe, uses the user's
configured pip index, and supports demo or local scaffold modes. Existing
Dashboard, data, schema, importers, connectors, and controlled-write contracts
are unchanged.

## Evidence and next gate

Focused bundle/config tests passed 7/7; a real lean ZIP was built; isolated
Python 3.12 online demo installation and root-cwd config/query/Dashboard smoke
passed; `make rehearse-release` passed. `make validate` passed boundary,
synthetic, and documented-use-case stages twice, but the host execution session
was reclaimed during runtime tests before a final result was emitted. No commit
or push occurred. Next gate: independent Sol read-only review and validation.

## Corrective review follow-up

The generated agent now layers a cross-platform Python 3.12 setup gate over
the maintained agent, retaining its full read-only, stdin-safe memory, and
controlled-write instructions. Manifest provenance now includes revision and
dirty identity, and local mode initializes the empty local database after
configuration scaffolding. Further setup-health validation and final complete
validation evidence remain subject to the follow-up review gate.

## Setup-helper dynamic regression follow-up

The generated setup and initialization helpers are now importable functions
with injected command-runner and filesystem seams for deterministic tests;
their CLI arguments, JSON states, error categories, and installation sequence
remain unchanged. Focused generated-bundle tests now cover marker publication
only after all smokes pass, sanitized smoke failure without a marker, verified
healthy reuse, explicit partial-install repair, local empty-database bootstrap,
and atomic demo copy with matching SHA-256 plus SQLite integrity checks.

Focused bundle, database-path, and release-engineering tests passed 21/21;
targeted Ruff and diff hygiene passed. Full `make validate` and the repeated
independent read-only review remain the acceptance gate. No commit or push
occurred.

## Third review correction

The generated agent now requires one OS-selected root virtualenv executable
(`.venv\\Scripts\\pm.exe` on Windows or `.venv/bin/pm` elsewhere) and stops
when it is absent; it does not retain a PATH executable fallback. Setup now
rechecks the actual Python version at install time, atomically replaces the
demo selector in `src/.env`, and restores an invalid/truncated selector from
the bundled example only during explicit repair. The staged-runtime path test
imports configuration from the temporary staged copy rather than the source
checkout. Focused regression now also covers JSON-only main states, version
gating, Windows path selection, failed atomic env replacement, and repair.

## Fourth review correction and next gate

Generated command guidance now uses the shell-neutral `<workspace-pm>`
placeholder, with direct POSIX and PowerShell executable forms and a
PowerShell-safe Python-subprocess stdin requirement for raw user turns. Network
classification applies only to dependency installation; configuration, tool,
and initialization failures retain their own stable categories. Malformed setup
markers and executable-runner OS errors return one sanitized JSON result without
a traceback.

Implementation validation is complete: the main-agent final `make validate`
passed 493 runtime tests, 49 repository-tool tests plus 19 subtests, and all
9 checks; `make rehearse-release` passed. The sixth review found P1/P2 issues;
the correction is applied and final independent no-finding re-review remains
pending before owner acceptance. No commit or push occurred.

## Final candidate package and review closure

The seventh independent Sol read-only review found no P0-P2 findings. Final
validation evidence is: focused regression 27/27; `make validate` passed 493
runtime tests, 49 repository-tool tests plus 19 subtests and all 9 checks; and
`make rehearse-release` passed.

The final lean ZIP is
`/Users/yanceywu/Documents/AI DM Workspace/dist/dm-usage-lean-candidate/delivery-manager-usage-lean-v0.2.0rc1.zip`
(601432 bytes; SHA-256
`4d58faa91e44573f2995302089bbb6c875c08ba18fb03c50f69e069646820a7d`).
Archive inspection confirmed one root, the exact root allowlist, one README,
no launcher/cache/metadata/venv/wheelhouse/artifacts/duplicate source folder,
required README/Copilot/setup/lock/demo files, and manifest file hashes matching
the ZIP payload. The manifest intentionally records the local dirty source
identity at `8fb8aa26c604b1405ed34045556897da1f40a168`.

Next gate: owner local test and acceptance only. No commit, push, release, or
other external action occurred.
