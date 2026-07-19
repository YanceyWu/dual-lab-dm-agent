# Delivery Manager operating mode

For Delivery Manager questions in this repository, do not inspect SQLite,
connector configuration, raw exports, or formatted CLI output directly.

Use the structured local tool commands instead:

```bash
pm tool list
pm tool describe team-workload-overview
pm tool query team-workload-overview [--team "Exact Team Name"]
```

For a natural-language availability or workload question, first identify whether
`team-workload-overview` applies, then run its structured query. Explain only
the returned data and evidence. State uncertainty whenever the result status is
`unavailable`, `partial`, or `invalid`; do not invent people, capacity, or
assignments. This command is read-only and must not be used to make writes.
