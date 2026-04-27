# Authoring Workflow

## Summary

- Follow this sequence to produce consistent, lean agent files.
- Treat QA as a required gate, not optional review.

## Workflow

1. Define one profession per agent file.
2. Имя файла: `.cursor/agents/<slug>.md`, где `slug` = `name` в frontmatter.
3. Fill one-paragraph Identity from template.
4. Add optional Role summary if needed.
5. Add role pillars plus required failure and completion sections.
6. Run compression pass (shorten, dedupe, move deep detail into skills).
7. Add escalation only if constraints/completion do not already cover it.
8. Run brevity pass (remove repetition and emphasis noise).
9. Calibrate against exemplars for density and shape.
10. Run hard QA rubric and fix all failures.
11. Run final review checklist.

## Review Checklist

- [ ] `name` в frontmatter совпадает с именем файла (без `.md`).
- [ ] Required sections are present (включая блоки репозитория: Dependencies, When invoked, DO/DON'T, Checklist).
- [ ] Identity is one paragraph.
- [ ] DoD and handoff are testable.
- [ ] Нет запрещённых имён субагент-инструментов; везде канон **`Task`**.
- [ ] Target size and scanability are met.

## Refactoring Tips

- Replace bold-heavy lines with plain list items.
- Merge duplicate guidance across sections.
- Move large examples into skill references.
