---
description: Answer a Delivery Manager workload or availability question using the local structured tool.
agent: agent
---

Answer the user's workload or availability question. Interpret the question,
then run `pm tool describe team-workload-overview` if parameter meaning is
unclear and run `pm tool query team-workload-overview` with an exact team filter
only when one is explicitly supplied. Use the JSON result and its `context` as
the sole source of facts. State that the capacity period is current, present
current availability and overload flags, then cite evidence, freshness,
assumptions, warnings, and the execution ID. If freshness is not fresh, explain
the limitation and recommend verification before a commitment. Do not inspect
the database, raw files, or formatted `pm workload` output.
