# IP-016 — Connector Sync Result Contract

`connector-sync-results` normalizes the latest locally recorded connector source outcome: status, freshness, timestamps, observed/changed rows, target tables, retry recommendation, and `error_present`. It never invokes a connector or exposes endpoints, credentials, raw errors, or source payloads.
