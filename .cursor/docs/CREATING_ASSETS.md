# CREATING_ASSETS — Гайд по созданию агентов, скиллов и команд

Этот файл описывает соглашения для **этого** проекта. Следуй им при добавлении нового агента, скилла или команды в `.cursor/`.

<a id="task-delegation"></a>

## Инструмент `Task` и делегирование (канон)

Этот раздел — **единственный источник истины** по имени инструмента субагентов. Любая новая команда, skill, rule или правка примера в `.cursor/` **не должна** его обходить.

### Что писать в инструкциях

- Субагенты вызываются только через встроенный инструмент Cursor **`Task`** (параметры `subagent_type`, `prompt`, `description`, при необходимости `model`, `readonly`, `run_in_background`).
- В примерах вызова используй **`Task(subagent_type="...", ...)`** или формулировки «вызови **`Task`** с …».

### Чего не писать (чтобы проблема не вернулась)

| Запрещено | Почему |
|-----------|--------|
| **`mcp_task`** в любом виде | Такого инструмента нет; модель не вызовет субагентов и сделает всё в одном агенте. |
| Связка «субагенты через MCP» без уточнения | Субагенты — **не** из списка MCP-серверов в настройках; путаница снова приведёт к неверному имени. |
| Другое выдуманное имя (`agent_task`, `subagent_mcp`, …) | Только **`Task`** совпадает с палитрой инструментов Cursor. |

Историческая ошибка репозитория: везде писали ложное имя (см. ячейку «Запрещено» в таблице выше) — заменено на **`Task`**. **Не возвращай** его при копипасте из старых чатов или внешних гайдов.

### Поведение IDE

«Отдельные окна» контекста субагентов бывают только если модель **реально вызывает `Task`**. Если в сессии нет инструмента `Task` (Ask, отключённые агентные инструменты), вся цепочка остаётся в одном чате — см. [`workflow-selection.mdc`](../rules/workflow-selection.mdc).

### Обязательная проверка перед merge любых правок в `.cursor/`

1. Поиск по `.cursor/`: строка из колонки «Запрещено» в таблице выше — **допустима только в этой таблице** (файл `CREATING_ASSETS.md`); во **всех остальных** файлах под `.cursor/` вхождений **ноль** (архив отчётов `.cursor/reports/*.json` не считается — там может быть история сессий). Удобно: `rg` / поиск IDE и просмотр совпадений.
2. В новых командах и skills — везде **`Task`**, не синонимы.
3. В [`rules/README.md`](../rules/README.md) при добавлении правила про workflow — ссылка на этот раздел (`#task-delegation`) или на [`workflow-selection.mdc`](../rules/workflow-selection.mdc).

---

<a id="agent-intent-map"></a>

## Карта формулировок → первичный агент → workflow

Визуальная схема: **какие глаголы в запросе** наводят на **кого звать первым** и **какой базовый workflow** (итоговая цепочка всё равно задаётся командами `/workflow-*` и skill [`workflow-selector`](../skills/workflow-selector/SKILL.md)). Делегирование — только через **`Task(subagent_type=...)`** ([`workflow-selection.mdc`](../rules/workflow-selection.mdc)).

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
| Документация | задокументируй, опиши API, обнови README, добавь docstrings | document, describe API, update README, add docstrings | documenter | scaffold / implement |
| Дизайн / презентации / UI-спеки | оформи, сверстай систему, макет слайдов, визуальная система | design, layout, deck, slides, tokens, mockup | designer | по контексту |

**Как читать таблицу**

- **Первичный агент** — с кого начать цепочку `Task` для типа задачи; стрелка `debugger → worker` означает: сначала отладка/диагностика, затем правка кода. Если нужны **только** правки в `app/docs/`, docstrings и README без смены логики кода — можно начать с **documenter** (или завершить любой workflow шагом documenter, как в командах `/workflow-*`).
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
  Invoked via Task with subagent_type="agent-name".
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
- [`documenter.md`](../agents/documenter.md) — документация (`app/docs/`, docstrings, README); скилл [`docs`](../skills/docs/SKILL.md)
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
- Субагенты вызываются **только** через `Task(subagent_type="...")`.
- Ссылки на другие команды и шаблоны — относительными путями `.cursor/...`.

### Список команд

- [`workflow-scaffold`](../commands/workflow-scaffold.md) — быстрый (при необходимости designer → worker или designer → documenter; см. ветвление в файле)
- [`workflow-implement`](../commands/workflow-implement.md) — средний (опционально designer; + reviewer-senior)
- [`workflow-feature`](../commands/workflow-feature.md) — полный (planner + designer/worker/refactor по плану + остальные субагенты)
- [`norissk`](../commands/norissk.md) — авто-выбор workflow

---

## Чеклист перед добавлением нового ассета

- [ ] **Делегирование:** канон из раздела [Инструмент `Task` и делегирование](#task-delegation); запрещённая строка только в таблице там, в остальном `.cursor/` — нет; нет формулировок «субагент через MCP» вместо `Task` без уточнения.
- [ ] Если меняется логика маршрутизации — обновлена **карта формулировок** (таблица выше) или явно сказано «вне таблицы» в описании агента/команды?
- [ ] Имя не конфликтует с существующим агентом/скиллом/командой?
- [ ] Frontmatter заполнен корректно (name, description)?
- [ ] Если агент — есть блок Required Skill Dependencies?
- [ ] Если скилл — примеры на Python, не на TypeScript?
- [ ] Если команда — субагенты вызываются только через `Task(subagent_type="...")`?
- [ ] Ссылки из других файлов обновлены (если ассет заменяет старый)?
- [ ] README правил обновлён если добавлено новое правило?
