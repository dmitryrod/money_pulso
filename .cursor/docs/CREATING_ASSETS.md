# CREATING_ASSETS — Гайд по созданию агентов, скиллов и команд

Этот файл описывает соглашения для **этого** проекта. Следуй им при добавлении нового агента, скилла или команды в `.cursor/`.

---

## Агенты (`.cursor/agents/`)

### Frontmatter-шаблон

```markdown
---
name: agent-name
description: >-
  One-sentence description of what this agent does and when to invoke it.
  Invoked via mcp_task with subagent_type="agent-name".
skills: [skill-one, skill-two]
---
```

### Соглашения

- Имена — строчные, без префикса `agt-`: `worker`, `planner`, `researcher`, не `agt-worker`.
- `description` — одно-два предложения; первое: что делает, второе: когда использовать.
- `skills` — только скиллы из `.cursor/skills/`, которые агент реально читает.
- В начале файла — блок **Required Skill Dependencies** с явным указанием, какие файлы читать.
- Секции DO/DON'T — по 3–5 пунктов, конкретные запреты/обязательства.
- Quality Checklist в конце — что должно быть выполнено перед завершением.

### Структура файла агента

```markdown
---
(frontmatter)
---

Короткое описание роли (1–2 предложения).

## Required Skill Dependencies

Before performing tasks:
1. Read `.cursor/skills/<skill>/SKILL.md`
2. Apply patterns from the skill — do NOT duplicate its content

## When invoked

1. ...
2. ...

## ✅ DO:
- ...

## ❌ DON'T:
- ...

## Quality Checklist
- [ ] ...
```

### Примеры существующих агентов

- [`worker.md`](../agents/worker.md) — базовый реализатор
- [`planner.md`](../agents/planner.md) — декомпозиция задач
- [`reviewer-senior.md`](../agents/reviewer-senior.md) — двухуровневый ревью

---

## Скиллы (`.cursor/skills/`)

### Frontmatter-шаблон

```markdown
---
name: skill-name
description: What this skill provides. Use when doing X.
---
```

### Соглашения

- Каждый скилл — отдельная папка: `.cursor/skills/skill-name/SKILL.md`.
- Имя папки = имя скилла в frontmatter.
- Скилл описывает **паттерны и чеклисты**, не конкретные задачи.
- Примеры кода — на Python (стек проекта), не TypeScript/JS.
- Скилл не дублирует содержимое другого скилла — только ссылается.
- Связанные агенты указывают скилл в frontmatter `skills: [...]`.

### Примеры существующих скиллов

- [`code-quality-standards`](../skills/code-quality-standards/SKILL.md) — чеклист для reviewer-senior Level 1
- [`architecture-principles`](../skills/architecture-principles/SKILL.md) — чеклист для reviewer-senior Level 2
- [`task-management`](../skills/task-management/SKILL.md) — формат задач для planner
- [`security-guidelines`](../skills/security-guidelines/SKILL.md) — паттерны безопасности

---

## Команды (`.cursor/commands/`)

### Соглашения

- Файл = команда: `workflow-feature.md` → `/workflow-feature`.
- Первая строка — заголовок `# command-name`.
- Вторая строка — краткое описание (что делает, какие субагенты).
- Субагенты вызываются **только** через `mcp_task(subagent_type="...")`.
- Ссылки на другие команды и шаблоны — относительными путями `.cursor/...`.

### Список команд

- [`workflow-scaffold`](../commands/workflow-scaffold.md) — быстрый (worker → test-runner → documenter)
- [`workflow-implement`](../commands/workflow-implement.md) — средний (+ reviewer-senior)
- [`workflow-feature`](../commands/workflow-feature.md) — полный (planner + все субагенты)
- [`norissk`](../commands/norissk.md) — авто-выбор workflow

---

## Чеклист перед добавлением нового ассета

- [ ] Имя не конфликтует с существующим агентом/скиллом/командой?
- [ ] Frontmatter заполнен корректно (name, description)?
- [ ] Если агент — есть блок Required Skill Dependencies?
- [ ] Если скилл — примеры на Python, не на TypeScript?
- [ ] Если команда — субагенты вызываются только через mcp_task?
- [ ] Ссылки из других файлов обновлены (если ассет заменяет старый)?
- [ ] README правил обновлён если добавлено новое правило?
