---
description: Answer a Delivery Manager workload or availability question using the local structured tool.
agent: agent
---

Answer the user's workload or availability question. Interpret the question,
then run `pm tool describe team-workload-overview` if parameter meaning is
unclear and run `pm tool query team-workload-overview` with an exact team filter
only when one is explicitly supplied. Use the JSON result as the sole source of
facts. Present current availability, overload flags, evidence, and uncertainty.
Do not inspect the database, raw files, or formatted `pm workload` output.
