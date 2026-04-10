---
name: stitch-mcp
description: Google Stitch MCP (UI screens, design systems). Use when generating or editing Stitch projects/screens or syncing tokens with the designer agent.
---

# Google Stitch MCP

Официальный MCP: `https://stitch.googleapis.com/mcp`. В Cursor сервер задаётся в пользовательском `mcp.json` под именем **`stitch`** (см. заголовок `X-Goog-Api-Key`). **Ключ не коммитить** — только в локальном `mcp.json` или секретах окружения.

## Когда вызывать

- Генерация экранов из текста, варианты, правки экранов.
- Проекты Stitch: список, создание, детали.
- Дизайн-системы: список, создание, обновление, применение к экранам.

Агент **`designer`** использует эти инструменты для визуальной работы; реализация кода в приложении остаётся за **`worker`**.

## Вызов из Cursor

Перед первым вызовом прочитай JSON-схему нужного инструмента в каталоге MCP descriptors (если доступен): `mcps/user-stitch/tools/<tool>.json`.

Используй **`call_mcp_tool`** с **`server`**: в пользовательском `mcp.json` обычно **`stitch`**; в сессии Cursor иногда отображается как **`user-stitch`** — смотри список доступных MCP-серверов. Далее **`toolName`** из таблицы ниже.

## Инструменты (toolName)

| toolName | Назначение |
|----------|------------|
| `list_projects` | Список проектов (фильтр `view=owned` / `view=shared`). |
| `get_project` | Детали проекта по ID. |
| `create_project` | Новый проект (контейнер экранов). |
| `list_screens` | Экраны в проекте. |
| `get_screen` | Конкретный экран (после генерации — дождаться готовности). |
| `generate_screen_from_text` | Новый экран из промпта (**долго**, не ретраить подряд; при обрыве — позже `get_screen`). |
| `edit_screens` | Правки экранов по промпту. |
| `generate_variants` | Варианты дизайна. |
| `list_design_systems` | Доступные дизайн-системы. |
| `create_design_system` | Создать дизайн-систему. |
| `update_design_system` | Обновить. |
| `apply_design_system` | Применить к выбранным screen instances (`assetId` из list, инстансы из `get_project`). |

## Практический порядок

1. Нет `projectId` → `list_projects` или `create_project` → сохранить numeric **projectId** (без префикса `projects/`).
2. Генерация → `generate_screen_from_text` с `projectId`, `prompt`, при необходимости `deviceType` / `modelId`.
3. Подождать; при сбое соединения не спамить повтором — проверить `get_screen` / список экранов.
4. Дизайн-система: `list_design_systems` → при необходимости `apply_design_system` с ID из `get_project.screenInstances`.

## Ограничения

- Долгие операции: не считать зависанием; не делать параллельных дублей одной генерации.
- Итог для репозитория: по возможности дублировать ключевые токены/описание в markdown в `presentations/` или `app/docs/`, чтобы не зависеть только от облака Stitch.
- Ошибки квоты/ключа — зафиксировать в ответе пользователю, перейти на спеки без MCP.
