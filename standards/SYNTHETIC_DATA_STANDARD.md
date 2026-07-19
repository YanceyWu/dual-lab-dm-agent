# Synthetic Data Standard

Version: 1.0
Marker: `SYNTHETIC_DATASET_V1`

## Purpose

All repository examples, tests, screenshots, demo databases, and expected output
must be demonstrably fictional. Renaming a real record is not sufficient.

## Canonical fictional organization

### People

| Synthetic ID | Display name | Purpose |
| --- | --- | --- |
| 990001 | Alex Example | Delivery lead |
| 990002 | Blair Example | Backend engineer |
| 990003 | Casey Example | Full-stack engineer |
| 990004 | Drew Example | Project manager |
| 990099 | Inactive Example | Inactive-row behavior |

### Projects

| Project | Key | Synthetic numeric code | Purpose |
| --- | --- | --- | --- |
| Project Atlas | ATL | 9901001 | Delivery/stabilization scenario |
| Project Beacon | BCN | 9901002 | Build/feature scenario |
| Project Cedar | CDR | 9901003 | Recovery/capacity scenario |
| Project Delta Archive | DLT | 9901999 | Inactive-row behavior |

### Other identifiers

- Placeholder: `HIREF-SYN-001`
- Contracts: `CONTRACT-SYN-001`, `CONTRACT-SYN-002`
- Change records: `CHG-SYN-001` and subsequent values
- External hosts: subdomains of `example.invalid` only
- Email addresses: `example.invalid` only

## Construction rules

1. Every sample file contains the marker `SYNTHETIC_DATASET_V1`.
2. Six- or seven-digit employee/project-style identifiers use the reserved `99`
   prefix.
3. Person display names end in `Example`.
4. Project names come from the canonical fictional organization above.
5. Dates, allocations, skills, risks, and statuses are invented to exercise a
   test behavior; they are never shifted or paraphrased from a live record.
6. URLs use the reserved `.invalid` domain.
7. Sample files do not contain company names, internal hosts, real employee IDs,
   customer terms, or copied operational descriptions.
8. Generated demo databases inherit this classification only when built solely
   from approved sample files.

## Approval evidence

A sample-data release requires:

- automated marker/identifier/domain validation;
- successful clean demo rebuild;
- deterministic row-count and semantic smoke checks;
- manual owner confirmation that values were constructed, not anonymized;
- an approval entry in `docs/SOURCE_PORTABILITY_REVIEW.md`.

Synthetic data may resemble common delivery-management situations. It must not
preserve the unique combination of people, dates, allocations, descriptions, or
identifiers from a real organization.
