# Layered Project Health and Milestone Evolution

Status: `LAYERED HEALTH INTENT APPROVED — PHASE 4 DESIGN PROPOSED`
Last updated: 2026-07-29
Baseline branch: `codex/phase-2-attention-center`
Trigger: IP-028 Batch C2 product-contract review

## Decision supported

Replace the current single Jira weighted-grade mental model with an explainable
three-layer health architecture:

1. Sprint Execution Health;
2. Release and Milestone Health; and
3. seven-dimension Project Health.

Story points remain useful evidence for Sprint execution. They are not a
substitute for Release commitments, milestone achievement, dependency
readiness, or overall Project Health.

The owner approved this architecture revision on 2026-07-29. The approval
establishes architecture intent and phase ownership. The bounded IP-028 C2
public-interface correction and its mutation-boundary review fix are
implemented, locally validated, and technically re-reviewed without remaining
P0-P2 findings. The owner accepted the correction and Batch D validation
passed. That approval did not itself authorize Phase 2 promotion. A subsequent
owner decision promoted Phase 2 locally on 2026-07-29; it does not authorize
Phase 3/4 runtime, connector, real-data, milestone schema, release, push,
merge, or tag work.

## Verified current behavior

The current Jira health sync calculates four scores:

| Current score | Current evidence | Current overall weight |
| --- | --- | ---: |
| release burndown, persisted as `velocity_score` | release done/total story points against an assumed 90-day line to release date | 35% |
| Sprint completion | completed versus committed Sprint story points | 25% |
| defects | weighted P1/P2 and P3/P4 defects relative to completed stories | 25% |
| scope change | net story-point delta from the prior version snapshot | 15% |

The weighted score is currently converted to `GREEN` at 75 or above,
`YELLOW` from 50 through 74.9, and `RED` below 50. Missing story-point
baselines receive neutral-looking fallback scores rather than an explicit
unavailable state.

The Phase 2 Attention rule does not evaluate those four scores directly. It
reads the already-computed Jira grade and a Confluence RAG label, maps each
label to `red`, `amber`, or `clear`, and applies source/state precedence.

There is no canonical milestone or release-commitment model. The current
evolution plan requires normalized milestone inputs for Forecast but does not
assign an earlier phase to create them.

## Owner decisions recorded

The owner confirmed on 2026-07-29 that:

- a project override may target only a project that already exists in the
  canonical local project registry;
- Delivery Managers need to configure bounded health conditions, not edit a
  technical label mapping;
- the current four Jira factors need configurable condition semantics;
- milestone achievement is a required Release and Project Health input;
- a Release Version may exist before its stories have story points, so missing
  story points cannot stand in for Release risk or receive a fabricated neutral
  score; and
- the system remains decision support, not a manager-supervision workflow.

## Layered health model

### Layer 1 — Sprint Execution Health

Decision question:

> Is the active Sprint executing as planned?

Candidate fixed factor catalog:

- Sprint commitment completion;
- Sprint goal status, when available as structured evidence;
- blocked or aging work;
- Sprint defects;
- Sprint scope churn; and
- carry-over from prior Sprints.

Story-point evidence belongs here. If committed or completed story points are
missing, that factor is `unknown` or `not_available`; the engine must not
substitute 50.

### Layer 2 — Release and Milestone Health

Decision question:

> Is the Release or delivery commitment likely to achieve its critical gates
> on time?

Candidate fixed factor catalog:

- critical milestone adherence;
- Release target-date adherence;
- milestone forecast slip;
- prerequisite and dependency readiness;
- Release scope readiness;
- unresolved release blockers;
- quality/readiness gates; and
- evidence completeness and freshness.

Release Version and Milestone are related but distinct. A Release Version is a
scope container. A Milestone is a commitment, outcome, gate, or decision point.
Either may exist without a one-to-one counterpart.

Story points may qualify a Release signal when coverage is sufficient and the
scope is stable. They are never required for milestone-based Release Health.

### Layer 3 — Project Health

Decision question:

> Across the material delivery dimensions, is management attention required?

The seven dimensions remain:

- Schedule;
- Delivery;
- Scope;
- Quality;
- Resource;
- Dependency; and
- Governance.

Project Health consumes promoted facts and signals from the Sprint and
Release/Milestone layers. It must not average a critical missed milestone into
an apparently healthy composite.

## Canonical milestone and commitment intent

The future canonical model must describe sanitized concepts rather than source
schemas. At minimum:

| Concept | Required meaning |
| --- | --- |
| `milestone_id` | stable anonymous identifier |
| `project_id` | existing canonical stable anonymous project identifier |
| `milestone_type` | bounded type such as release, contractual, readiness, governance, or internal gate |
| `criticality` | bounded management impact; critical status may activate a hard health guard |
| `planned_date` | original approved target |
| `forecast_date` | latest supported forecast, distinct from commitment |
| `actual_date` | supported completion date |
| `status` | bounded lifecycle state |
| `release_commitment_ids` | optional stable links; no forced one-to-one relation |
| `dependency_ids` | optional canonical dependency links |
| `evidence` | normalized source references, never narrative inference |
| `freshness` | observed time, source state, and completeness |
| `rule_version` | deterministic evaluation contract |

Proposed milestone lifecycle vocabulary:

```text
planned | in_progress | at_risk | achieved | missed | cancelled | unknown
```

Narrative text may explain a returned fact but cannot create a milestone,
completion claim, due date, forecast, dependency, or criticality.

## Health factor and condition contract

### Fixed by deterministic code

- versioned factor identifiers;
- allowed source facts for each factor;
- allowed value types and bounded operators;
- missing/stale/conflict behavior;
- critical guard semantics;
- layer and dimension membership;
- reference integrity, evidence, and freshness;
- safe aggregation order; and
- validation and persistence.

No prompt, SQL, Python, executable expression, arbitrary field path, or
source-specific query is configurable.

### Configurable by the Delivery Manager

Within bounded definitions, the DM may configure:

- whether an approved factor applies to the selected layer/project type;
- state conditions and threshold bands;
- observation/lookahead windows within approved bounds;
- tolerance or grace periods;
- critical versus advisory treatment;
- a bounded weight only where a same-layer composite is explicitly approved;
- existing-project overrides; and
- removal of an existing-project override.

The DM does not create new factors. New factor types require an architecture
and implementation gate.

### Required condition form

Conditions are structured data over a fixed factor catalog. Initial operators
should be limited to bounded enums such as:

```text
in | equals | less_than | less_than_or_equal |
greater_than | greater_than_or_equal |
days_before | days_after
```

Cross-factor arbitrary Boolean expressions are not allowed. Critical guards and
aggregation are named, versioned strategies owned by deterministic code.

### Factor result states

Every factor returns one of:

```text
red | amber | green | unknown | stale | missing |
conflicting | not_available | not_applicable
```

`missing`, `unknown`, `stale`, `conflicting`, and `not_available` are never
converted into green or a neutral numeric score.

## Recommended deterministic aggregation

1. Evaluate each factor independently with evidence and freshness.
2. Apply approved critical guards before any composite.
3. A missed or overdue critical milestone may set Schedule or Delivery to red.
4. Red cannot be averaged away by green factors.
5. Amber remains visible when no red guard applies.
6. Green requires all mandatory factors for that dimension to be complete,
   fresh, non-conflicting, and green.
7. Insufficient mandatory evidence produces unknown/partial, not green.
8. Project Health exposes every dimension and the deterministic reason for the
   overall state.

Example milestone guards:

```text
critical milestone past planned_date and not achieved
    -> Schedule red

critical milestone forecast slips beyond approved tolerance
    -> Schedule red or amber according to the bounded condition

critical milestone due inside the lookahead window with incomplete evidence
    -> Schedule amber/unknown; never green
```

## Configuration workflow intent

An accepted future DM-operable configuration workflow requires:

1. a read-only projection of the current factor catalog, conditions, versions,
   defaults, existing-project overrides, and effective configuration;
2. propose/preview showing prior, proposed, and effective conditions;
3. explicit confirmation with a hashed, expiring, one-time token;
4. stale-version and no-op rejection;
5. atomic version creation;
6. separate confirmed evaluation/reconciliation before current health or
   Attention state changes; and
7. append-only safe audit without operational names or raw source payloads.

Project override preview fails with `PROJECT_NOT_FOUND` semantics when the
stable anonymous project does not exist. Preconfiguration for a future project
is out of scope unless separately designed with an explicit pending lifecycle.

## Phase ownership revision

### Phase 2 — Attention Center

Retain the accepted deterministic Attention foundation and C1 Center
interfaces. Phase 2 may consume the current Jira grade only as a legacy,
versioned source observation. It must not claim that the current label-mapping
write is the accepted DM-operable Project Health configuration model.

The local Batch C2 implementation at `71d90d3` is validated code but failed
product-contract review. It is not accepted or promoted. A separately approved
bounded correction must remove or disable its public mapping-configuration
surface while preserving C1 and safe existing data. Do not rewrite history or
silently drop an additive table.

### Phase 3 — Execution and milestone signal foundation

Add, after separate design approval:

- canonical milestone and release-commitment storage;
- release-to-milestone and dependency references;
- Sprint/Release signal separation;
- no-SP and incomplete-evidence states;
- incremental Jira issue-history and links already planned;
- deterministic milestone adherence and forecast-slip facts; and
- source freshness and bounded history for every new signal.

Phase 3 does not calculate seven-dimension overall Project Health or produce a
forecast.

### Phase 4 — Seven-dimension Project Health

Add, after Phase 3 promotion and separate design approval:

- versioned fixed factor catalog;
- DM-operable bounded condition configuration;
- dimension-specific health assessments;
- critical milestone guards;
- effective default and existing-project override projection;
- health snapshots with evidence/freshness;
- legacy Jira-grade strangler comparison; and
- explainable overall Project Health without averaging away red.

### Phase 7 — Forecast v1

Reuse promoted milestone/release-commitment history from Phase 3 and health
facts from Phase 4. Phase 7 adds deterministic forecast and backtesting; it
does not become the first owner of milestone data.

## Compatibility and migration direction

- Preserve `UseCaseResult 1.0` and existing Management Attention projections.
- Keep current Jira health snapshots readable as legacy evidence.
- Do not reinterpret historic fallback scores as known milestone or Release
  health.
- Introduce layered health through strangler comparison before retiring any
  legacy grade.
- No automatic project-status, milestone, action, staffing, or decision write.
- No connector or real-data action is authorized by this design.
- Any future schema is additive, versioned, synthetic-tested, and rehearsed
  before promotion.

## Required synthetic scenarios

1. A Release Version exists but no stories have story points; Sprint SP factors
   are unavailable while a critical milestone can still make Release Health
   red, amber, or green from complete evidence.
2. A Sprint is amber but every critical Release milestone remains on time;
   Project Health explains the Sprint risk without falsely declaring the
   Release missed.
3. Sprint completion is green but a critical milestone is overdue; Schedule
   and overall Project Health remain red.
4. A critical milestone forecast slips within and beyond configured tolerance.
5. Missing, stale, or conflicting milestone evidence never produces green.
6. Scope grows while milestone dates remain unchanged; Scope and Schedule
   remain separate and explainable.
7. An override for a nonexistent project fails before an operation or version
   is created.
8. Configuration preview exposes prior, proposed, and effective conditions;
   confirmation alone does not change health until separate evaluation.
9. Legacy Jira grade and layered health can be compared without changing
   Management Attention or `UseCaseResult 1.0`.
10. No real names, source payloads, credentials, or proprietary identifiers
    enter portable artifacts.

## Non-goals

- no Phase 3 or Phase 4 runtime implementation in this design revision;
- no live connector call or schema discovery;
- no black-box model score or narrative-derived milestone;
- no cross-team Story Point normalization assumption;
- no visual Dashboard Center;
- no automatic business-object write;
- no Phase 2 promotion, release, push, merge, or tag; and
- no silent deletion of the unaccepted local C2 storage.

## Approved decisions and exact next action

Owner review confirmed on 2026-07-29:

1. the Sprint/Release/Project layer separation;
2. milestone ownership moving to Phase 3 and reuse in Phases 4 and 7;
3. missing Story Points producing unavailable rather than neutral scores;
4. fixed factor catalog with bounded DM-configurable conditions;
5. critical milestone guards and non-averaging aggregation;
6. existing-project-only overrides; and
7. the unaccepted C2 mapping interface disposition.

The bounded IP-028 C2 correction removes the unaccepted public
mapping-configuration preview paths, blocks direct preview and legacy-token
confirmation, removes dormant configuration mutation helpers, preserves
accepted C1 behavior and additive data, and is locally validated. Technical
re-review found no remaining P0-P2 issue. The owner accepted the
correction and Batch D validation passed. The owner then promoted Phase 2
locally on 2026-07-29. The subsequent Phase 3 review is recorded in
`architecture/09_PHASE_3_EXECUTION_AND_MILESTONE_FOUNDATION_DESIGN.md` and
was approved by the owner on 2026-07-29. Phase 3 is subsequently promoted
locally. The implementation-level Phase 4 design is now proposed in
`architecture/11_PHASE_4_SEVEN_DIMENSION_PROJECT_HEALTH_DESIGN.md`; Phase 4
implementation remains unauthorized pending owner review.
