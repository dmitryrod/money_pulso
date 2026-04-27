# Аудит сборки Cursor agents/skills

Дата: 2026-04-26

## Ключевые выводы

1. `.cursor/config.json`, `docs` skill и несколько агентов считают `app/` основным деревом проекта, но в workspace нет `app/`. Это ломает документационные и тестовые маршруты по умолчанию.
2. RAG-память ищет `agent-transcripts` по slug, который не совпадает с фактическим slug Cursor для этого workspace: код сохраняет `_`, а Cursor использует дефисы.
3. `.gitignore` игнорирует всю `.cursor/`, поэтому сборка оркестрации не будет нормально версионироваться в новом git-репозитории.
4. hh.ru/Playwright workflow удалён из этой сборки как чужой project-specific контур.
5. Marp/Polza ветка хранит презентационные ассеты в `.cursor/presentations/`.
6. GitHub-команды содержат битые относительные ссылки на `.cursor/templates/gh-commands.md` из `.cursor/commands/`.

## План исправлений

1. Выбрать профиль репозитория: `cursor-toolchain` без `app/` или application repo с `app/`. Для текущего workspace предпочтителен `cursor-toolchain`.
2. Обновить `.cursor/config.json`, `.cursor/rules/documentation.mdc`, `.cursor/skills/docs/SKILL.md`, `worker`, `researcher`, `documenter`, `imager`: убрать обязательный `app/` как default и задать `.cursor/docs`, `.cursor/plans`, `.cursor/reports`, `.cursor/memory/tests` как канонические пути для этой сборки.
3. Исправить RAG slug: заменить ручной `_slugify_workspace` на autodiscovery по `%USERPROFILE%/.cursor/projects/*/agent-transcripts` с fallback на env vars; добавить тест для `agent_skills_creator -> agent-skills-creator`.
4. Переписать `.gitignore`: не игнорировать всю `.cursor/`; игнорировать только runtime-артефакты (`.cursor/reports/session-*.json`, `.cursor/reports/METRICS_SUMMARY.md`, `.cursor/active_memory.md`, `.cursor/memory/chroma_db/`, `.cursor/memory/rag_fts.sqlite`, `.cursor/memory/.ingest_state.json`, временные gh title/body).
5. Удалено: hh.ru workflow не является активной инструкцией этой сборки.
6. Для Marp/Polza использовать `.cursor/presentations/scripts/polza_marp_images.py` и `.cursor/presentations/dist`.
7. Исправить ссылки из `.cursor/commands/*.md` на `../templates/gh-commands.md`.
8. Добавить lightweight validation script для `.cursor`: проверка существования файлов из ссылок, agent/skill frontmatter, CSV references, запрет `mcp_task`, наличие тестовой команды.

## Проверки после исправлений

- `python -m pytest .cursor/memory/tests -q`
- `node --check .cursor/scripts/metrics-report.js`
- `python -m py_compile .cursor/hooks/rag_before_submit.py .cursor/hooks/rag_session_end.py .cursor/memory/engine.py .cursor/memory/sqlite_backend.py`
- новый validator: `python .cursor/scripts/validate_cursor_assets.py`
