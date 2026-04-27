# Prompt templates (Prompt Enhancer)

## Полный шаблон (сложная / средняя задача)

```text
## Задача
[точное действие, без generic глаголов]

## Контекст проекта
- Workspace: [если известно]
- Релевантные файлы/директории: [...]
- Текущее поведение / состояние: [...]
- Целевое поведение / результат: [...]

## Маршрут Cursor
- Workflow: [scaffold | implement | feature | ... по workflow-selector; marketing_tactical / marketing_research если это маркетинг]
- Вызовы: Task(subagent_type="...", prompt="...", description="...")
- Skills to read: [пути .cursor/skills/.../SKILL.md]

## Ограничения
- Do not touch: [...]
- Do not add: [лишние deps без согласования]
- Ask before: [зависимости, деструктивные действия, схема БД, секреты]

## Ожидаемый результат
- Deliverables: [...]
- Output format: [...]

## Done when
- [бинарный критерий готовности]
- [тесты / линты / доки / ручная проверка — по смыслу]

## Проверка
- Команды: [как в .cursor/config.json → testing, если касается app/]
- Блокер: [что считать fail]
```

## Краткий шаблон (простой запрос)

```text
Сделай [target] в [scope]. Используй [workflow/primary agent по agent-intent-map + workflow-selector]. Учти контекст: [файлы/краткое что есть]. Не трогай [do-not-touch]. Готово, когда [Done when]. Проверь: [verification].
```

## Многошаговый сплит (MEDIUM+)

Если одним промптом нельзя закрыть без риска scope creep:

**Prompt 1** — plan/research (например `planner` или `researcher` + вывод).  
**Prompt 2** — implement (`worker` / …).  
**Prompt 3** — `test-runner` → `reviewer-senior` / `documenter` по workflow.

Каждый prompt — self-contained + ссылка на артефакт предыдущего шага.
