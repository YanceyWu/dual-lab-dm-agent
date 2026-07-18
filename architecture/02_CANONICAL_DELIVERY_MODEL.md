# Canonical Delivery Model

## Purpose

Provide one local delivery-management language independent of JIRA, Confluence,
SharePoint, spreadsheets, and exported documents.

## Data zones

### Raw source zone

Preserves source payload, stable source reference, import batch, observed time,
parser version, and processing status. Raw data is evidence, not the domain API.

### Canonical domain zone

Contains normalized management concepts and relationships used by domain services
and decision use cases.

### Derived and snapshot zone

Contains calculated capacity, health signals, recommendations, point-in-time
snapshots, and execution evidence. Derived facts state calculation version and
source observation time.

## Initial concepts

- `Person`: delivery resource identity, role, status, capacity factor.
- `Skill`: capability and proficiency evidence.
- `Contract`: coverage period, status, and renewal risk.
- `Project`: delivery scope, lifecycle, priority, and ownership.
- `Demand`: requested effort, period, skills, priority, and constraints.
- `Assignment`: person-to-project allocation across a time period.
- `Capacity`: available effort derived for a person and time bucket.
- `Milestone` and `Release`: planned delivery commitments and readiness.
- `WorkItem`: normalized unit of delivery work.
- `Risk` and `Dependency`: threats, blockers, ownership, due dates, evidence.
- `Action` and `Decision`: management follow-up and decision memory.
- `Snapshot`: point-in-time canonical state.
- `SourceRecord`: provenance link to the raw source observation.

## Required metadata

Canonical records should support, where applicable:

- stable local identifier;
- source and source reference;
- observed, effective, created, and updated times;
- confidence or completeness status;
- ownership and lifecycle state;
- evidence links;
- schema or calculation version.

## Migration rule

Do not replace all current tables at once. Introduce canonical contracts at use-
case boundaries, adapt existing tables behind them, and migrate one vertical
slice at a time. Preserve raw records for traceability.

