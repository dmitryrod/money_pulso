# CREATING_ASSETS — Гайд по созданию агентов, скиллов и команд

Этот файл описывает соглашения для **этого** проекта. Следуй им при добавлении нового агента, скилла или команды в `.cursor/`.

---

<a id="agent-intent-map"></a>

## Карта формулировок → первичный агент → workflow

Визуальная схема: **какие глаголы в запросе** наводят на **кого звать первым** и **какой базовый workflow** (итоговая цепочка всё равно задаётся командами `/workflow-*` и skill [`workflow-selector`](../skills/workflow-selector/SKILL.md)). Делегирование в коде — только через **`mcp_task(subagent_type=...)`** ([`workflow-selection.mdc`](../rules/workflow-selection.mdc)).

| Группа | Слова RU | Слова EN | Первичный агент | Workflow |
|--------|----------|----------|-----------------|----------|
| Создание простое | добавь, создай, напиши, сгенерируй | add, create, write, generate | worker | scaffold |
| Создание сложное | реализуй, имплементируй, разработай, построй | implement, build, develop | worker | implement / feature |
| Интеграция | интегрируй, подключи, внедри, настрой, сконфигурируй | integrate, connect, setup, configure | worker | implement / feature |
| Общее | сделай, выполни, реши | do, make, solve | worker | по контексту |
| Исправление | исправь, починь, устрани | fix, patch, resolve | debugger → worker | scaffold / implement |
| Обновление | обнови, измени, переделай, расширь | update, change, modify, extend | worker | implement |
| Рефакторинг | рефактори, улучши, оптимизируй, упрости | refactor, optimize, improve, simplify | refactor | implement / feature |
| Миграция | мигрируй, перенеси, портируй | migrate, move, port, convert | worker / refactor | feature |
| Структура | переименуй, удали, перемести | rename, delete, remove, split | worker | scaffold |
| Деплой / сборка | задеплой, собери, запусти | deploy, build, run, launch | worker | scaffold |
| Дизайн / презентации / UI-спеки | оформи, сверстай систему, макет слайдов, визуальная система | design, layout, deck, slides, tokens, mockup | designer | по контексту |

**Как читать таблицу**

- **Первичный агент** — с кого начать цепочку `mcp_task` для типа задачи; стрелка `debugger → worker` означает: сначала отладка/диагностика, затем правка кода.
- **Workflow** — ориентир по сложности: `scaffold` / `implement` / `feature` из [`workflow-selector`](../skills/workflow-selector/SKILL.md). Ячейка **по контексту** — выбери workflow по критериям скилла, не по одному глаголу.
- **По контексту** и границы **implement / feature**: при сомнении — более полный workflow (как в скилле workflow-selector).
- Явная пользовательская команда **`/workflow-scaffold`**, **`/workflow-implement`**, **`/workflow-feature`**, **`/norissk`** переопределяет эвристику по глаголам.

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
- [`designer.md`](../agents/designer.md) — дизайн: слайды, токены, UI-спеки (не код приложения)
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
- [`stitch-mcp`](../skills/stitch-mcp/SKILL.md) — Google Stitch MCP для агента designer (экраны, дизайн-системы)
- [`figma-mcp`](../skills/figma-mcp/SKILL.md) — официальный Figma remote MCP (`mcp.figma.com`), OAuth в Cursor; пример конфига: [`mcp.figma.example.json`](../mcp.figma.example.json)

---

## Команды (`.cursor/commands/`)

### Соглашения

- Файл = команда: `workflow-feature.md` → `/workflow-feature`.
- Первая строка — заголовок `# command-name`.
- Вторая строка — краткое описание (что делает, какие субагенты).
- Субагенты вызываются **только** через `mcp_task(subagent_type="...")`.
- Ссылки на другие команды и шаблоны — относительными путями `.cursor/...`.

### Список команд

- [`workflow-scaffold`](../commands/workflow-scaffold.md) — быстрый (при необходимости designer → worker или designer → documenter; см. ветвление в файле)
- [`workflow-implement`](../commands/workflow-implement.md) — средний (опционально designer; + reviewer-senior)
- [`workflow-feature`](../commands/workflow-feature.md) — полный (planner + designer/worker/refactor по плану + остальные субагенты)
- [`norissk`](../commands/norissk.md) — авто-выбор workflow

---

## Чеклист перед добавлением нового ассета

- [ ] Если меняется логика маршрутизации — обновлена **карта формулировок** (таблица выше) или явно сказано «вне таблицы» в описании агента/команды?
- [ ] Имя не конфликтует с существующим агентом/скиллом/командой?
- [ ] Frontmatter заполнен корректно (name, description)?
- [ ] Если агент — есть блок Required Skill Dependencies?
- [ ] Если скилл — примеры на Python, не на TypeScript?
- [ ] Если команда — субагенты вызываются только через mcp_task?
- [ ] Ссылки из других файлов обновлены (если ассет заменяет старый)?
- [ ] README правил обновлён если добавлено новое правило?
