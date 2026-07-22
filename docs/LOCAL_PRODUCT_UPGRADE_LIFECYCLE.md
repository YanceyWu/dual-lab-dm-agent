# Local Product Upgrade Lifecycle

## Scope

The distributable product is the versioned `src/` package, portable tests,
sanitized samples, and documentation. A Delivery Manager's database,
credentials, exports, logs, backups, and local configuration remain private and
must never be committed or bundled.

## Install

From the `src/` directory, create an isolated environment and install the
versioned package:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -e .
pm init
```

Set the local database path and any connector credentials only in local,
ignored configuration. Do not copy another user's database or `.env` file.

## Upgrade procedure

1. Read the target release notes and migration notes before changing code.
2. Confirm a clean product-core working tree and local configuration boundary.
3. Create a local recovery point before schema-affecting changes:

   ```bash
   pm backup create --label before-upgrade
   ```

4. Install the approved package version in the local environment.
5. Run `pm init` to apply the additive bootstrap/migration path.
6. Verify configuration, portable connector contracts, and local facts:

   ```bash
   pm config validate
   pm connector validate --portable
   pm tool list
   pm sync status
   ```

7. Record the installed product commit/version in the local change record; do
   not record secrets, source exports, or personal operational data.

## Recovery

If validation fails, stop operational use. Restore the database from the local
backup manifest and DB snapshot, then return product code to the tagged commit.
Do not use a Git reset to overwrite unreviewed local work. A database restore is
an explicit local operator action and must be verified before resuming writes.

## Release acceptance

A release must pass portable source/boundary/sample checks and the regression
suite. Any schema migration must be additive, tested against the prior supported
database shape, and backed by this recovery path.
