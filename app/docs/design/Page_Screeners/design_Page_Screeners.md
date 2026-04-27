# Page Screeners

## 1. Назначение страницы

Страница Screeners показывает список настроенных скринеров, даёт вход в создание Add Screener и управляет global debug switch. Это operational table: оператор должен быстро увидеть включённые стратегии, их рынок/биржу, состояние, параметры и перейти к редактированию.

## 2. Использованные источники

| Источник | Путь |
|----------|------|
| Screenshot | [`../frontend/Page Screeners.jpg`](../frontend/Page%20Screeners.jpg) |
| Frontend template | Starlette Admin list view + `app/admin/templates/layout.html` |
| CSS/static | Tabler/starlette-admin default styles + `/admin_api/screeners/global-debug.js` |
| Shared layout | `app/admin/templates/layout.html` |
| Routes/API | `/admin/screeners/list`, `/admin_api/screeners/global-debug`, `/admin_api/screeners/global-debug.js` |

## 3. Общий layout

Viewport assumption: desktop `approx. 1440x900`. Текущий screenshot показывает default admin table с dark sidebar, light header, button Add Screener и global debug switch. Цель — привести list page к тому же dark table паттерну, что Analytics.

Структура:

- shared sidebar/topbar shell;
- page header/action row;
- debug control strip;
- screeners table;
- pagination/bulk actions if present.

Responsive: wide table scrolls horizontally; actions collapse into icon/overflow menu; debug switch remains visible near title.

## 4. Иерархия блоков сверху вниз

1. Shell navigation.
2. Page title "Screeners" and primary action "Add Screener".
3. Global debug switch/status.
4. Filters/search area from Starlette Admin if enabled.
5. Screeners table.
6. Pagination/bulk action footer.

## 5. Подробное описание блоков

### Page Header

Role: list context and create action.

- Layout: flex row, title left, Add Screener button right.
- Title: `1.25rem`, weight `600`, color target `#e0e6f0`.
- Primary button: target yellow `#f0b90b`, text `#0b0e11`, radius `8px`, height `36-40px`.
- Secondary actions: dark `#232a3e`, border `#2d3550`.

### Global Debug Strip

Role: массовое включение/выключение debug mode across screeners.

- Source: `/admin_api/screeners/global-debug(.js)`.
- Position: immediately below header or inline right of title if compact.
- Background: target `#1a1f2e`.
- Border/radius: `#2d3550`, radius `10px`.
- Content: label, switch, status text, optional "applies to all screeners" hint.
- States: on green `#2fb344`; off neutral `#2d3550`; loading spinner; error red soft panel.

### Filters/Search

Role: найти скринер по name/exchange/market/status.

- Current: Starlette Admin default if present.
- Target: dark inputs `#232a3e`, text `#c0ccdd`, border `#2d3550`, radius `6px`.
- Layout: row wrap gap `8px`.

### Screeners Table

Role: main list.

- Target wrapper: radius `10`, border `#2d3550`, overflow auto.
- Header: `#1a1f2e`, text `#8899bb`, compact uppercase optional.
- Body: rows `#0f141f`, hover `#1e2538`.
- Columns: name, exchange, market, status/enabled, filters summary, notifications, debug, actions.
- Numeric/config summary: use small chips rather than long raw values.
- Row height: `approx. 40-48px`.
- Actions: edit/delete/view as compact icon buttons, not large default buttons.

### Status And Filter Summary

Role: make strategy state scannable.

- Enabled: green pill/dot `#2fb344`.
- Disabled: red/neutral pill `#d63939` or `#2d3550`.
- Debug on: warning/yellow `#f0b90b` or orange `#ff9800`.
- Filter chips: dark raised bg `#232a3e`, border `#2d3550`, text `#aab8d0`.

### Footer/Pagination

Role: navigate long list.

- Background: same table wrapper or transparent.
- Buttons: compact dark secondary.
- Text: muted `#8899bb`.

## 6. Компоненты

- Buttons: Add Screener primary, row action buttons secondary/danger.
- Inputs/selects/forms: search and filters in dark style.
- Tables: main component; should reuse Analytics table tokens.
- Cards: debug strip as compact card.
- Charts/graphs: нет.
- Badges/status labels: enabled/disabled/debug/filter chips.
- Filters/search: name/exchange/market/status.
- Navigation: sidebar active item Screeners.

## 7. Контент и data states

- Empty: no screeners; show empty table card with primary Add Screener CTA.
- Populated: compact rows; active screeners visually stand out.
- Error: table load/API debug switch error shown inline; keep list if already rendered.
- Loading: skeleton rows; global debug switch disabled while request pending.
- Bulk debug update: optimistic state only if API confirms; otherwise revert and show error.

## 8. Google Stitch prompt

```text
Design a dark crypto-exchange Screeners list page for Money Pulso admin. It is a FastAPI/starlette-admin server-rendered list view, not a SPA. Use a Binance/Bybit-inspired shell with dark left sidebar and compact topbar. Create a page header with "Screeners" and a yellow #f0b90b Add Screener primary button, a raised global debug switch panel powered by /admin_api/screeners/global-debug, and a dense dark table for screener strategies. Use #0b0e11 background, #1a1f2e table headers and panels, #232a3e filters/chips, #2d3550 borders, #5b9cf6 links, green enabled pills, red disabled/error pills, orange/yellow debug indicators. Include search/filter controls, row action buttons, empty/loading/error states, and horizontal scrolling for wide admin columns.
```

## 9. Риски/неясности

- Страница частично генерируется Starlette Admin, поэтому точный DOM/columns могут зависеть от model view configuration.
- Global debug JS подключается отдельно; visual spec должен учитывать async loading/error switch state.
- Нужна проверка, насколько глубоко можно переоформить default admin table без fork `starlette-admin` templates.
