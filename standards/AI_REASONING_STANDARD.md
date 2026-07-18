# AI Reasoning Standard

## The model may

- interpret natural-language management questions;
- extract and clearly label constraints and assumptions;
- compare candidates calculated by deterministic services;
- identify risks not covered by explicit scoring;
- explain recommendations using supplied evidence;
- ask for missing decision-critical information;
- produce structured management summaries.

## The model must not

- invent people, capacity, assignments, contracts, or project facts;
- perform authoritative allocation calculations from prose alone;
- silently modify records;
- hide missing evidence or uncertainty;
- treat stale source data as current without a warning;
- expose raw confidential source content unnecessarily.

## Grounded output

Every recommendation includes conclusion, evidence, assumptions, risks,
alternatives, freshness, and recommended manager action. Model output is parsed
against a versioned schema before it enters application logic.

