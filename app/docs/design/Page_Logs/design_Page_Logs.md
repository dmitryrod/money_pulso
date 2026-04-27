# Page Logs

## 1. Назначение страницы

Страница логов даёт оператору быстрый просмотр runtime-событий, ошибок, warning и signal-related сообщений. Это terminal-like page: важны читаемость, поиск/фильтрация, стабильный scroll и цветовое кодирование уровней.

## 2. Использованные источники

| Источник | Путь |
|----------|------|
| Screenshot | [`../frontend/Page Logs.jpg`](../frontend/Page%20Logs.jpg) |
| Frontend template | `app/admin/templates/logs.html` |
| CSS/static | inline CSS в template |
| Shared layout | `app/admin/templates/layout.html` |
| Route/view | `/admin/logs` |

## 3. Общий layout

Viewport assumption: desktop `approx. 1440x900`. Текущая страница уже имеет black terminal block внутри admin shell. Целевой redesign должен сделать toolbar тоже dark, чтобы не было конфликта со светлым admin header.

Структура:

- sidebar/topbar shell;
- page content with toolbar at top;
- log container below, full width, max-height `75vh`;
- vertical scrolling внутри log container, page scroll only for overflow around it.

Responsive: toolbar controls wrap; log container keeps monospace and horizontal scroll for long lines.

## 4. Иерархия блоков сверху вниз

1. Shell navigation.
2. Toolbar title and controls.
3. Optional status row: file/source, last update, auto-refresh state.
4. Log terminal container.
5. Bottom helper/pagination/tail controls if present.

## 5. Подробное описание блоков

### Toolbar

Role: выбрать источник/уровень логов, выполнить поиск или refresh.

- Current title color: `#2d3436`; target should become `#e0e6f0`.
- Inputs: current border `#dee2e6`, radius `8`, focus `#74b9ff`, shadow `rgba(116,185,255,.2)`; target dark input `#232a3e`, border `#2d3550`, focus same blue.
- Button: current `#0984e3`, hover `#074b8a`, radius `8`; target secondary blue or yellow primary for refresh.
- Layout: flex row, gap `8-10px`, align center, wrap on small width.
- Padding: `10-14px`, background target `#1a1f2e`, border `#2d3550`, radius `10px`.

### Source/Status Row

Role: показать, какой файл/stream читается и насколько данные свежие.

- Position: under toolbar or inside right toolbar segment.
- Typography: `12-13px`, muted `#8899bb`.
- States: live green dot `#4caf50`, paused/warning orange `#ff9800`, error red `#f44336`.

### Log Container

Role: основной terminal viewport.

- Current background: `#1e1e1e`.
- Current text: `#d4d4d4`.
- Current radius: `12px`.
- Current padding: `20px`.
- Current font: monospace `12.5px`, line-height `1.7`.
- Current max-height: `75vh`.
- Target: keep terminal black but align with shell: background `#0d1117` or `#111827`, border `#2d3550`, subtle inner shadow.
- Scroll: vertical auto; horizontal auto or wrap mode toggle.

### Log Lines

Role: readable event stream.

- Base: timestamp muted `#8899bb`, message `#d4d4d4`.
- Info: current `#74b9ff`.
- Warning: current `#fdcb6e`.
- Error: current `#ff7675`.
- Success: current `#55efc4`.
- Target: keep these colors; they fit dark terminal and crypto monitoring.
- Hover: optional line bg `rgba(255,255,255,.04)`.

### Empty/Error Overlay

Role: avoid blank black box.

- Empty: centered muted text and "Refresh logs" action.
- Error: red soft panel `#3d2a2a`, text `#e0a0a0`, retry button.
- Loading: terminal skeleton with dim grey bars.

## 6. Компоненты

- Buttons: refresh, clear filter, tail/live toggle; primary can be `#f0b90b`, secondary `#232a3e`.
- Inputs/selects/forms: search input, level select, source select.
- Tables: нет.
- Cards: toolbar card + terminal card.
- Charts/graphs: нет.
- Badges/status labels: live/paused/error dot; log level labels optional.
- Filters/search: level, text search, source/log file; matches highlighted with yellow soft background.
- Navigation: sidebar active item Logs.

## 7. Контент и data states

- Empty: log file exists but no matching lines; show "No log entries match current filters".
- Populated: latest lines visible, optionally auto-scroll to bottom.
- Error: cannot read logs; show cause and retry.
- Loading: toolbar disabled, terminal shows loading rows.
- Long lines: preserve monospace; allow horizontal scroll to avoid destroying stack traces.

## 8. Google Stitch prompt

```text
Design a dark terminal-style Logs page for Money Pulso admin, inspired by crypto exchange operations consoles. Keep the FastAPI/starlette-admin server-rendered shell with left sidebar and compact dark topbar. Create a dark toolbar with title, log source selector, level filter, search input, refresh and live-tail controls. Below it, place a large black terminal panel with #1e1e1e/#0d1117 background, #2d3550 border, 12px radius, 20px padding, monospace 12.5px text, max-height around 75vh, vertical and horizontal scrolling. Use blue info #74b9ff, yellow warning #fdcb6e, red error #ff7675, mint success #55efc4, muted timestamps, live status dots, empty/loading/error states, and Binance/Bybit-like dark surfaces and compact spacing.
```

## 9. Риски/неясности

- Не указано, есть ли live streaming логов или только refresh; prompt допускает live-tail как визуальный target, но реализация может остаться manual refresh.
- Текущие toolbar colors светлые; redesign должен изменить их без изменения backend route.
- Для stack traces нужно решить: wrap или horizontal scroll. Для operator UI предпочтительнее horizontal scroll + copy action.
