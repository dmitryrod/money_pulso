# Page Add Screener

## 1. Назначение страницы

Страница создания скринера: пользователь задаёт биржу, рынок, список инструментов, фильтры pump/dump, OI, funding, volume, liquidations, daily volume, daily price change и Telegram-уведомления. Это конфигуратор стратегии, поэтому главный UX-приоритет — быстро понять, какие фильтры включены, какие поля обязательны и почему скринер готов/не готов к запуску.

## 2. Использованные источники

| Источник | Путь |
|----------|------|
| Screenshot | [`../frontend/Page Add Screener.jpg`](../frontend/Page%20Add%20Screener.jpg) |
| Frontend template | `app/admin/templates/create_screener.html` |
| CSS/static | inline CSS в template + Tabler/Bootstrap классы через Starlette Admin |
| Shared layout | `app/admin/templates/layout.html` extends `@starlette-admin/layout.html` |
| Route/view | `GET /admin/screeners/create` (создание `SettingsModelView`, шаблон `create_screener.html`) |

## 3. Общий layout

Viewport assumption: desktop `approx. 1440x900`. Текущий скриншот показывает тёмный левый sidebar, белый top header и светлую form/card область. Целевое состояние: единый dark trading shell с left sidebar, dark topbar и form canvas на `#0b0e11`.

Структура:

- fixed/collapsible sidebar слева, top/left offsets из shared layout `2.25rem`, background `rgba(26,31,46,.92)`, border `rgba(255,255,255,.12)`;
- top header над content area, в redesign должен стать dark и компактным;
- content area scrolls vertically, form width `approx. 960-1180px`, centered или aligned left with `16px` page padding;
- accordion sections stack vertically; long form scrolls, sidebar remains visible.

Responsive: при ширине `<992px` sidebar collapses; accordion занимает всю ширину; multi-column form rows должны превращаться в one-column stack.

## 4. Иерархия блоков сверху вниз

1. Shell: sidebar navigation + topbar.
2. Page header: title "Add Screener"/"Create Screener", optional status badge.
3. Main form card.
4. Accordion section: General settings.
5. Accordion sections: pump/dump, OI, funding, volume, liquidations, daily volume, daily price change.
6. Accordion section: notifications.
7. Sticky or bottom action row: save/cancel.

## 5. Подробное описание блоков

### Shell

Role: постоянная навигация админки. Текущий sidebar уже dark; top header сейчас визуально светлый и конфликтует с crypto aesthetic.

- Position: sidebar fixed left, content shifted right; topbar fixed/relative above content.
- Background: sidebar `rgba(26,31,46,.92)`, target topbar `#1a1f2e`.
- Border: `rgba(255,255,255,.12)` для shell, `#2d3550` для content panels.
- Typography: nav labels `13-14px`, color `#e0e6f0`, muted icons `#8899bb`.
- State: active nav item через dark raised bg `#232a3e` и accent strip `#f0b90b`.

### Page Header

Role: контекст создания и быстрый health state формы.

- Position: first content block, margin-bottom `12-16px`.
- Layout: title left, optional badge/right helper text.
- Typography: h1 `1.25rem`, `600`, color `#e0e6f0`.
- Target badge: `Ready` green `#2fb344` или `Incomplete` red `#d63939`, radius `999px`, padding `4px 8px`.

### Main Form Card

Role: контейнер формы. Сейчас Bootstrap/Tabler card выглядит светлой; target должен быть dark raised panel.

- Size: width `100%`, max-width `approx. 1180px`.
- Padding: `12-16px` around accordion.
- Background: target `#1a1f2e`.
- Border/radius: `1px solid #2d3550`, radius `10-12px`.
- Shadow: `0 12px 32px rgba(0,0,0,.24)` only if needed.

### Accordion Sections

Role: группировка фильтров и снижение cognitive load.

- Title: текущий `1.1rem`; сохранить размер, сделать weight `600`.
- Header background: target `#232a3e`, hover `#2a334d`.
- Body background: `#1a1f2e`.
- Gap: `8-10px` between accordion items.
- Radius: `8-10px`.
- Border: `#2d3550`.
- States: collapsed, expanded, invalid. Invalid section gets red left border `#d63939`; enabled section gets yellow/blue marker.

### General Settings

Role: обязательная идентификация скринера и базовые market settings.

- Fields: name, exchange, market type, symbol include/exclude, enabled/debug flags if present.
- Layout: target two-column grid on desktop, one-column mobile.
- Labels: `12-13px`, uppercase optional, color `#8899bb`.
- Inputs: `#232a3e`, text `#c0ccdd`, border `#2d3550`, radius `6px`, height `34-38px`.

### Filter Sections

Role: настройка условий сигнала. Pump/dump, OI, funding, volume, liquidations, daily volume, daily price change должны выглядеть как повторяемые filter modules.

- Layout: compact rows with threshold, interval, direction/operator, enabled toggle.
- Background for nested filter block: `#171c28`.
- Border: `#2f3a52`.
- Gap: `8px`.
- Validation: missing required values show inline text `#e0a0a0` and red border.
- Disabled: opacity `0.55`, no bright accent.

### Notifications

Role: Telegram delivery settings and signal destination.

- Fields: bot token placeholder, chat id, notification toggles.
- Security: реальные токены не показывать; masked values if already configured.
- Target visual: warning/info helper block for rate limits, background `#3d2a2a` or `#2d3550` depending severity.

### Action Row

Role: submit/cancel. На длинной форме лучше sticky bottom within content.

- Primary button: `#f0b90b`, text `#0b0e11`, radius `8px`, height `36-40px`.
- Secondary: `#232a3e`, text `#e0e6f0`, border `#2d3550`.
- Danger/reset: `#3d2a2a`, text `#e8b4b4`, border `#6a4040`.

## 6. Компоненты

- Buttons: primary save, secondary cancel/back, optional destructive reset; hover brightness `+8%`.
- Inputs/selects/forms: dark inputs, compact height, focus border `#5b9cf6`, focus shadow `rgba(91,156,246,.18)`.
- Tables: not primary for this page; if symbol preview appears, use shared dark table.
- Cards: main form card + nested filter cards.
- Charts/graphs: нет.
- Badges/status labels: enabled green `#2fb344`, disabled red `#d63939`, incomplete red soft pill.
- Filters/search: symbol include/exclude fields can use token/chip style.
- Navigation: shared sidebar/topbar, active item Screeners.

## 7. Контент и data states

- Empty/new: all fields blank, General settings expanded, first required field focused.
- Populated: completed sections show compact summary in accordion header, e.g. `Volume > 2.5x / 5m`.
- Error: validation errors inline under fields, section header marked red.
- Loading: on submit, primary button disabled with spinner; no full-page blocking unless save creates background task.
- Success: redirect/list or success toast; badge turns green before navigation if staying on page.

## 8. Google Stitch prompt

```text
Design a dark crypto-exchange style "Add Screener" configuration page for Money Pulso, a server-rendered FastAPI/starlette-admin admin UI. Keep a left dark sidebar and compact dark topbar, then create a dense strategy form in a raised panel. Use accordion sections for General settings, pump/dump, open interest, funding, volume, liquidations, daily volume, daily price change, and Telegram notifications. Make it feel like Binance/Bybit strategy setup: black #0b0e11 background, panels #1a1f2e, inputs #232a3e, borders #2d3550, yellow primary save button #f0b90b, blue focus states #5b9cf6, green enabled badges and red invalid badges. Include responsive one-column mobile behavior, sticky action row, validation states, and compact section summaries.
```

## 9. Риски/неясности

- Точная форма генерируется Starlette Admin model form, поэтому набор полей может отличаться от визуального порядка в screenshot.
- Текущий screenshot светлый; часть целевых цветов — redesign direction, а не фактическое состояние.
- Необходимо проверить, можно ли сделать sticky action row без конфликта с `@starlette-admin/layout.html`.
