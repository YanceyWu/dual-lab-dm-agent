# IP-019 — Interface-to-Executor Migration

Migrate Dashboard `/api/project-snapshots` from direct SQL to shared
`project-snapshot-list`. The route preserves its legacy JSON array, while the
use case provides the evidence-bearing read-only contract. Rollback restores
only the route adapter; storage and write paths remain unchanged.
