# Page Signals

## 1. Назначение страницы

Страница Signals показывает поток сигналов scanner feed: живые/последние события, результаты тестов фильтров, статусы stream connection и details по каждому сигналу. UX должен быть близок к market feed/trading terminal: плотные cards, мгновенная читаемость ok/fail, контроль reconnecting state.

## 2. Использованные источники

| Источник | Путь |
|----------|------|
| Screenshot | [`../frontend/Page Signals.jpg`](../frontend/Page%20Signals.jpg) |
| Frontend template | `app/admin/templates/signals.html` |
| CSS/static | inline CSS в template |
| Shared layout | `app/admin/templates/layout.html` |
| Routes/API | `/admin/signals`, `/admin_api/signals`, `/admin_api/signals/stream` |

## 3. Общий layout

Viewport assumption: desktop `approx. 1440x900`. Текущая страница уже наиболее близка к target dark terminal. `.signals-page` использует flex column, gap `12`, padding `8px 16px 80px`.

Структура:

- shell sidebar/topbar;
- `.signals-page` vertical stack;
- toolbar card;
- feed/list of signal/test cards;
- optional sticky connection status.

Responsive: при `<=1100px` test card меняется на two-column layout; на мобильном — one-column, details wrap.

## 4. Иерархия блоков сверху вниз

1. Shell navigation.
2. Signals toolbar with stream status and controls.
3. Filter/search/time range controls if present.
4. Signal/test card feed.
5. Empty/loading/error/reconnecting state.

## 5. Подробное описание блоков

### Signals Page Container

Role: vertical feed layout.

- Current: `.signals-page { display: flex; flex-direction: column; gap: 12px; padding: 8px 16px 80px; }`.
- Target: keep.
- Background: page `#0b0e11`.
- Max width: full content width, because feed cards benefit from horizontal space.

### Toolbar

Role: page controls and stream health.

- Current: bg `#1a1f2e`, radius `10`, padding `10px 14px`.
- Buttons: current `#232a3e`, active `#3a5bbf`; target active can remain blue or use yellow for primary mode.
- Layout: flex row, wrap, gap `8px`, align center.
- Status dot: green `#4caf50`, red `#f44336`, orange `#ff9800`.
- Typography: labels `13px`, muted text `#8899bb`, active text `#e0e6f0`.

### Signal/Test Card

Role: one signal or scanner test result with structured fields.

- Current grid: columns `170px 250px minmax(0,1fr)`, gap `8px 10px`.
- Current responsive: `<=1100px` changes to two columns.
- Radius: current `12px`.
- Background: dark gradient blocks `#1e2538` to `#171c28`.
- Target border: `1px solid #2d3550`.
- Padding: `10-14px`.
- Hover: subtle border `#3a5bbf` or bg lift.

### Card Column 1: Identity/Time

Role: symbol, exchange, timestamp, direction.

- Width: current `170px`.
- Typography: symbol `15-16px`, weight `600`, color `#e0e6f0`.
- Secondary: exchange/market/time `12-13px`, color `#8899bb`.
- Direction/status: green/red badge depending signal.

### Card Column 2: Summary

Role: price/volume/key metrics summary.

- Width: current `250px`.
- Numeric values: tabular, color accent for important deltas.
- Positive/ok: `#4caf50`; negative/fail: `#e57373`.
- Use compact metric rows with label left and value right.

### Card Column 3: Filter Blocks

Role: detailed pass/fail breakdown.

- Layout: grid/list of filter blocks.
- Current filter blocks: radius `6`, border `#2f3a52`.
- Background: `#171c28` or `#1e2538`.
- OK: current `#4caf50`.
- Fail: current `#e57373`.
- Text: `12-13px`, muted labels.
- Target: each block has status dot/icon, threshold, actual value.

### Stream State Banner

Role: SSE/websocket-like `/admin_api/signals/stream` connection state.

- Connected: green dot + "Live".
- Reconnecting: orange dot + "Reconnecting".
- Disconnected/error: red dot + retry button.
- Position: toolbar right or sticky top within page.

## 6. Компоненты

- Buttons: pause/live, clear, refresh, filters; active button current `#3a5bbf`, primary target `#f0b90b`.
- Inputs/selects/forms: optional symbol/search filter, dark input tokens.
- Tables: нет; feed cards replace table.
- Cards: signal/test card and nested filter blocks.
- Charts/graphs: нет on this page; mini sparklines could be target-only if data exists.
- Badges/status labels: stream dot, ok/fail labels, direction badges, exchange/market chips.
- Filters/search: symbol, status, screener, exchange, time window.
- Navigation: sidebar active item Signals.

## 7. Контент и data states

- Empty: "No signals yet" card with hint to enable screeners.
- Populated: newest signals first; cards use consistent height where possible.
- Error: stream/API failure banner, keep last known cards stale-labeled.
- Loading: skeleton toolbar stats + skeleton cards.
- Reconnecting: orange stream status, disable destructive actions only if needed.
- High volume: virtualized/incremental rendering is implementation concern; visually keep feed dense and scrollable.

## 8. Google Stitch prompt

```text
Design a dark live Signals feed page for Money Pulso admin, inspired by Binance/Bybit market scanners. This is a FastAPI/starlette-admin server-rendered UI using /admin_api/signals and /admin_api/signals/stream, not a SPA. Keep a dark left sidebar and compact topbar, then a full-width signals feed with padding 8px 16px 80px and 12px vertical gaps. Add a raised toolbar #1a1f2e with live/reconnecting/disconnected status dots, filters, refresh and active buttons. Build dense signal cards using a 170px / 250px / flexible grid, dark gradients #1e2538 to #171c28, 12px radius, #2d3550 borders, nested filter blocks with #2f3a52 borders, green ok #4caf50 and red fail #e57373. Include responsive two-column behavior below 1100px, empty/loading/error/reconnecting states, and a professional crypto operations console feel.
```

## 9. Риски/неясности

- `/admin_api/signals/stream` может быть SSE or another streaming mechanism; визуально важен connection state, но exact transport не фиксируется.
- Неясно, есть ли client-side filtering сейчас; prompt допускает filters as target controls.
- При очень большом потоке карточек может понадобиться pagination/windowing, но это не часть документационного изменения.
