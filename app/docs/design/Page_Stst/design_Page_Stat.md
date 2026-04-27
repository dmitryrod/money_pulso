# Page Analytics Stat (detail)

## 1. Назначение страницы

Детальная аналитика одной **tracking session** скринера: мультисерийный график (score, фильтры PD/OI/LQ, фон — диапазон цены low–high за UTC‑минуту) и список **событий** из JSONL. Открывается с list-страницы Analytics по ссылке вида `/admin/analytics/stat-<symbol_slug>-<tracking_id>` (пример: `http://localhost:8000/admin/analytics/stat-roamusdt-61b7f31563ba4150929d` → символ **ROAMUSDT**, `tracking_id` **61b7f31563ba4150929d**).

Связанный list-spec: [Page Analytics](../Page_Analytics/design_Page_Analytics.md).

## 2. Использованные источники

| Источник | Путь |
|----------|------|
| Screenshot | [`../frontend/Page Stat.jpg`](../frontend/Page%20Stat.jpg) |
| Frontend template | `app/admin/templates/analytics_stat.html` |
| CSS/static | inline `<style>` в шаблоне; Chart.js `4.4.1` (cdn.jsdelivr) |
| Shared layout | `app/admin/templates/layout.html` |
| Route | `GET /admin/analytics/{page:path}` где `page` = `stat-<slug>-<tracking_id>` (регистрация в `app/admin/__init__.py`, handler `_admin_analytics_stat_subpage`) |
| Path parsing | `app/screener/scanner_runtime.py` — `parse_stat_page_path`: после префикса `stat-` **первый** `-` отделяет slug символа от `tracking_id` (id может содержать дефисы, как у UUID) |
| Data API | `GET /admin_api/analytics/samples?tracking_id=<id>` → `{ session, samples }`; `samples` — строки JSONL (`kind: sample` | `event` | `session_meta`) |

## 3. Общий layout

- Shell: тот же sidebar/topbar, что и у остальной админки (`layout.html`).
- Локально скрыты дефолтные `.page-title` и `.page-header` админки (`display: none`), чтобы не дублировать заголовок.
- Контент: колонка на всю ширину (`.stat-page.col-12`), вертикальный flex внутри `row-deck` (override `flex-direction: column` для совместимости с Tabler).
- График: **full-bleed** по viewport (`.stat-charts-fullbleed`: `width: 100vw`, отрицательные margin `calc(50% - 50vw)`).
- Viewport assumption для скриншота: desktop `approx. 1440x900` (оценка по кадру).

## 4. Иерархия блоков сверху вниз

1. Shell navigation (sidebar + topbar).
2. `.stat-page-head` — строка заголовка, мета сессии, чекбоксы, подсказка.
3. `.stat-charts-fullbleed` — панель графика (canvas) + панель «События».
4. `#stat-err` — текст ошибки (скрыт до fetch error).

## 5. Подробное описание блоков

### Head row

- **Title:** `Stat · {{ symbol_slug|upper }} · <code>{{ tracking_id }}</code>` — h1 `.stat-page-title`, `font-size: 1rem`, `color: #e0e6f0`, `margin: 0`.
- **Session line:** `#stat-session-line`, изначально «Загрузка…»; после успешного ответа API: `symbol · exchange · status` из `data.session`.
- **Toolbar:** `.stat-toolbar`, чекбоксы:
  - «Все тики» — без агрегации по минуте (иначе одна точка на UTC‑минуту = последний `sample`).
  - «Score 0–1» — линейная нормализация score по окну данных.
- **Hint:** `.stat-hint`, `font-size: 11px`, `color: #6677aa` — пояснение про 1 точку/мин и столбцы min/max цены за минуту.

### Chart panel

- Контейнер: `.stat-chart-box.stat-chart-box--graph` — `background: #1a1f2e`, границы `#2d3550`, **без** боковых границ у full-bleed (`border-left/right: none`), `border-radius: 0` для graph box.
- Подзаголовок h2: `font-size: 13px`, `color: #8899bb` — в коде: «Score + фильтры PD / OI / LQ · фон: цена low–high за минуту (USDT)» (на скриншоте заголовок может обрезаться визуально — источник текста: шаблон).
- Canvas wrap: `.stat-chart-canvas-wrap` — фиксированная высота **`500px`** (`max-height: 500px`), `overflow: hidden`.

**Chart.js datasets (факт из JS):**

| Серия | Тип | Ось | Цвет (border / fill) |
|-------|-----|-----|----------------------|
| цена low–high (за мин., USDT) | bar (floating `[low, high]`) | `yPrice` (right) | `rgba(38,198,218,0.22)` / `rgba(38,198,218,0.42)` |
| score (или norm.) | line | `y` (left, title «score») | `#5b9cf6` |
| PD `price_change_pct` | line | `y1` (right, «фильтры (текущие %)») | `#ff9800` |
| OI `change_pct` | line | `y1` | `#66bb6a` |
| LQ `lq_pct_of_daily_volume` | line | `y1` | `#ba68c8` |

Данные фильтров читаются из `sample.test_filters[]` по `id`: `pd`, `oi`, `lq`. Цена для столбцов: `sample.last_price`, иначе fallback `pd.current.final_price` (старые JSONL).

### Events panel

- Обёртка `.stat-events-wrap`, внутри `.stat-chart-box` с обычным radius `10px`.
- Список `#stat-events`: `ul.stat-events`, `max-height: 200px`, `overflow: auto`, элементы `ts — event`.

### Ошибки

- `#stat-err.stat-err`: `color: #e57373`; при 404 API — сообщение «Сессия не найдена».

## 6. Компоненты

- Checkboxes: подписи `.stat-toolbar label`, `font-size: 12px`, `color: #8899bb`.
- Chart: Chart.js `4.4.1`, легенда снизу, tooltips с форматом для bar как `low … high`.
- ResizeObserver на wrap для `chart.resize()`.

## 7. Контент и data states

- **Loading:** текст «Загрузка…» в session line; график пуст до ответа.
- **Success:** график и список событий заполнены; session line с метаданными.
- **Empty samples:** возможен пустой график / только оси — зависит от JSONL.
- **Error / 404:** видимый `#stat-err`, session line очищается.

## 8. Responsive notes

- Head row: `flex-wrap`, gap `8px 14px`; на узкой ширине подсказка и тулбар переносятся.
- Full-bleed график может требовать горизонтального внимания к легенде; canvas ограничен по высоте 500px.

## 9. Риски/неясности

- Имя каталога **`Page_Stst`** — зафиксировано в репозитории по договорённости пути; логическое имя страницы — **Analytics Stat**.
- Скриншот `Page Stat.jpg` с пробелом в имени; в ссылках использовать URL-encoding (`Page%20Stat.jpg`).
- Визуальная легенда/обрезка заголовка на скриншоте может отличаться от полного DOM — эталон формулировок: `analytics_stat.html`.

## 10. Google Stitch prompt

```text
Design a Binance/Bybit-inspired dark Analytics Stat detail page for Money Pulso admin: server-rendered Jinja page (not SPA) extending a left-sidebar shell. Hide default admin page header; show a compact head row: title "Stat · SYMBOL · tracking_id", session meta line "symbol · exchange · status", two checkboxes ("All ticks", "Score 0–1"), and a small muted hint about 1 point per UTC minute and price bars as min/max per minute. Below, a full-bleed dark chart panel (#1a1f2e, #2d3550 borders) with a 500px-tall Chart.js canvas. Chart: floating bars in teal for per-minute price low–high (USDT, right price axis); blue line for score on left axis; orange/green/purple lines on right axis for PD price_change_pct, OI change_pct, LQ lq_pct_of_daily_volume; bottom legend; muted grid; professional trading-terminal density. Under the chart, a second dark card titled "Events" with a scrollable list (max-height ~200px) of timestamped event lines. Error state: red inline message. Use #0b0e11 app feel, #e0e6f0 primary text, #8899bb labels, #6677aa hints.
```
