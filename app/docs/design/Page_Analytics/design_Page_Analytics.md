# Page Analytics

## 1. Назначение страницы

Страница аналитики показывает sessions/samples по работе scanner и ведёт к detail-графику `/admin/analytics/stat-<symbol_slug>-<tracking_id>` (см. отдельный spec [Analytics Stat (detail)](../Page_Stst/design_Page_Stat.md)). Это data table + chart workflow: сначала найти нужную сессию/символ, затем провалиться в график и оценить динамику.

## 2. Использованные источники

| Источник | Путь |
|----------|------|
| Screenshot | [`../frontend/Page Analitycs.jpg`](../frontend/Page%20Analitycs.jpg) |
| Frontend templates | `app/admin/templates/analytics.html` (detail: `analytics_stat.html` — [design_Page_Stat.md](../Page_Stst/design_Page_Stat.md)) |
| CSS/static | inline CSS в `analytics.html` |
| Shared layout | `app/admin/templates/layout.html` |
| Routes/API | `/admin/analytics`, `/admin_api/analytics/sessions`, purge endpoints; detail route и `samples` API — в [design_Page_Stat.md](../Page_Stst/design_Page_Stat.md) |

## 3. Общий layout

Viewport assumption: desktop `approx. 1440x900`. List page использует `.analytics-page` с padding `8px 16px 48px` и max-width `1200px`. Target layout сохраняет max-width для list, но визуально вписывает таблицу в тёмный exchange shell.

Структура:

- shared sidebar/topbar;
- `.analytics-page` внутри content area, vertical flow;
- toolbar row с filters/actions, gap `8px`;
- table wrapper full width до `1200px`;
- stat detail page: full-bleed chart page с chart box и canvas height `500px`.

Responsive: table получает horizontal scroll; toolbar wraps; chart canvas keeps min-width or responsive aspect ratio.

## 4. Иерархия блоков сверху вниз

1. Shell navigation.
2. Page title.
3. Toolbar: filters/search/selects, refresh/purge actions.
4. Sessions/samples table wrapper.
5. Pagination or load-more area if present.
6. Stat detail: chart header, chart box, canvas, legend/time controls.

## 5. Подробное описание блоков

### Page Container

Role: ограничить ширину и задать плотную data-page структуру.

- Current CSS: `.analytics-page { padding: 8px 16px 48px; max-width: 1200px; }`.
- Target background: transparent over app bg `#0b0e11`.
- Gap between blocks: `12px`.
- Typography: h1 `1.25rem`, color `#e0e6f0`.

### Toolbar

Role: фильтрация и сервисные действия.

- Layout: flex row, wrap, gap `8px`, align center.
- Inputs: current `#232a3e`, text `#c0ccdd`, border `#2d3550`, radius `6px`; сохранить.
- Purge/destructive: current bg `#3d2a2a`, text `#e8b4b4`, border `#6a4040`; сохранить как danger button.
- Primary/refresh target: `#f0b90b` for main action, `#232a3e` for secondary.
- Responsive: controls wrap into two rows; search grows `minmax(220px, 1fr)`.

### Analytics Table

Role: основной список sessions/samples.

- Wrapper: current radius `10`, border `#2d3550`; overflow hidden + horizontal scroll.
- Header: bg `#1a1f2e`, text `#8899bb`, font `12-13px`, sticky top inside scroll if feasible.
- Rows: bg `#0f141f` or transparent over wrapper; hover `#1e2538`.
- Links: current `#5b9cf6`, underline only on hover.
- Numeric cells: right aligned, tabular numbers.
- Density: row height `approx. 36-44px`; padding `8px 10px`.

### Status Pills

Role: показать lifecycle session/sample.

- Active: current bg `#2e4a2e`, text `#8fdf8f`.
- Done/neutral: current bg `#2d3550`, text `#aab8d0`.
- Other/error: current bg `#3d2a2a`, text `#e0a0a0`.
- Shape: radius `999px`, padding `3px 8px`, font `12px`.

### Stat Chart Header

Role: контекст конкретного symbol/tracking_id.

- Layout: title left, timeframe/action controls right.
- Background: optional toolbar `#1a1f2e`, radius `10`.
- Content: symbol, tracking id, last update, sample count.

### Chart Box

Role: full-bleed visual analytics.

- Current: chart box `#1a1f2e`, border `#2d3550`, radius `10`.
- Canvas: current height `500px`.
- Chart.js: `4.4.1`.
- Target: dark grid lines `rgba(136,153,187,.18)`, axes `#8899bb`, lines green/red/blue/yellow depending series, legend as compact pills.

## 6. Компоненты

- Buttons: refresh/filter secondary, purge danger, chart navigation secondary.
- Inputs/selects/forms: dark compact controls with focus blue.
- Tables: main component; shared dark table should be reused by Screeners.
- Cards: chart box and optional KPI summary cards.
- Charts/graphs: Chart.js time-series line/candlestick-like visual; canvas height `500px`.
- Badges/status labels: active/done/error pills.
- Filters/search: session filter, symbol search, tracking id, date/time range if available.
- Navigation: sidebar active item Analytics; detail page should include back link.

## 7. Контент и data states

- Empty: table wrapper contains empty card "No analytics sessions yet" + hint to run screeners.
- Populated: rows sorted by recent session/sample; links to stat detail visible.
- Error: inline panel above table with retry button; table preserved if stale data exists.
- Loading: skeleton rows in table and disabled toolbar.
- Purging: destructive button loading state; require clear visual progress after click.
- Chart empty: chart box shows centered empty state, not blank canvas.

## 8. Google Stitch prompt

```text
Design a Binance/Bybit-inspired dark Analytics page for Money Pulso admin. It is a server-rendered FastAPI/starlette-admin page, not a SPA. Use a compact dark shell with left sidebar and topbar, then a max-width 1200px analytics content area with h1, dense toolbar filters, refresh and purge actions, and a professional exchange-style data table. Use #0b0e11 background, #1a1f2e table headers and chart panels, #232a3e inputs, #2d3550 borders, #5b9cf6 links, #f0b90b primary accents, green/red/neutral status pills. Include a detail chart page with a 500px dark Chart.js canvas, muted grid, compact legend, timeframe controls, empty/loading/error states, and horizontal scrolling for wide tables.
```

## 9. Риски/неясности

- Screenshot filename contains typo `Page Analitycs.jpg`; documentation links to the actual file name.
- Набор колонок таблицы зависит от API payload; точные column widths нужно сверить в браузере.
- Detail chart может иметь несколько series; цветовая схема должна быть назначена после проверки фактических данных samples.
