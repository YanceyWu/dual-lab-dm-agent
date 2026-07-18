# Use Case Standard

Every user-facing use case defines:

- stable ID and purpose;
- supported intents and generic example requests;
- input schema and validation;
- required canonical context;
- domain services used;
- deterministic rules and configurable thresholds;
- model reasoning role and prohibited inferences;
- output schema, evidence, warnings, and uncertainty;
- read/write behavior and confirmation requirement;
- failure modes and fallback behavior;
- execution tracing fields;
- scenarios, focused tests, and acceptance criteria.

## Shared execution contract

`UseCaseRequest` contains use-case ID, actor, parameters, requested output, and an
optional confirmation token.

`UseCaseResult` contains status, data, evidence, warnings, proposed writes, and
execution metadata.

Interfaces call this contract. They do not duplicate use-case routing or business
logic.

