# Routing rules (Prompt Enhancer)

## Сначала: optimize vs execute

- Пользователь просит **улучшить/переписать промпт** → роль `prompt-enhancer`, итог = текст промпта (advisory-only).
- Пользователь просит **сделать фичу/фикс/рефакторинг** без «улучши промпт» → **не** оформлять ответ так, как будто `prompt-enhancer` — основной исполнитель; дай 1–2 предложения и перенаправь на маршрут по [`agent-intent-map.csv`](../../../docs/agent-intent-map.csv) + [`workflow-selector`](../../workflow-selector/SKILL.md).

## Источники истины

- Первичный агент и типичные цепочки: [`agent-intent-map.csv`](../../../docs/agent-intent-map.csv).
- Сложность workflow: [`workflow-selector/SKILL.md`](../../workflow-selector/SKILL.md) (`scaffold` / `implement` / `feature` / `workflow-integrate-skill` для внешних пакетов).
- Список допустимых `subagent_type`: только slug из [`.cursor/agents/*.md`](../../../agents/).

## Правила по типу задачи

- **`.cursor` authoring** (новый агент, новый скилл, нормализация md) — в генерируемом промпте указать чтение [`agent-creator`](../../agent-creator/SKILL.md) / [`agent-skill-creator`](../../agent-skill-creator/SKILL.md) / [`md-design-system`](../../md-design-system/SKILL.md), обновление CSV при новом сценарии: см. [CREATING_ASSETS](../../../docs/CREATING_ASSETS.md).
- **Маркетинг тактика** — `Task(subagent_type="marketing", ...)` после контекста; **маркетинг-исследование** — `marketing-researcher` (не сводить к `worker` из-за глагола «создай») — как в `workflow-selector`.
- **Свежие веб-факты** — `Task(subagent_type="researcher", ...)` до исполнителя; MCP по скиллу [`firecrawl-mcp`](../../firecrawl-mcp/SKILL.md) вызывает **делегированный** `researcher`, не подмена `Task`.
- **Security-sensitive** (auth, платежи, чувствительные данные) — в цепочке предусмотреть `security-auditor` в конце по [`workflow-feature`](../../../commands/workflow-feature.md) / `workflow-selector`.
- **Средняя+ сложность** — не один монолитный `worker` prompt: `Prompt 1` plan/research → `Prompt 2` implement → `Prompt 3` verify/review; каждый с явным DoD.

## Запрещено в тексте для пользователя

- Выдуманные `subagent_type` или несуществующие скиллы.
- Синонимы вместо **`Task`** для вызова субагентов.
- «Все субагенты подряд» — только минимально достаточная цепочка по [trigger-routing](../../../docs/CREATING_ASSETS.md#trigger-routing).
