# Hard QA Rubric (Pass/Fail)

## Summary

- Use after drafting any agent file.
- Ship only when all checks pass.

## Gating checks

1. Role boundary clarity.
2. Explicit refusal/out-of-scope boundary.
3. Ambiguity handling in failure section.
4. Dependency/tool outage handling.
5. Conflict tie-break ownership.
6. Completion contract quality.
7. Output concreteness.
8. **Task / subagent_type** — роль вызывается как `Task(subagent_type="<name>", ...)`; имя совпадает с `name` в frontmatter.
9. Brevity and scanability.
10. Formatting hygiene.

## Decision rule

- **Ship** — all checks pass.
- **Revise** — any check fails.
