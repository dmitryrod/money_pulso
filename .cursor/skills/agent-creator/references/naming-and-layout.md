# Naming and Layout

## Summary

- Standardized naming keeps agent packs predictable.
- Внешние паки: `<role>-agent.md`. **Этот репозиторий:** `.cursor/agents/<slug>.md` и `name: <slug>` в frontmatter.

## File naming (this repo)

- Pattern: `.cursor/agents/<slug>.md` (kebab-case).
- `slug` == `subagent_type` для **`Task(subagent_type="<slug>", ...)`**.
- Примеры: `reviewer-senior.md`, `test-runner.md`, не `reviewer.md`.

## One role per file

- Do not combine distinct professions unless the file is a defined orchestrator role.

## Placement

- Агенты живут только в `.cursor/agents/`.

## Agents vs skills

- Agent: role behavior and decision boundaries.
- Skill: reusable procedural guidance.
- Reference skills by folder name under `.cursor/skills/`.

## Portability note

- Для внешнего копирования агента в другой проект — перепиши пути в Required Skill Dependencies под тот репозиторий.
