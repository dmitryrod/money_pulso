# workflow-scaffold

**Быстрый workflow** — короткая цепочка субагентов для простых задач (компонент, функция, эндпоинт) или дизайн-артефактов. Без планирования, без code review, без security audit. При необходимости **designer** готовит спеки/слайды; **worker** создаёт код и тесты; Test-Runner верифицирует; Documenter добавляет документацию.

**Использование:** `/workflow-scaffold <описание задачи>` — например: `/workflow-scaffold Создай React компонент Button с пропсами label и onClick`

## Шаги

**Как вызывать субагентов:** для каждого шага вызывай инструмент **mcp_task** с параметрами subagent_type (`designer` | `worker` | `test-runner` | `debugger` | `documenter`), prompt, description. Не выполняй роли designer/worker/test-runner/documenter самостоятельно — только через mcp_task.

**Ветвление по типу задачи**

- **Только дизайн / презентации / UI-спеки** (нет изменений кода приложения): **designer → documenter**. Шаги с test-runner **пропусти**; в session report укажи `testsSkipped: true`, причину.
- **Смешанная задача** (сначала спеки/токены/макет, потом код): **designer → worker** → далее шаги 2–3 как ниже.
- **Только код** (как раньше): начинай с шага 1 — **worker**.

Выполни последовательно, делегируя каждому субагенту его часть:

0. **Инициализация репо (если задача — создать новый проект)**
   - Если папка не git-репозиторий: `git init`, при наличии `gh` — `gh repo create`. Ветка и PR — опционально.

1. **Designer или Worker — в зависимости от ветки**
   - **Designer** — если выбрана ветка «только дизайн» или «смешанная» (первый шаг): `mcp_task(subagent_type="designer", prompt="...", description="Designer specs")`. Дизайн-артефакты: токены, структура слайдов, описание UI — см. [`designer`](../agents/designer.md).
   - **Worker** — если ветка «только код» или после designer на «смешанной» ветке: `mcp_task(subagent_type="worker", prompt="...", description="Worker implementation")`. Worker создаёт код и тесты (если применимо).
   - Дождись завершения.

2. **Test-Runner — верификация** (только если затронут код в `app/` или другие тестируемые артефакты)
   - Вызови mcp_task(subagent_type="test-runner", ...) для запуска тестов.
   - Если тесты падают — test-runner исправляет (сохраняя намерение теста).
   - Если test-runner не справляется — вызови mcp_task(subagent_type="debugger", ...) (единственное исключение для этого workflow).
   - Дождись успешного прохождения или явного отчёта о проблемах.

3. **Documenter — документация**
   - Вызови mcp_task(subagent_type="documenter", ...) для создания документации.
   - Documenter добавляет docstrings, README-секцию или API-описание. Не создаёт `ai_docs/` — только inline и README.
   - Дождись завершения.

## Результат

Перед возвратом результата:

1. **Session report:** сохрани отчёт в `.cursor/reports/session-<YYYYMMDD-HHmm>.json` (путь из config.metrics.sessionsPath) со структурой: command (workflow-scaffold), workflow (scaffold), escalation, subagentsCalled, debuggerCalls, testsPassed, reviewerFindings, securityAuditorCalled, documentationCreated, taskSummary.
2. **Запусти скрипт метрик:** `node .cursor/scripts/metrics-report.js`.
3. Включи итоговый скор в ответ (блок «Метрики»).

Верни пользователю краткое резюме:
- Что реализовано
- Статус тестов
- Где находится документация
- Блок «Метрики» со скором

## Заметки

- **Минимальный набор.** Не вызывай planner, reviewer-senior, refactor, security-auditor. Debugger — только если test-runner не справляется с падениями тестов. **Designer** — для дизайн-only или первый шаг смешанных задач (см. ветвление выше). Для сложных фич используй `/workflow-implement` или `/workflow-feature`.
- Для простых задач (одна функция, один компонент) этот workflow занимает минуты.
- Если проект без тестов — пропусти шаг 2, укажи это в резюме.
