---
name: workflow-selector
description: Use when implementing features. Analyze task complexity and choose workflow-scaffold/workflow-implement/workflow-feature. Apply when user asks to add, create, or implement something.
---

# Workflow Selector

При запросе на реализацию (добавить, создать, реализовать) — оцени сложность задачи и выбери один из трёх workflow.

## Критерии выбора

| Workflow | Когда выбирать |
|----------|---------------|
| **workflow-scaffold** | Один артефакт (функция, компонент, эндпоинт); мало зависимостей; нет auth/payments/sensitive data; задача укладывается в 1–3 файла |
| **workflow-implement** | Несколько связанных файлов; нужен code review; средняя сложность; не требует декомпозиции на подзадачи; 4–10 файлов |
| **workflow-feature** | Auth, payments, sensitive data; много подзадач; нужна декомпозиция; архитектурные решения; интеграция нескольких подсистем |

## Шаги каждого workflow (команды: /workflow-scaffold, /workflow-implement, /workflow-feature)

**workflow-scaffold:** при необходимости designer (дизайн-only: designer → documenter; или designer перед worker) → worker → test-runner → documenter

**workflow-implement:** при необходимости designer → worker → test-runner → reviewer-senior → documenter (ветка только дизайн: designer → documenter)

**workflow-feature:** planner → [designer / worker / refactor по плану] → test-runner → reviewer-senior → security-auditor (если security-sensitive) → documenter

## Делегирование

Шаги выполняются через вызов **Task** с subagent_type. Не выполняй роли субагентов сам — только делегируй через Task.

## Эскалация

Если в процессе выполнения задача оказалась сложнее выбранного workflow — переключись на следующий. **Триггеры эскалации:**
- scaffold → implement: появились связанные изменения, нужен review, затронуто >3 файлов
- implement → feature: появились подзадачи, нужна декомпозиция, нужен security-auditor (auth/payments/sensitive data)

**При эскалации** передай субагенту: выбранный workflow, что уже сделано, текущие блокеры. Максимум одна эскалация за сессию — при повторной необходимости сообщи пользователю.

## При неопределённости

Склоняйся к более полному workflow: workflow-implement лучше workflow-scaffold, workflow-feature лучше workflow-implement.
