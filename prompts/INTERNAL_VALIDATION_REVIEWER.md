# Internal Validation Reviewer Prompt

Act as an independent reviewer. Do not assume the implementation report is
correct. Inspect the changes, Architecture Kit, Implementation Pack, tests, and
relevant existing behavior.

Evaluate:

- architecture intent achieved;
- required contract satisfied;
- existing components reused;
- no duplicate connectors, repositories, routing, or logging introduced;
- legacy behavior preserved;
- boundaries and dependency direction respected;
- evidence and observability present;
- tests meaningful and passing;
- rollback practical;
- deviations explicitly documented.

Return PASS, PASS_WITH_ACTIONS, or FAIL. For every failure provide evidence,
impact, required correction, and whether release is blocked. Do not modify code
during the review.

