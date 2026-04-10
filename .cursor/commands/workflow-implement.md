# workflow-implement

**Workflow с review** — цепочка субагентов для задач средней сложности (несколько связанных файлов, нужен code review). Опционально **designer** даёт спеки; **worker** создаёт код и тесты; Test-Runner верифицирует; Reviewer-Senior проверяет качество и архитектуру; Documenter добавляет документацию.

**Использование:** `/workflow-implement <описание задачи>` — например: `/workflow-implement Добавь валидацию форм с отображением ошибок`

## Шаги

**Как вызывать субагентов:** для каждого шага вызывай инструмент **mcp_task** с параметрами subagent_type (`designer` | `worker` | `test-runner` | `debugger` | `reviewer-senior` | `documenter`), prompt, description. Не выполняй роли designer/worker/test-runner/reviewer-senior/documenter самостоятельно — только через mcp_task.

**Ветвление:** если задача **преимущественно дизайн** (несколько файлов спеков, токены, презентация, без кода приложения): **designer → documenter** (шаг 5) — шаги **2–4** (worker, test-runner, reviewer-senior) **пропусти**, в резюме укажи причину. Если **UI/фича с кодом и нужны спеки до реализации** — шаг 1 **designer** (если нужен), затем шаги **2–5** как ниже.

Выполни последовательно, делегируя каждому субагенту его часть:

0. **Инициализация репо (если задача — создать новый проект)**
   - Если папка не git-репозиторий: `git init`, при наличии `gh` — `gh repo create`. Опционально — один issue на задачу. Ветка + PR в конце.

1. **Designer (опционально) — спеки до кода**
   - Если нужен отдельный слой дизайна: `mcp_task(subagent_type="designer", ...)` перед worker. Иначе сразу worker.

2. **Worker — реализация**
   - Вызови mcp_task(subagent_type="worker", prompt="...", description="Worker implementation") с задачей из запроса пользователя (и ссылкой на артефакты designer, если были).
   - Worker создаёт код и тесты (если применимо).
   - Дождись завершения.

3. **Test-Runner — верификация**
   - Вызови mcp_task(subagent_type="test-runner", ...) для запуска тестов.
   - Если тесты падают — test-runner исправляет (сохраняя намерение теста).
   - Если test-runner не справляется — вызови mcp_task(subagent_type="debugger", ...). После исправления — снова test-runner.
   - Дождись успешного прохождения или явного отчёта о проблемах.

4. **Reviewer-Senior — code review**
   - Вызови mcp_task(subagent_type="reviewer-senior", ...) для проверки качества кода и архитектуры.
   - Если reviewer-senior нашёл проблемы — исправь или вызови mcp_task(subagent_type="debugger", ...) для сложных исправлений.
   - Повтори reviewer-senior при необходимости.

5. **Documenter — документация**
   - Вызови mcp_task(subagent_type="documenter", ...) для создания документации.
   - Documenter добавляет docstrings, README-секцию или API-описание. Не создаёт `ai_docs/` — только inline и README.
   - Дождись завершения.

## Результат

Перед возвратом результата:

1. **Session report:** сохрани отчёт в `.cursor/reports/session-<YYYYMMDD-HHmm>.json` (путь из config.metrics.sessionsPath) со структурой: command (workflow-implement), workflow (implement), escalation, subagentsCalled, debuggerCalls, testsPassed, reviewerFindings, securityAuditorCalled, documentationCreated, taskSummary.
2. **Запусти скрипт метрик:** `node .cursor/scripts/metrics-report.js`.
3. Включи итоговый скор в ответ (блок «Метрики»).

Верни пользователю резюме:
- Что реализовано
- Статус тестов
- Замечания reviewer-senior и исправления
- Где находится документация
- Блок «Метрики» со скором

## Заметки

- **Средний уровень.** Для простых задач используй `/workflow-scaffold`, для сложных фич с декомпозицией — `/workflow-feature`.
- Не вызывай planner, security-auditor — это scope `/workflow-feature`.
- **Designer** — перед worker, если нужны токены/макеты/слайды; или отдельная ветка designer → documenter без кода (см. ветвление выше).
- Debugger вызывается при падении тестов (шаг 3) или при необходимости исправить замечания reviewer-senior (шаг 4).
- Если проект без тестов — пропусти шаг 3, укажи это в резюме.
