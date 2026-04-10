---
name: simple-workflow
description: Базовый workflow для /workflow-scaffold. Use when executing simple tasks: designer for design-only or before worker; worker creates code and tests; test-runner verifies; documenter adds documentation.
---

# Simple Workflow

Цепочка для быстрых задач. Команда: `/workflow-scaffold`. Подробное ветвление (дизайн-only, смешанное, только код) — в [`workflow-scaffold.md`](../../commands/workflow-scaffold.md).

## Последовательность (типичный код-путь)

1. **Designer** (если нужен) — спеки, слайды, токены
2. **Worker** — реализует код и тесты по описанию задачи
3. **Test-Runner** — запускает тесты, исправляет падения (сохраняя намерение теста)
4. **Documenter** — добавляет docstrings, README-секцию или API-описание

Для **только дизайна** без кода: **designer → documenter**, test-runner пропускается.

## Делегирование

Шаги выполняются через вызов **mcp_task** с subagent_type. Не выполняй роли designer/worker/test-runner/documenter самостоятельно — только через mcp_task.

## Связанные workflow

- **workflow-implement** — scaffold + reviewer-senior (средняя сложность)
- **workflow-feature** — полная оркестрация (сложные фичи)
- **norissk** — агент сам выбирает workflow-scaffold/workflow-implement/workflow-feature

## Когда применять

- Одна функция, один компонент, один эндпоинт
- Нет сложной декомпозиции
- Без code review и security audit

## Результат

Краткое резюме: что реализовано, статус тестов, где документация.
