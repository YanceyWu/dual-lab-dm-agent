# Delivery Manager workspace instructions

Use the workspace `Delivery Manager` custom agent for normal DM operations. Use
the standard coding agent only for source, test, architecture, configuration, or
repository changes.

For DM operations:

- use only the structured commands and routing defined in
  `.github/agents/delivery-manager.agent.md`;
- treat returned JSON, evidence, freshness, warnings, and execution metadata as
  the sole factual basis;
- never inspect SQLite, credentials, connector configuration, raw exports,
  connector payloads, or human-formatted legacy output;
- never infer missing facts as zero, healthy, available, valid, or safe;
- run live connector probes or syncs only after an explicit request;
- keep staffing writes within propose, preview, explicit confirmation, persist.

For repository changes:

- follow the root `AGENTS.md` and read `PROGRESS.md` first;
- treat `README.md`, `PROGRESS.md`, `docs/REAL_ENVIRONMENT_UAT_RUNBOOK.md`, and
  `docs/RELEASE_ENGINEERING.md` as current operational context;
- treat implementation packs and reports as historical unless `PROGRESS.md`
  explicitly identifies one as the active pack;
- preserve the company/personal information boundary and use synthetic data
  only;
- validate portable candidate changes with `make validate` and
  `make rehearse-release`.
