# workflow-scaffold

**Быстрый workflow** — три субагента для простых задач (компонент, функция, эндпоинт). Без планирования, без code review, без security audit. Worker создаёт код и тесты, Test-Runner верифицирует, Documenter добавляет документацию.

**Использование:** `/workflow-scaffold <описание задачи>` — например: `/workflow-scaffold Создай React компонент Button с пропсами label и onClick`

## Шаги

**Как вызывать субагентов:** для каждого шага вызывай инструмент **Task** с параметрами subagent_type (`designer` | `worker` | `test-runner` | `debugger` | `documenter`), prompt, description. Не выполняй роли designer/worker/test-runner/documenter самостоятельно — только через Task.

Выполни последовательно, делегируя каждому субагенту его часть:

0. **Инициализация репо (если задача — создать новый проект)**
   - Если папка не git-репозиторий: `git init`, при наличии `gh` — `gh repo create`. Ветка и PR — опционально.

**Ветвление по типу задачи**

- **Только дизайн / токены / UI-спеки / слайды (без кода приложения):** `designer` → `documenter`. Пропусти worker и test-runner; в резюме укажи причину.
- **Дизайн-спека, затем код:** `designer` → далее шаги 1–3 как ниже.
- **Обычная реализация кода:** шаг 1 без designer.

1. **Worker — реализация**
   - Вызови Task(subagent_type="worker", prompt="...", description="Worker implementation") с задачей из запроса пользователя.
   - Worker создаёт код и тесты (если применимо).
   - Дождись завершения.

2. **Test-Runner — верификация**
   - Вызови Task(subagent_type="test-runner", ...) для запуска тестов.
   - Если тесты падают — test-runner исправляет (сохраняя намерение теста).
   - Если test-runner не справляется — вызови Task(subagent_type="debugger", ...) (единственное исключение для этого workflow).
   - Дождись успешного прохождения или явного отчёта о проблемах.

3. **Documenter — документация**
   - Вызови Task(subagent_type="documenter", ...) для создания документации.
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

- **Минимальный набор.** Не вызывай planner, reviewer-senior, refactor, security-auditor. Debugger — только если test-runner не справляется с падениями тестов. Для сложных фич используй `/workflow-implement` или `/workflow-feature`.
- Для простых задач (одна функция, один компонент) этот workflow занимает минуты.
- Если проект без тестов — пропусти шаг 2, укажи это в резюме.
