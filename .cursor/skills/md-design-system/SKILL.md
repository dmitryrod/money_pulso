---
name: md-design-system
description: >-
  Лёгкий контракт форматирования Markdown для `.cursor/`: заголовки, списки, структура без изменения фактов.
  Use when нормализуешь skills, agents, docs; не применяй к каноническим таблицам «запрещено» в CREATING_ASSETS без ручного review.
---

# MD Design System (локальная адаптация)

## Core Rules

1. **Format only** — never change facts, decisions, constraints, or values.
2. **Template first** — [CREATING_ASSETS § Агенты/Скиллы](../../docs/CREATING_ASSETS.md) и YAML frontmatter скиллов задают обязательные поля; не удалять.
3. **One H1 + no heading skips** — `#` then `##` then `###` then `####` (для тел без frontmatter; в `SKILL.md` после frontmatter первый заголовок — `#`).
4. **Lists over prose** — bullets and steps for scanability.
5. **Named items over tables** — `- **name** — value` for fields/interfaces where applicable.
6. **Canonical syntax** — см. [references/canonical-syntax.md](references/canonical-syntax.md).
7. **Lean output** — remove decorative noise and repetition.
8. **Filenames** — skill folder kebab-case; entry `SKILL.md`. Агенты: `.cursor/agents/<slug>.md` (не обязательно суффикс `-agent.md`).

## Workflow

1. Выбери профиль: [references/canonical-profiles.md](references/canonical-profiles.md) (skill / spec / generic). Для агентов этого репозитория сохраняй блоки из CREATING_ASSETS (Required Skill Dependencies, When invoked, DO/DON'T, Checklist).
2. Нормализуй синтаксис и структуру.
3. [references/normalization-checklist.md](references/normalization-checklist.md) перед merge.

## Этот репозиторий

- Не переставляй секции так, чтобы нарушить якоря в других `.md`, которые на них ссылаются.
- Таблицы в `agent-intent-map.csv` и кодовые блоки с примерами `Task` — не «упрощать» до потери точности.

## Reference Index

- [references/canonical-profiles.md](references/canonical-profiles.md)
- [references/molecules.md](references/molecules.md)
- [references/canonical-syntax.md](references/canonical-syntax.md)
- [references/normalization-checklist.md](references/normalization-checklist.md)
- [references/context-budget.md](references/context-budget.md)

## When To Use This Skill

- Рефакторинг больших `SKILL.md` / доков под единый стиль.
- Финальный format pass после [agent-skill-creator](../agent-skill-creator/SKILL.md) или [agent-creator](../agent-creator/SKILL.md).
