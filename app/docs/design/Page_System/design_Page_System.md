# Page System

## 1. Назначение страницы

Страница System/Monitoring показывает системные метрики в виде карточек: состояние процессов, ресурсов или внутренних counters. Текущее состояние похоже на light metric cards; целевой redesign должен сделать её тёмной status overview page в стиле exchange operations dashboard.

## 2. Использованные источники

| Источник | Путь |
|----------|------|
| Screenshot | [`../frontend/Page Sistem.jpg`](../frontend/Page%20Sistem.jpg) |
| Frontend template | `app/admin/templates/metr.html` |
| CSS/static | inline CSS в template |
| Shared layout | `app/admin/templates/layout.html` |
| Route/view | `/admin/monitoring` |

## 3. Общий layout

Viewport assumption: desktop `approx. 1440x900`. Current template uses `.metric-container` with max-width `600px`, margin `30px auto`, gap `20px`. Screenshot shows centered light metric cards in admin shell.

Target:

- keep centered summary layout for simple system view;
- optionally expand max-width to `960px` for 2-column metric cards;
- dark shell and dark metric cards;
- cards scroll vertically if many metrics.

Responsive: desktop two columns if enough metrics; mobile one column.

## 4. Иерархия блоков сверху вниз

1. Shell navigation.
2. Page title/status summary.
3. Metric card grid/container.
4. Individual metric cards with value, label, progress bar and state.
5. Optional last-updated/reload control.

## 5. Подробное описание блоков

### Metric Container

Role: centralize system status and avoid full-width sparse layout.

- Current: max-width `600px`, margin `30px auto`, gap `20px`.
- Target: max-width `600px` for 1-column or `960px` for 2-column grid.
- Layout: grid/flex column, gap `16-20px`.
- Page padding: `8px 16px 48px`.

### Metric Card

Role: show one system metric.

- Current: padding `25px`, gradient `#fff -> #f8f9fa`, radius `16`, shadow, hover `translateY(-2px)`.
- Target: background gradient `#1a1f2e -> #171c28`, border `#2d3550`, radius `16`, shadow `0 12px 32px rgba(0,0,0,.24)`.
- Padding: keep `20-25px`.
- Hover: `translateY(-2px)` can remain, with border highlight `#3a5bbf`.

### Metric Value

Role: primary number/state.

- Current value size: `32px`.
- Target: keep `32px`, weight `700`, color `#e0e6f0`.
- Positive/healthy: green `#2fb344`.
- Warning: yellow/orange `#fdcb6e` or `#ff9800`.
- Danger: red `#d63939`.
- Secondary label: `13-14px`, color `#8899bb`.

### Progress Bars

Role: show resource usage/health percentage.

- Current height: `6px`.
- Current gradients:
  - normal `#74b9ff -> #0984e3`;
  - warning `#ffeaa7 -> #fdcb6e`;
  - danger `#ff7675 -> #d63031`.
- Target: keep height `6px`, radius `999px`, track `#232a3e`.
- Place value/percentage near bar for scanability.

### Last Updated / Refresh

Role: reassure operator about freshness.

- Position: below title or above cards.
- Text: muted `#8899bb`, `12-13px`.
- Button: secondary dark; primary refresh can use yellow `#f0b90b`.

## 6. Компоненты

- Buttons: refresh/reload; optional details link.
- Inputs/selects/forms: нет unless time range is added.
- Tables: нет.
- Cards: main metric cards.
- Charts/graphs: progress bars, optional mini trend sparkline as target-only if data exists.
- Badges/status labels: healthy/warning/danger badges or dots.
- Filters/search: нет.
- Navigation: sidebar active item System/Monitoring.

## 7. Контент и data states

- Empty: no metrics available; show centered empty card with refresh.
- Populated: cards sorted by severity first or stable logical order.
- Error: red soft card with reason and retry.
- Loading: skeleton metric cards preserving layout.
- Stale: warning badge "stale" with last successful update timestamp.

## 8. Google Stitch prompt

```text
Design a dark System Monitoring page for Money Pulso admin, inspired by Binance/Bybit operations dashboards. It is a server-rendered FastAPI/starlette-admin page, not a SPA. Keep the left dark sidebar and compact topbar. Create a centered metric dashboard using a max-width 600px single-column layout or 960px responsive two-column grid. Use dark metric cards with #1a1f2e to #171c28 gradient, #2d3550 borders, 16px radius, 20-25px padding, subtle shadow, and hover lift. Show 32px metric values, muted labels, healthy/warning/danger badges, 6px progress bars with blue, yellow, and red gradients, last updated text, refresh action, and empty/loading/error/stale states. The page should feel like a compact crypto exchange system health console.
```

## 9. Риски/неясности

- Screenshot filename contains typo `Page Sistem.jpg`; documentation links to the actual file name.
- Набор метрик не зафиксирован в запросе; spec описывает визуальный контейнер и states, не конкретную telemetry schema.
- Если System page останется только с несколькими cards, слишком широкий 2-column layout может выглядеть пусто; `600px` single-column безопаснее.
