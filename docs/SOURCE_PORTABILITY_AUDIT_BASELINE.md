# Source Portability Audit Baseline

Date: 2026-07-19
Scope: ignored local runtime under `src/`, excluding private-state and approved
sample-data directories
Status: `PORTABLE TEXT CHECK PASSED; INTERNAL-ONLY UNITS REMAIN BLOCKED`

## Safety model

The automated audit reads text locally but reports only the affected relative
path and risk category. It never prints the matched URL, email, identifier, or
absolute path value.

The audit is intentionally conservative and is not a secret scanner or a
replacement for human review.

## Initial category counts

| Category | Initial count | Default disposition |
| --- | ---: | --- |
| Company configuration unit | 2 | `INTERNAL_ONLY` |
| Historical documentation unit | 9 | `INTERNAL_ONLY` |
| Concrete URL in portable source | 9 | Review: configure, synthesize, or allow public vendor endpoint |
| Hard-coded numeric identifier | 9 | Review: synthetic fixture, configuration, or remove |
| Non-synthetic email domain | 2 | Replace in portable metadata/fixtures |
| Malformed or template URL | 2 | Review template construction; may be false positive |
| Absolute user path | 1 | Remove from portable source/test text |

Counts are a baseline, not a list of confidential values. Re-run the tool after
each sanitization slice; progress is measured by category reduction plus manual
unit approval.

### Current delta after portability slice 2

- Absolute user-path findings: reduced from 1 to 0.
- Non-synthetic email-domain findings: reduced from 2 to 0.
- Portable concrete-URL findings: reduced from 9 to 0.
- Portable hard-coded numeric identifiers: reduced from 9 to 0.
- Template URLs are accepted as non-concrete; Atlassian public OAuth/API hosts
  are classified as vendor protocol endpoints.
- `python3 tools/audit_source_portability.py --portable-only` passes.
- The full audit remains blocked by design because it includes units classified
  as `INTERNAL_ONLY`.

## Unit decisions

### Keep internal

- `configs/company/`
- `docs/history/`
- `docs/current/*UAT*`

These units are not required for the portable product core.

### Candidate portable core

- `pm_agent/config.py` after company defaults are removed;
- database bootstrap and repository layers after identifier review;
- use-case services and deterministic rules after alias/fixture review;
- connector contracts and generic connector implementations after endpoint
  classification;
- CLI and dashboard after template-path review;
- import scripts after synthetic-ID review;
- current tests after all fixtures use the approved synthetic language.

## Required review sequence

1. Remove obvious portable metadata/test false positives.
2. Separate company configuration and historical documentation permanently.
3. Replace company endpoint defaults with required local configuration.
4. Classify public vendor protocol endpoints separately from company endpoints.
5. Move hard-coded source identifiers into configuration or the canonical
   synthetic dataset.
6. Re-run runtime tests, tool tests, both safety checks, and this audit.
7. Approve only the clean units; keep the rest quarantined.

## Current conclusion

The automated portable-text gate now passes, but no runtime source directory is
approved for public transfer yet. Manual unit review, focused contract evidence,
and explicit quarantine narrowing remain required. Internal configuration,
history, and UAT evidence must never be included in a portable approval.
