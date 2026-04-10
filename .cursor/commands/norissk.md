# norissk

**Универсальная точка входа** — агент анализирует задачу и сам выбирает workflow: workflow-scaffold, workflow-implement или workflow-feature. Выполняет соответствующие шаги.

**Использование:** `/norissk <описание задачи>` — например: `/norissk Добавь кнопку экспорта в PDF` или `/norissk Реализуй систему аутентификации с OAuth`

## Шаги

**Как вызывать субагентов:** при выполнении шагов workflow вызывай встроенный инструмент Cursor **`Task`** (`subagent_type`, `prompt`, `description`, …). Не выполняй роли planner/**designer**/worker/refactor/test-runner/debugger/reviewer-senior/documenter/security-auditor и др. самостоятельно — только через **`Task`**. См. workflow-scaffold / workflow-implement / workflow-feature и [`workflow-selection.mdc`](../rules/workflow-selection.mdc) (там же: почему не появляются отдельные субагенты).

1. **Анализ и выбор workflow**
   Проанализируй задачу по критериям из skill workflow-selector:
   - **scaffold** — один артефакт (функция, компонент, эндпоинт); мало зависимостей; нет auth/payments/sensitive data
   - **implement** — несколько связанных файлов; нужен review; средняя сложность; не требует декомпозиции
   - **feature** — auth, payments, sensitive data; много подзадач; нужна декомпозиция; архитектурные решения

   **Дизайн / презентации / UI-спеки без кода** (токены, слайды, макеты в markdown): обычно **scaffold** или **implement** с веткой **designer → documenter** — см. [`workflow-scaffold`](workflow-scaffold.md) / [`workflow-implement`](workflow-implement.md). Сложный продукт «дизайн + несколько подсистем кода» — **feature**, planner назначит **designer** на соответствующие подзадачи.

   Зафиксируй выбор (например: «Выбран workflow: scaffold»).

2. **Выполнение выбранного workflow**
   Выполни шаги соответствующей команды (workflow-scaffold / workflow-implement / workflow-feature):
   - **Git (опционально):** если пользователь явно не просит инициализировать репо — можно пропустить. Иначе: папка не git-репозиторий → `git init`, при наличии `gh` — `gh repo create`. В workflow-feature — полная интеграция (issues, ветки, PR).
   - **workflow-scaffold** — см. команду: при необходимости **designer** (дизайн-only или перед worker), иначе **worker** → test-runner → documenter
   - **workflow-implement** — опционально **designer**, затем **worker** → test-runner → reviewer-senior → documenter; ветка только дизайн: **designer → documenter**
   - **workflow-feature** — planner → [**designer** / worker / refactor по плану] → test-runner (если менялся код) → reviewer-senior → security-auditor (если нужно) → documenter

3. **Эскалация**
   Если в процессе выполнения задача оказалась сложнее выбранного workflow — переключись на следующий (scaffold → implement → feature). Триггеры: подзадачи, нужен security-auditor, >N файлов. При эскалации передай субагенту: выбранный workflow, что уже сделано, блокеры. Максимум одна эскалация за сессию.

## Результат

Перед возвратом результата:

1. **Session report:** сохрани отчёт в `.cursor/reports/session-<YYYYMMDD-HHmm>.json` (или путь из config.metrics.sessionsPath) со структурой: command (norissk), workflow, workflowReason, escalation, subagentsCalled, debuggerCalls, testsPassed, reviewerFindings, securityAuditorCalled, documentationCreated, taskSummary.
2. **Запусти скрипт метрик:** выполни `node .cursor/scripts/metrics-report.js`. Скрипт обновит METRICS_SUMMARY.md.
3. Включи итоговый скор из вывода скрипта в ответ (блок «Метрики» в конце).

Верни пользователю:
- Выбранный workflow и обоснование
- Результат выполнения (как в workflow-scaffold / workflow-implement / workflow-feature)
- Блок «Метрики» со скором

## Заметки

- Субагенты в отдельном контексте = вызовы **`Task`**. Канон и запреты по именам — [`CREATING_ASSETS.md` — «Инструмент Task»](../docs/CREATING_ASSETS.md#task-delegation).
- Используй skill workflow-selector для детальных критериев.
- При неопределённости — склоняйся к более полному workflow (implement лучше scaffold, feature лучше implement).
- Пользователь может явно указать workflow: `/norissk workflow-scaffold: добавь кнопку` — тогда не анализируй, выбери workflow-scaffold.
