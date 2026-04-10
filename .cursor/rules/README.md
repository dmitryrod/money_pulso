# Rules — Оглавление правил `.cursor/rules/`

Все правила применяются автоматически (`alwaysApply: true`). Здесь — краткое описание зачем каждое существует и как связано с агентами/скиллами.

| Файл | Суть | Связанные ассеты |
|------|------|-----------------|
| [`workflow-selection.mdc`](workflow-selection.mdc) | При запросе на реализацию — выбрать workflow (scaffold/implement/feature) и делегировать субагентам через **Task**; задачи дизайна/спеков — через субагента **designer**, не подменять вручную | [`skills/workflow-selector`](../skills/workflow-selector/SKILL.md), [`commands/norissk.md`](../commands/norissk.md), [карта глаголов → агент → workflow](../docs/CREATING_ASSETS.md#agent-intent-map) |
| [`documentation.mdc`](documentation.mdc) | Когда и что обновлять в `app/docs/`: CHANGELOG, ARCHITECTURE, troubleshooting, .env.example. Google-style docstrings. | [`skills/docs`](../skills/docs/SKILL.md), [`agents/documenter.md`](../agents/documenter.md) |
| [`testing.mdc`](testing.mdc) | Unit/integration/e2e тесты, стиль Arrange-Act-Assert, именование тест-функций | [`agents/test-runner.md`](../agents/test-runner.md) |
| [`security.mdc`](security.mdc) | Базовые требования: секреты в env, валидация входов, параметризованные запросы | [`skills/security-guidelines`](../skills/security-guidelines/SKILL.md), [`agents/security-auditor.md`](../agents/security-auditor.md) |
| [`commit-messages.mdc`](commit-messages.mdc) | Conventional Commits: feat/fix/docs/refactor/chore, scope, 72 символа | [`skills/git-helper`](../skills/git-helper/SKILL.md) |
| [`git-workflow.mdc`](git-workflow.mdc) | Ветки (feature/fix), PR с Closes #N, squash/rebase | [`skills/git-helper`](../skills/git-helper/SKILL.md) |

## Добавление нового правила

1. Создай `.mdc` файл с frontmatter `description:` и `alwaysApply: true`.
2. Добавь строку в таблицу выше.
3. Если правило связано с агентом/скиллом — обнови их.

Подробнее о создании ассетов: [`docs/CREATING_ASSETS.md`](../docs/CREATING_ASSETS.md). Канон имени инструмента субагентов (`Task`): [`CREATING_ASSETS.md` → «Инструмент Task»](../docs/CREATING_ASSETS.md#task-delegation).
