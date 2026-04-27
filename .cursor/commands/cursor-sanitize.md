# cursor-sanitize

**Локальная гигиена `.cursor/`** — удаление сессионных кэшей, отчётов, RAG-индексов, временных gh-файлов и **generated** вывода Marp в `dist/`, не трогая версионируемую сборку (агенты, скиллы, команды, доки).

**Использование:** `/cursor-sanitize` или явный промпт, например: `очисти .cursor, сначала сухой прогон`

## Шаги (оркестрация)

1. **Worker** — единственный, кто запускает CLI и пишет краткое резюме.
   - Сначала: `node .cursor/scripts/sanitize-cursor.mjs --dry-run` (из **корня** workspace) — в выводе таблица: путь, действие, причина.
   - После визуальной проверки: при необходимости повторить **без** `--dry-run` и с флагом **`--force`** (обязателен в **неинтерактивной** среде / CI, и otherwise если не хотите вводить `yes` в TTY).
   - Опции скрипта: `--soft` (только минимальный список), `--all` (агрессивнее, не вместе с `--soft`), `--strip-project-identity` (осторожно: бэкап/удаление/замена `marketing-context.md`), `--replace-with-example` (только вместе с `--strip-project-identity` и при наличии [`.cursor/marketing-context.example.md`](../marketing-context.example.md)).
2. **Documenter** (опционально) — если менялись инструкции/контракт; обычно **не** нужен для однократного прогона sanitize.

**Как вызывать субагентов:** `Task(subagent_type="worker", prompt="...", description="Run sanitize-cursor.mjs")`. Не выполняй роль worker сам, если `Task` доступен.

## Результат

- Краткое резюме: что снова видно в `--dry-run`, какие флаги применялись.
- При изменении сценария в репо — обнови [`agent-intent-map.csv`](../docs/agent-intent-map.csv) (строка `cursor_hygiene`) согласно [§ local-hygiene](../docs/CREATING_ASSETS.md#local-hygiene).

## См. также

- [`.cursor/docs/CREATING_ASSETS.md` § Local hygiene](../docs/CREATING_ASSETS.md#local-hygiene)
- [`.cursor/scripts/sanitize-cursor.mjs`](../scripts/sanitize-cursor.mjs)
