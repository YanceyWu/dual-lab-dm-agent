You are generating a sanitized technical reconstruction package for an external architecture review.

The output will NOT be copied as text.

The output will be read and transferred by mobile screenshots.

Therefore, readability and screenshot layout are mandatory.

Your task is to inspect the actual repository, database schema, migrations, ORM models, queries, and staffing-related execution flow, then generate a sanitized DATABASE AND CODE RECONSTRUCTION PACK.

Do not modify code.

Do not output source code.

Do not output real internal names, real table names, real file names, internal URLs, credentials, project names, employee names, application names, customer data, or actual records.

Use stable anonymous identifiers consistently:

- Tables: T01, T02, T03...
- Components: M01, M02, M03...
- Use cases: UC01, UC02...
- Connectors: CN01, CN02...
- Risks: R01, R02...
- Constraints: MC01, MC02...

Preserve technical meaning, relationships, logic, data types, keys, dependencies, and runtime behavior.

==================================================
MANDATORY SCREENSHOT FORMAT
==================================================

The response must be optimized for mobile screenshots.

Follow all rules below.

1. Output one SCREEN at a time.

2. Every screen must begin with:

===== SCREEN XX =====
Title: [short title]

3. Every screen must end with:

===== END SCREEN XX =====

4. Keep each screen between 120 and 220 words.

5. Never exceed 14 short lines per screen.

6. Use short sentences.

7. Avoid paragraphs longer than 3 lines.

8. Use bullets or compact field-value format.

9. Do not use wide Markdown tables.

10. Do not place more than:
- one major topic per screen
- one table definition per screen for core tables
- two table definitions per screen for minor tables

11. Use large, visible headings.

12. Use consistent numbering.

13. Do not repeat background explanations.

14. Do not include recommendations.

15. If content is too long, continue on the next numbered screen.

16. Relationship maps must be placed on separate screens.

17. Staffing Trace must be placed on separate screens.

18. Read/Write Matrix must be split across multiple screens.

19. Schema risks must be split across multiple screens.

20. End every screen at a complete sentence or complete bullet.

==================================================
OUTPUT ORDER
==================================================

Generate the screens in this exact order.

--------------------------------------------------
SECTION A — SYSTEM AND DATABASE OVERVIEW
--------------------------------------------------

SCREEN A01
Title: System Overview

Include:
- programming language
- application style
- database technology
- database access approach
- ORM or query framework
- migration mechanism
- main runtime entry points
- approximate major component count

SCREEN A02
Title: Data Architecture Overview

Include:
- raw-source storage strategy
- normalized storage strategy
- snapshot/history strategy
- execution metadata strategy
- legacy compatibility strategy
- local versus external data ownership

--------------------------------------------------
SECTION B — REPOSITORY STRUCTURE
--------------------------------------------------

SCREEN B01
Title: Repository Module Map

Show only a compact text tree using anonymous module IDs.

Example:

M01 Entry Points
  M01.1 CLI
  M01.2 HTTP

M02 Use Cases
M03 Domain Services
M04 Repositories
M05 Integrations
M06 Models
M07 Database
M08 Prompts
M09 Renderers

Use the actual repository structure.

SCREEN B02 onward
Title: Component MXX

For every important component provide:

- ID
- Role
- Called by
- Calls
- Reads database: YES / NO / PARTIAL
- Calls external systems: YES / NO / PARTIAL
- Contains business rules: YES / NO / PARTIAL
- Contains prompt logic: YES / NO / PARTIAL
- Approximate size: SMALL / MEDIUM / LARGE
- Notes

Use one important component per screen.

Minor components may be grouped two per screen.

--------------------------------------------------
SECTION C — DATABASE TABLE CATALOG
--------------------------------------------------

Use one core table per screen.

Use at most two minor tables per screen.

For every table screen use this exact format:

===== SCREEN CXX =====
Title: TXX — Generic Table Name

Purpose:
[maximum 25 words]

Category:
[RAW_SOURCE / CANONICAL_DOMAIN / TRANSACTIONAL / SNAPSHOT / REFERENCE / CONFIGURATION / EXECUTION_METADATA / LEGACY_COMPATIBILITY / UNKNOWN]

Importance:
[CORE / SUPPORTING / LEGACY]

Columns:
- C01: meaning | type | nullable | PK/FK/unique
- C02: meaning | type | nullable | PK/FK/unique
- C03: meaning | type | nullable | PK/FK/unique

Relationships:
- compact relationship descriptions

Read by:
- UC or component IDs

Written by:
- UC or component IDs

Update pattern:
[INSERT_ONLY / UPSERT / REPLACE / APPEND_HISTORY / MANUAL / MIXED / UNKNOWN]

Source lineage:
[maximum 30 words]

Known issue:
[maximum 30 words or NONE]

===== END SCREEN CXX =====

Do not output actual table names.

Do not output sample rows.

Do not output SQL.

--------------------------------------------------
SECTION D — DATABASE RELATIONSHIP MAP
--------------------------------------------------

SCREEN D01
Title: Core Entity Relationship Map

Use compact lines only.

Example:

T01 Person
  1 → many T03 Assignment
  many → many T05 Skill through T06

T02 Project
  1 → many T03 Assignment
  1 → many T07 Risk

Use actual relationships.

SCREEN D02
Title: Weak and Unenforced Relationships

Include:
- relationships implied by code
- application-enforced keys
- missing foreign keys
- nullable relationship risks
- legacy-link relationships

SCREEN D03
Title: Source-of-Truth Map

For each core concept state:
- primary table
- secondary table
- ambiguous ownership
- overwrite/version behavior

--------------------------------------------------
SECTION E — READ / WRITE MATRIX
--------------------------------------------------

Split the matrix across multiple screens.

Use at most 4 use cases per screen.

Use this format:

===== SCREEN EXX =====
Title: Read / Write Matrix — Part X

UC01 [generic purpose]
Reads: T01, T02
Writes: T03
Access: ORM / repository / direct SQL / mixed
Transaction: single / multiple / none / unknown
External dependency: YES / NO / PARTIAL
Destructive: YES / NO

UC02 ...

===== END SCREEN EXX =====

Include at minimum:

- staffing recommendation
- workload view
- capacity forecast
- weekly delivery summary
- action management
- decision management
- snapshot management
- project listing
- source freshness
- change-request import
- release synchronization
- project health
- wiki comparison
- baseline data import
- contract status export

--------------------------------------------------
SECTION F — DOMAIN REPRESENTATION
--------------------------------------------------

Use one screen for every 3–4 concepts.

For each concept provide:

Concept:
[Person / Skill / Contract / Project / Demand / Assignment / Capacity / Milestone / Release / Work Item / Risk / Dependency / Action / Decision / Snapshot / Source Record]

Status:
[EXPLICIT / PARTIAL / IMPLICIT / MULTIPLE_INCOMPATIBLE / MISSING]

Primary tables:
[IDs]

Source of truth:
[table ID or UNKNOWN]

Important derived fields:
[short list]

Semantic gap:
[maximum 25 words]

--------------------------------------------------
SECTION G — STAFFING RECOMMENDATION TRACE
--------------------------------------------------

This section must be fully separate.

Do not mix it with any other section.

SCREEN G01
Title: Staffing Trace — User Input

Include:
- user inputs
- defaults
- optional inputs
- validation
- missing-input behavior

SCREEN G02
Title: Staffing Trace — Data Reads

Include:
- exact table read order
- purpose of each read
- source lineage
- legacy reads
- caching or reuse

SCREEN G03
Title: Staffing Trace — Eligibility Filters

List actual filters only.

For every filter provide:
- rule
- data used
- fail behavior
- configurable: YES / NO

SCREEN G04
Title: Staffing Trace — Scoring

Include:
- scoring factors
- weights or relative priority
- derived calculations
- tie-breaking
- missing-data behavior

Do not reveal proprietary business values if sensitive.

Use relative weights where necessary.

SCREEN G05
Title: Staffing Trace — Output and Writes

Include:
- result structure
- evidence returned
- warnings
- optional writes
- tables written
- transaction behavior
- confirmation behavior

SCREEN G06
Title: Staffing Trace — Structured Pseudocode 1

Provide the first half of language-neutral pseudocode.

No real names.

No source-code syntax tied to a programming language.

SCREEN G07
Title: Staffing Trace — Structured Pseudocode 2

Provide the remaining pseudocode.

SCREEN G08
Title: Staffing Trace — Coupling and Testability

Include:
- direct table coupling
- direct connector coupling
- dependencies on other capabilities
- reusable services
- testability
- observed missing tests
- extension difficulty

--------------------------------------------------
SECTION H — CODE CALL GRAPHS
--------------------------------------------------

SCREEN H01
Title: CLI Execution Path

Show actual call sequence using anonymous component IDs.

Example:

User Command
→ M01.1
→ M02.3
→ M03.2
→ M04.1
→ Renderer

Add short notes only where necessary.

SCREEN H02
Title: HTTP Execution Path

Use the same format.

SCREEN H03
Title: Prompt / Agent Execution Path

Show:
- prompt wrapper
- model call
- routing translation
- CLI or service invocation
- output handling

SCREEN H04
Title: Staffing Call Graph

Show the complete staffing call chain.

SCREEN H05
Title: Project Health Call Graph

Show the complete project-health call chain.

SCREEN H06
Title: Weekly Summary Call Graph

Show the complete weekly-summary call chain.

--------------------------------------------------
SECTION I — COUPLING AND DUPLICATION
--------------------------------------------------

Use at most 5 facts per screen.

Use:

CP01
Area:
Observed fact:
Affected components:
Impact:

Include:
- entry-point duplication
- direct database access
- direct connector access
- prompt/code rule overlap
- repeated context assembly
- repeated data retrieval
- capability bypasses
- legacy compatibility leakage

--------------------------------------------------
SECTION J — SCHEMA RISKS AND MIGRATION CONSTRAINTS
--------------------------------------------------

Use at most 4 risks per screen.

For each risk:

R01

Area:
[DUPLICATION / NORMALIZATION / SOURCE_OF_TRUTH / LEGACY / INTEGRITY / INDEXING / HISTORY / LINEAGE / NULLABILITY / TRANSACTION / OTHER]

Severity:
[P0 / P1 / P2]

Observed fact:
[maximum 30 words]

Affected tables:
[IDs]

Affected use cases:
[IDs]

Likely impact:
[maximum 30 words]

Do not recommend a solution.

Then create separate screens for migration constraints.

For each constraint:

MC01

Constraint:
[maximum 30 words]

Evidence:
[maximum 30 words]

Existing behavior depending on it:
[maximum 30 words]

--------------------------------------------------
SECTION K — CONFIDENCE AND UNKNOWN AREAS
--------------------------------------------------

SCREEN K01
Title: Confidence Assessment

For each section:
- confidence: HIGH / MEDIUM / LOW
- evidence inspected
- main limitation

SCREEN K02
Title: Unknown Areas

List:
- unknown facts
- unavailable artifacts
- external dependencies not inspected
- assumptions
- areas requiring manual confirmation

==================================================
FINAL QUALITY CHECK
==================================================

Before producing the response, verify:

- Every screen has a unique screen ID.
- Every screen has a title.
- Every screen follows the word limit.
- No screen contains source code.
- No screen contains confidential names.
- No screen contains actual data.
- Core tables use one screen each.
- Relationship map is separate.
- Staffing Trace is separate.
- Read/Write Matrix is split.
- No architecture recommendations are included.
- UNKNOWN is used instead of guessing.

Start with SCREEN A01.

Generate all screens in order.

Do not summarize at the end.
