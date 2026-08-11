# Development Workflow

## Purpose

This workflow turns an approved Delivery Manager problem into a small,
reviewable, maintainable change. It applies to human developers and coding
agents.

It does not authorize work by itself. The TPO selects the product problem and
accepts product behavior; the technical lead owns the engineering approach and
code quality.

## Roles

### TPO

- defines the business scenario, priority, scope, and non-goals;
- selects the Golden Path and target maturity;
- approves user stories and acceptance criteria;
- accepts or rejects product behavior;
- decides whether a capability should advance, pause, or retire.

### Technical lead or designated reviewer

- confirms capability ownership and architecture fit;
- approves material contract, dependency, schema, or refactor decisions;
- ensures the change is reviewable and maintainable;
- verifies that technical evidence supports the claim being made.

### Developer or coding agent

- inspects the real implementation before proposing a solution;
- implements only the approved bounded scope;
- supplies tests, documentation, and traceable evidence;
- reports uncertainty and stops at the agreed gate.

The same person may fill more than one role, but product acceptance and
technical evidence must still be recorded separately.

## Step 1: Define the change

The request must state:

- business or engineering objective;
- affected user and workflow;
- current problem and evidence;
- expected result;
- acceptance criteria;
- in-scope and out-of-scope behavior;
- product owner and technical owner.

For product work, also state the target maturity level and the actual DM
decision or action the result will support.

If these are unclear and different interpretations would materially change the
solution, clarify them before implementation.

## Step 2: Inspect the current system

Trace the existing path across the relevant surfaces:

- user entry and product Agent route;
- UI, CLI, or API;
- application use case;
- domain rule;
- persistence and schema;
- connector or imported source;
- tests and release path.

Record what already exists, what is reusable, where the actual break occurs,
and what remains unverified. Do not treat planning documents as proof of a
working call path.

## Step 3: Choose the smallest solution

Use this order:

1. configuration or documentation clarification;
2. defect correction in the owning capability;
3. connection of existing capabilities into the approved workflow;
4. small extension of an existing public contract;
5. new capability or architecture change only when the earlier options cannot
   meet the accepted outcome.

Write a short design before implementation when the change affects a public
contract, schema, data authority, module ownership, security boundary,
generated release artifact, DM Agent behavior, or more than one capability.

The design must include alternatives considered, compatibility, data impact,
test approach, rollback, and explicit non-goals. It requires TPO approval for
product behavior and technical-lead approval for engineering impact.

## Step 4: Prepare a bounded implementation slice

Before editing, name:

- exact behavior to add or correct;
- owning module and allowed dependencies;
- affected public contracts and data;
- focused tests;
- compatibility expectations;
- validation commands or acceptance procedure;
- stop condition and next gate.

Do not combine unrelated cleanup, future features, or opportunistic redesign
with the slice.

## Step 5: Implement and verify

During implementation:

- preserve unrelated user changes;
- use synthetic, anonymous test data;
- keep writes controlled and auditable;
- keep source facts and derived outputs separate;
- update tests with the behavior;
- document only facts supported by the implementation.

Verification must include focused tests and relevant regression checks. Add
clean re-import and release rehearsal when schema, onboarding, export,
packaging, or operational behavior changes.

When usability is claimed, verify the real user entry and full call path. Mark
any flow that cannot be exercised as **NOT YET VERIFIED**.

## Step 6: Review

Review the completed diff independently from implementation. The review checks:

- scope and acceptance criteria;
- reuse versus unnecessary addition;
- module and dependency boundaries;
- data ownership and failure behavior;
- security and write safety;
- tests and compatibility;
- documentation accuracy;
- product claim versus actual evidence.

Correct accepted findings and repeat the affected checks. Passing tests do not
replace review.

## Step 7: Product acceptance

Technical completion and product acceptance are different decisions.

For a product change, the TPO evaluates the agreed scenario using representative
synthetic or separately authorized operational data and records:

- accepted, rejected, or accepted with limitations;
- achieved maturity level;
- known gaps and follow-up decision;
- whether the behavior entered a repeatable DM workflow.

Do not label a capability L3 or L4 without this evidence.

## Step 8: Handoff and release

Update `PROGRESS.md` with the current state, evidence, risks, exact next action,
and Git state. Update the relevant design, contract, and user documentation
without copying current-state claims into multiple files.

A release is a separate gate. Verify the exact artifact, generated DM Agent,
installation or upgrade path, import/export continuity, rollback, and the
approved user acceptance scenario. Source validation is not release acceptance.

Push, merge, tag, deployment, publication, connector access, and real-data UAT
require their own explicit authorization.

## Pull-request minimum

Every pull request should answer:

1. What problem and user outcome does this change address?
2. Why is this the smallest suitable approach?
3. What existing assets are reused?
4. What modules, contracts, data, and compatibility are affected?
5. What was deliberately not implemented?
6. What tests, review, and acceptance evidence exist?
7. What risks, rollback, and next gate remain?

## Mapping to existing repository assets

This workflow condenses the current Developer Onboarding Index, `PROGRESS.md`
continuity rules, implementation-pack and review conventions, clean re-import
validation, release rehearsal, and the product-audit distinction between code,
tests, Owner use, and verified DM decisions.
