# Design Documentation

Документ фиксирует текущее состояние frontend-админки Money Pulso и целевое направление редизайна для Google Stitch. Цель редизайна: сохранить серверный FastAPI admin UI на `starlette-admin` + Tabler + Jinja, но визуально привести интерфейс к плотной crypto-exchange эстетике Binance/Bybit: тёмная рабочая поверхность, высокий контраст данных, компактные таблицы, графики и статусные индикаторы.

## Текущее состояние

Frontend сейчас не SPA. Это FastAPI admin UI на `starlette-admin`, Tabler и Jinja-шаблонах. Общий shell задаётся в **`app/admin/templates/layout.html`** (полная копия структуры starlette-admin с `extends base.html`): collapsible sidebar toggle для ширины `>=992px`, регион **`main`**, мета-теги description/robots, подписи **aria** для кнопок/меню, **alt** у логотипа. Навигационные макросы — **`app/admin/templates/macros/views.html`** (переопределяют пакет через `ChoiceLoader`).

Основные маршруты:

| Страница | Route |
|----------|-------|
| Screeners | `/admin/screeners/list` |
| Add Screener | `/admin/screeners/create` |
| Signals | `/admin/signals` |
| Analytics | `/admin/analytics` |
| Analytics Stat | `/admin/analytics/stat-<symbol>-<tracking_id>` |
| System | `/admin/monitoring` |
| Logs | `/admin/logs` |

Основные API:

| API | Назначение |
|-----|------------|
| `/admin_api/screeners/global-debug` | массовое чтение/переключение debug mode |
| `/admin_api/screeners/global-debug.js` | JS для global debug switch |
| `/admin_api/signals` | список/снимок сигналов |
| `/admin_api/signals/stream` | stream обновлений сигналов |
| `/admin_api/analytics/sessions` | analytics sessions |
| `/admin_api/analytics/samples` | samples для аналитики |
| purge endpoints | очистка analytics/log-like данных в админке |

Текущие скриншоты показывают гибрид: тёмный левый sidebar, белый top header, светлые формы и системные карточки, отдельные тёмные страницы Analytics/Signals/Logs. Редизайн должен убрать визуальный разнобой и привести все страницы к единому trading terminal shell.

## Целевое направление

Ориентир: Binance/Bybit crypto exchange dashboard, но без копирования бренда. Интерфейс должен ощущаться как рабочий терминал для мониторинга рынка:

- тёмный фон приложения, плотные панели данных, минимум декоративных пустот;
- жёлтый/accent CTA для primary actions по аналогии с Binance, с синим secondary accent по аналогии с Bybit;
- таблицы как главный носитель информации: sticky header, компактные строки, чёткие numeric columns, hover state;
- графики на тёмной canvas-панели с приглушённой сеткой и яркими линиями;
- статусы через dot/badge/pill, а не длинный цветной текст;
- формы как конфигуратор стратегии: accordion sections, grouped filters, явные validation и enabled/disabled states;
- sidebar и topbar должны выглядеть частью одного trading shell, без белой верхней полосы.

## Design Tokens

### Цвета

| Token | Value | Применение |
|-------|-------|------------|
| `--mp-bg` | `#0b0e11` | общий фон приложения, Binance-like base |
| `--mp-surface` | `#1a1f2e` | карточки, toolbar, chart boxes |
| `--mp-surface-raised` | `#232a3e` | inputs, active table rows, secondary buttons |
| `--mp-surface-muted` | `#171c28` | вложенные блоки, scanner cards |
| `--mp-border` | `#2d3550` | основная граница панелей |
| `--mp-border-soft` | `rgba(255,255,255,.12)` | shell/sidebar border |
| `--mp-text` | `#e0e6f0` | основной текст |
| `--mp-text-muted` | `#8899bb` | headers, labels, secondary text |
| `--mp-text-soft` | `#aab8d0` | table body secondary text |
| `--mp-accent` | `#f0b90b` | primary CTA, market-highlight |
| `--mp-accent-blue` | `#5b9cf6` | links, secondary action, chart line |
| `--mp-success` | `#2fb344` | enabled/ok/active |
| `--mp-success-soft` | `#2e4a2e` | success pill background |
| `--mp-danger` | `#d63939` | disabled/fail/destructive |
| `--mp-danger-soft` | `#3d2a2a` | destructive/purge/error background |
| `--mp-warning` | `#ff9800` | reconnecting/warning |

Текущий sidebar уже близок к целевому shell: `background: rgba(26,31,46,.92)`, `border: rgba(255,255,255,.12)`, `color: #e0e6f0`, fixed offsets top/left `2.25rem`.

### Typography

- Базовый шрифт: Tabler/system sans-serif, без подключения новых зависимостей.
- Page title: `20px` / `1.25rem`, weight `600`, color `#e0e6f0`.
- Section title: `16-18px`, weight `600`.
- Table header: `12-13px`, uppercase optional, color `#8899bb`.
- Table body: `13px`, numeric values tabular if available.
- Logs/code: monospace `12.5px`, line-height `1.7`.

### Spacing

- Page padding: `8px 16px 48-80px` для dense admin pages.
- Panel padding: `10-16px` для toolbar/cards, `20-25px` только для marketing-like/summary cards.
- Grid gaps: `8px`, `10px`, `12px`, `20px`.
- Max width: analytics list `1200px`; metric/system cards `600px` currently, target can grow to `960px`.

### Radius, Borders, Shadows

- Inputs/buttons/filter blocks: radius `6-8px`.
- Tables/toolbars/chart boxes: radius `10px`.
- Large cards: radius `12-16px`.
- Border: `1px solid #2d3550`.
- Shadow: минимальный на тёмных страницах; для raised cards использовать soft shadow `0 12px 32px rgba(0,0,0,.24)`.

## Layout Shell

Базовый layout остаётся серверным. `layout.html` расширяет `@starlette-admin/layout.html` и должен быть источником общего shell:

- left sidebar: fixed/collapsible, dark translucent surface, border-right;
- top header: целевое состояние dark topbar, не white header;
- content area: scrollable main region с плотным page padding;
- breakpoint `>=992px`: sidebar toggle видим и работает;
- mobile/tablet: sidebar collapses over content, main content keeps horizontal scroll for wide tables/charts.

Целевой shell в Stitch: crypto admin terminal with persistent left nav, compact top market/status bar, dark surfaces, yellow primary accents, blue links, green/red signal states.

## Shared Components

### Cards

Использовать как контейнеры настроек, графиков и summary blocks. Target: `#1a1f2e`, border `#2d3550`, radius `10-12px`, padding `12-16px`. Light cards из Add Screener/System должны быть переведены в dark raised cards.

### Tables

Текущий Analytics table уже задаёт нужный паттерн: wrapper radius `10`, border `#2d3550`, header `#1a1f2e`, header text `#8899bb`, hover `#1e2538`, links `#5b9cf6`. Для Screeners нужен такой же exchange-style table вместо default admin table.

### Forms

Add Screener остаётся form-heavy page с accordion sections. Target: тёмные accordion cards, compact labels, dark inputs `#232a3e`, border `#2d3550`, focus ring через accent blue. Enabled/disabled status: green `#2fb344`, red `#d63939`.

### Charts

Analytics Stat использует Chart.js `4.4.1`. Chart container: `#1a1f2e`, border `#2d3550`, radius `10`, canvas height `500px`. Target: добавить exchange-like legend, timeframe controls, muted grid, bright green/red/blue series.

### Badges And States

- Active/ok: bg `#2e4a2e`, text `#8fdf8f`, dot `#4caf50`.
- Done/neutral: bg `#2d3550`, text `#aab8d0`.
- Error/fail/destructive: bg `#3d2a2a`, text `#e0a0a0`, dot `#f44336`.
- Warning/reconnecting: dot `#ff9800`.

### Empty, Loading, Error

Каждая data page должна иметь явные состояния:

- empty: тёмная empty card с short explanation и primary action;
- loading: skeleton rows/cards, без layout jump;
- error: inline error panel с retry action;
- stale/reconnecting: warning badge в toolbar, особенно Signals stream.

## Source Map

| Page | Screenshot | Template | Route/API |
|------|------------|----------|-----------|
| Add Screener | `app/docs/design/frontend/Page Add Screener.jpg` | `app/admin/templates/create_screener.html` | `/admin/screeners/create` |
| Analytics (list) | `app/docs/design/frontend/Page Analitycs.jpg` | `app/admin/templates/analytics.html` | `/admin/analytics`, `/admin_api/analytics/sessions`, purge endpoints |
| Analytics Stat (detail) | `app/docs/design/frontend/Page Stat.jpg` | `app/admin/templates/analytics_stat.html` | `/admin/analytics/stat-<symbol_slug>-<tracking_id>`, `/admin_api/analytics/samples` |
| Logs | `app/docs/design/frontend/Page Logs.jpg` | `app/admin/templates/logs.html` | `/admin/logs` |
| Screeners | `app/docs/design/frontend/Page Screeners.jpg` | starlette-admin list + `layout.html` + global debug JS | `/admin/screeners/list`, `/admin_api/screeners/global-debug(.js)` |
| Signals | `app/docs/design/frontend/Page Signals.jpg` | `app/admin/templates/signals.html` | `/admin/signals`, `/admin_api/signals`, `/admin_api/signals/stream` |
| System | `app/docs/design/frontend/Page Sistem.jpg` | `app/admin/templates/metr.html` | `/admin/monitoring` |

## Page Detail Files

- [Add Screener](design/Page_Add_Screener/design_Page_Add_Screener.md)
- [Analytics (list)](design/Page_Analytics/design_Page_Analytics.md)
- [Analytics Stat (detail chart)](design/Page_Stst/design_Page_Stat.md)
- [Logs](design/Page_Logs/design_Page_Logs.md)
- [Screeners](design/Page_Screeners/design_Page_Screeners.md)
- [Signals](design/Page_Signals/design_Page_Signals.md)
- [System](design/Page_System/design_Page_System.md)

## Global Google Stitch Direction Prompt

```text
Create a dark crypto-exchange admin dashboard redesign for Money Pulso, a FastAPI server-rendered admin UI using starlette-admin, Tabler, and Jinja templates, not a SPA. Use Binance/Bybit-inspired aesthetics without copying their branding: black #0b0e11 app background, raised dark panels #1a1f2e, inputs #232a3e, borders #2d3550, primary yellow accent #f0b90b, blue links #5b9cf6, green/red market status colors. Keep a collapsible left sidebar and compact topbar, dense data tables, chart panels, scanner feed cards, accordions for strategy configuration, terminal-style logs, clear empty/loading/error states, and responsive behavior for wide tables and charts. The UI should feel like a professional trading operations console for screeners, signals, analytics, logs, and system monitoring.
```

## Риски и неясности

- Часть визуальных размеров оценена как `approx.` по скриншотам; точные размеры нужно сверять в браузере.
- Для Screeners используется default admin table, поэтому часть detail spec описывает текущий вид по скриншоту и целевое приведение к shared table.
- Имена screenshot-файлов сохранены как есть: `Page Analitycs.jpg`, `Page Stat.jpg` (пробел в имени), `Page Sistem.jpg`; в документации используются правильные названия страниц Analytics/System.
- View path для отдельных Starlette Admin actions может быть неочевиден без чтения Python view-классов; в page specs указаны найденные/известные routes и templates.
