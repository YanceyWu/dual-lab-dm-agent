# Technical Reconstruction — Screenshot-Optimized Prompt

Use this prompt only inside the company environment. The output remains subject
to company policy; screenshot formatting is not permission to transfer it.

```text
You are generating a sanitized technical reconstruction package for an external
architecture review. Inspect the actual repository, database schema, migrations,
data-access code, and representative execution flows. Do not modify code.

Do not output source code, SQL, actual records, credentials, internal URLs, real
table/file/class names, people, projects, customers, applications, or proprietary
business values. Use stable anonymous IDs consistently:

- tables T01, T02...
- components M01, M02...
- use cases UC01, UC02...
- connectors CN01, CN02...
- risks R01, R02...
- constraints MC01, MC02...

Preserve field semantics, generic data types, keys, relationships, dependencies,
read/write behavior, decision flow, lineage, and legacy constraints. Describe the
actual system. Use UNKNOWN instead of guessing. Do not recommend a redesign.

SCREEN FORMAT

1. Output one SCREEN at a time.
2. Begin with "===== SCREEN XX =====" and a short Title.
3. End with "===== END SCREEN XX =====".
4. Keep each screen between 120 and 220 words and at most 14 short lines.
5. Use compact bullets or field-value lines; never use wide tables.
6. Use one major topic per screen.
7. Use one core table per screen or at most two minor tables.
8. Put relationship maps, read/write matrices, and Staffing Trace on separate screens.
9. End every screen at a complete bullet or sentence.

OUTPUT ORDER

A01 System Overview
- language and application style
- database technology and access approach
- ORM/query and migration mechanism
- runtime entry points and approximate component count

A02 Data Architecture Overview
- raw, normalized, snapshot/history, and execution-metadata strategies
- legacy compatibility and local/external data ownership

B01 Repository Module Map
- compact anonymous tree using MXX IDs

B02 onward: one important component per screen
- role, called by, calls
- database access, external access, business rules, prompt logic
- approximate size and short notes

C01 onward: Table Catalog
- TXX and generic name
- purpose, category, importance
- every meaningful column: anonymous ID, meaning, type, nullable, PK/FK/unique
- relationships, read by, written by, update pattern, lineage, known issue

D01 Core Entity Relationship Map
D02 Weak or application-enforced relationships
D03 Source-of-Truth Map

E01 onward: Read/Write Matrix, at most four use cases per screen
- purpose, reads, writes, access method, transaction behavior
- external dependency and destructive behavior
- include staffing, workload, capacity, weekly summary, action, decision,
  snapshot, project list, freshness, imports, release sync, health, source
  comparison, baseline import, and contract reporting

F01 onward: Domain Representation, three or four concepts per screen
- Person, Skill, Contract, Project, Demand, Assignment, Capacity, Milestone,
  Release, WorkItem, Risk, Dependency, Action, Decision, Snapshot, SourceRecord
- status: EXPLICIT, PARTIAL, IMPLICIT, MULTIPLE_INCOMPATIBLE, or MISSING
- primary tables, source of truth, derived fields, semantic gap

G01 Staffing Trace — User Input
G02 Staffing Trace — Data Reads in actual order
G03 Staffing Trace — Eligibility Filters
G04 Staffing Trace — Scoring and tie-breaking
G05 Staffing Trace — Output, evidence, warnings, writes, confirmation
G06 Staffing Trace — Language-neutral pseudocode, first half
G07 Staffing Trace — Language-neutral pseudocode, second half
G08 Staffing Trace — Coupling, reuse, tests, and extension difficulty

H01 CLI Execution Path
H02 HTTP Execution Path
H03 Prompt/Agent Execution Path
H04 Staffing Call Graph
H05 Project Health Call Graph
H06 Weekly Summary Call Graph

I01 onward: Coupling and Duplication, at most five facts per screen
- entry-point duplication, direct database or connector access
- prompt/code rule overlap, repeated context assembly and retrieval
- capability bypasses and legacy leakage

J01 onward: Schema Risks, at most four per screen
- RXX, area, severity, observed fact, affected tables/use cases, impact
- separate screens for MCXX migration constraints and dependent behavior

K01 Confidence Assessment by section
K02 Unknown Areas and assumptions requiring manual confirmation

FINAL CHECK

Verify unique screen IDs, titles, limits, anonymous identifiers, complete lines,
separate maps and traces, and absence of code, SQL, confidential names, actual
data, recommendations, or guesses. Start with A01. Generate only the next eight
screens when response length is limited. Never repeat completed screens.
```
