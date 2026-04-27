---
name: agent-creator
description: >-
  Авторинг lean role-driven агентов для `.cursor/agents/*.md`: границы роли, decision framework,
  failure modes, outputs, completion/handoff. Use when создаёшь или рефакторишь агента под этот репозиторий;
  канон делегирования — Task(subagent_type=...) и [.cursor/docs/CREATING_ASSETS.md](../../docs/CREATING_ASSETS.md).
---

# Agent Creator (локальная адаптация)

## Summary

- Строим **операционные** спеки ролей: не persona-only, а ownership + handoff.
- В этом репозитории файл агента — **`.cursor/agents/<slug>.md`** с YAML frontmatter (`name`, `description`, опционально `skills`), затем тело по паттернам ниже.
- Субагенты вызываются **только** через **`Task(subagent_type="<slug>", ...)`** — см. [§ Task](../../docs/CREATING_ASSETS.md#task-delegation). В тексте агента **не** используй выдуманные имена инструментов (`mcp_task` и т.д.).

## Соглашения этого репозитория

1. **`name` в frontmatter** = `subagent_type` (строчные, kebab-case): `worker`, `reviewer-senior`, не `reviewer`.
2. Обязательные блоки в теле: **Required Skill Dependencies**, **When invoked**, **DO / DON'T**, **Quality Checklist** — как в [CREATING_ASSETS § Агенты](../../docs/CREATING_ASSETS.md).
3. Дополнительно (из upstream): явный контракт **Completion and handoff** — DoD, stop, пакет для следующего `Task`, start rule; см. [references/completion-and-handoff.md](references/completion-and-handoff.md).
4. Пути к скиллам в зависимостях — **локальные**: `.cursor/skills/<skill>/SKILL.md` (это норма для этого репо; «портативность без путей» — для внешних паков, не догма).

## Core workflow

1. Выбери один profession / одна роль на файл.
2. Проверь, что `name` не конфликтует с существующими в [`.cursor/agents/`](../../agents/).
3. Заполни frontmatter по [CREATING_ASSETS](../../docs/CREATING_ASSETS.md).
4. Добавь секции по [references/agent-file-template.md](references/agent-file-template.md), адаптировав под шаблон репозитория (Required Skill Dependencies + чеклист).
5. Прогон **QA**: [references/qa-rubric.md](references/qa-rubric.md) — для пункта «portability» читай как «нет лишних секретов; пути только к `.cursor/` и `app/` осознанно».
6. Форматирование: при необходимости **[md-design-system](../md-design-system/SKILL.md)** (если скилл уже добавлен).

## Non-negotiable

- Делегирование следующей роли — через **`Task`**, не «сделай сам в одном ответе».
- **Completion and handoff** должен быть **тестируемым** (что именно получает следующий субагент).
- После добавления/смены агента — обновить **[`agent-intent-map.csv`](../../docs/agent-intent-map.csv)** при новых сценариях маршрутизации.

## Reference index

- [references/agent-file-template.md](references/agent-file-template.md) — структура секций.
- [references/completion-and-handoff.md](references/completion-and-handoff.md) — контракт завершения.
- [references/authoring-workflow.md](references/authoring-workflow.md) — порядок работы.
- [references/collaboration-patterns.md](references/collaboration-patterns.md) — sequential/parallel; в этом репо роли = `subagent_type`.
- [references/failure-modes.md](references/failure-modes.md)
- [references/naming-and-layout.md](references/naming-and-layout.md)
- [references/qa-rubric.md](references/qa-rubric.md)
- [references/role-vs-persona.md](references/role-vs-persona.md)
- [references/role-family-exemplars.md](references/role-family-exemplars.md)

## When to use

- Новый агент в `.cursor/agents/`.
- Рефакторинг перегруженного промпта в чеклист + handoff.
- Приведение агента к канону `Task` и CSV.
