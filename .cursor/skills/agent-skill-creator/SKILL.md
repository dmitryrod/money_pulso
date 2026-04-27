---
name: agent-skill-creator
description: >-
  Авторинг новых Agent Skills в `.cursor/skills/<name>/`: компактный SKILL.md, depth в references,
  явный output contract. Use when создаёшь или рефакторишь скилл в этом репозитории; внешние пакеты —
  через [ecosystem-integrator](../ecosystem-integrator/SKILL.md) и **`Task`** (см. CREATING_ASSETS).
---

# Agent Skill Creator (локальная адаптация)

## Summary

- Один скилл = один primary intent; дроби перегруженные темы.
- Главный файл — **операционный**; теория и длинные примеры — в `references/`.
- Любая оркестрация субагентов в тексте — только **`Task(subagent_type=..., ...)`** — [§ Task](../../docs/CREATING_ASSETS.md#task-delegation).

## Связь с ecosystem-integrator

- **Новый скилл с нуля** (внутренний) — этот документ + чеклист.
- **Пакет из skills.sh / внешний** — сначала [ecosystem-integrator](../ecosystem-integrator/SKILL.md) и команда **`/workflow-integrate-skill`**: сырой upstream не коммитить без адаптации под `Task`.

## Core workflow

1. Зафиксируй intent, триггеры, non-goals ([references/blueprint.md](references/blueprint.md)).
2. Frontmatter: `name`, `description` — паттерн `<what>. Use when <when>.`
3. Напиши минимальный `SKILL.md`: goal, workflow, strict rules, output contract, index ссылок.
4. Вынеси глубину в `references/*.md`; каждая ссылка из index должна существовать.
5. Прогон [references/quality-checklist.md](references/quality-checklist.md).
6. Если правишь много Markdown — опционально [md-design-system](../md-design-system/SKILL.md) / [md-compressor](../md-compressor/SKILL.md).

## Non-negotiable

- Папка = `name` из frontmatter = kebab-case.
- Нет запрещённых имён инструментов из таблицы в CREATING_ASSETS (только **`Task`** для субагентов).
- После нового сценария — строка или правка в [`agent-intent-map.csv`](../../docs/agent-intent-map.csv).

## Reference index

- [references/blueprint.md](references/blueprint.md)
- [references/file-layout.md](references/file-layout.md)
- [references/quality-checklist.md](references/quality-checklist.md)

## When to use

- Новый leaf/workflow skill под `.cursor/skills/`.
- Распил монолитного SKILL.md на references.
- Ревью качества скилла перед merge.
