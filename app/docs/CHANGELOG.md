# Changelog

Формат: версия приложения (как в `pyproject.toml`) и кратко — что изменилось для оператора/пользователя. Отсчёт ведётся с **1.3.x**; более ранние версии здесь не фиксируются.

## [1.5.0] — в разработке

### Документация

- **Демо для публики / сессии:** в **`app/README.MD`** — блок про публичный sandbox (`ADMIN_DEMO_ENABLED`, плейсхолдеры из `.env.example`), предупреждение о общих кредах; уточнено в **`app/docs/README.md`** и **`app/docs/ARCHITECTURE.md`**: сессия Starlette — подписанная cookie (не общий server-side map по username), параллельные браузеры с одной парой demo допустимы; при нескольких инстансах важен **одинаковый `CYPHER_KEY`**. **`app/docs/troubleshooting.md`** — карточка про «вылет» при разных ключах на репликах.

### Исправлено

- **Конфиг / Telegram (env):** некорректные **`TELEGRAM_CHAT_ID`** (не целое, префикс **`#`**, пробелы) и **`TELEGRAM_BOT_TOKEN`**, начинающийся с **`#`**, больше не вызывают **`ValueError` при импорте** — трактуются как «не задано» (**`WARNING`** в лог); стартуют Alembic и Uvicorn. Скринер без пары токен+chat по-прежнему работает, отправка в Telegram отключается (**`app/config/config.py`**: **`parse_optional_telegram_chat_id`**, **`parse_optional_telegram_bot_token`**), тесты **`tests/test_configuration_telegram_env.py`**. Уточнены комментарии в **`app/.env.example`**; карточка в **`app/docs/troubleshooting.md`**.

- **Админка / список скринеров (`/admin/screeners/list`):** main-тулбар DataTables в **`#btn_container`** (Экспорт, видимость столбцов, конструктор поиска) на desktop снова в **одну горизонтальную строку** (`flex-wrap: nowrap !important`), а на ширине ≤768px переносит кнопки в несколько строк без горизонтального скролла. Кнопка **«Добавить скринер»** остаётся справа в **`card-header`**; блок **«Глобальный режим отладки»** размещается рядом/ниже и не сдвигает create button от правого края. **`layout.html`**, **`app/admin/__init__.py`**.

- **Админка / topbar (мобильная вёрстка):** в **`app/admin/templates/layout.html`** удалены второй **`navbar-toggler`** (**`data-bs-target="#navbar-menu"`**) и пустой **`#navbar-menu`**; гамбургер для навигации — только в **`aside.navbar.navbar-vertical`** (**`#sidebar-menu`**). См. также историческую запись про перенос **`#navbar-menu`** в **`CHANGELOG`** (блок за 2026-04-28) — поведение заменено на отсутствие дублей.

- **Админка / Сигналы (мобильная навигация):** на странице **`/admin/signals`** убран CSS, скрывавший **`aside.navbar.navbar-vertical`** при ширине ≤600px — восстановлен тот же chrome, что на **`/admin/settings`** (гамбургер открывает **`#sidebar-menu`**). Шаблон: **`signals.html`**.

- **SSE / Signals:** **`ProductionAssetCacheMiddleware`** переведён с `BaseHTTPMiddleware` на прямой ASGI-обработчик заголовков `http.response.start` — исправляет ``RuntimeError: No response returned`` при потоковом **`GET /admin_api/signals/stream`** (старое поведение TaskGroup/async в BaseHTTPMiddleware + `StreamingResponse`).

### Изменено

- **Админка / Скринеры — demo и приватность:** при сессии с ролью **`demo`** в списке и деталях видна только запись с именем **`demo`** (константа **`DEMO_SCREENER_NAME`** в **`app/admin/roles.py`**); прямой URL к чужому PK не открывает строку. Колонки **ID Telegram чата** и **токен бота** в таблице, деталях и API-сериализации starlette-admin (**`API` / `LIST` / `DETAIL`**) маскируются для **всех** ролей (первые и последние 4 символа, середина **`****`**); в формах **создания и редактирования** значения без маски. **`SettingsModelView`** (`get_list_query`, `get_count_query`, `get_details_query`, `serialize_field_value`), **`app/admin/privacy_mask.py`**, тесты **`tests/test_admin_screener_privacy.py`**.

- **Админка / Сигналы (`/admin/signals`):** нативные подсказки при наведении (`title`) на ранг CoinMarketCap, Score (средний вклад по фильтрам), название скринера, биржу и тип рынка (раздельно), время запуска скринера и длительность отслеживания на test-карточках Scanner; на узких карточках — подсказки для биржи/рынка и времени сигнала. **`signals.html`**.

- **Админка / Scanner (test-карточки на `/admin/signals`):** кнопка **«Закрепить»** (`.sct-btn-lock`) в одной строке со ссылкой **«График»** (`.sct-id-stat` / `.btn-analytics-chart`), справа от графика; обёртка **`.sct-stat-row`**; высота замка выровнена с **«Графиком»** (те же `padding` / `line-height` / `border-radius`, что у `.btn-analytics-chart`). **`signals.html`**.

- **CoinMarketCap rank cache:** инициализация перенесена из импорта модуля в **`lifespan`** FastAPI (`app/__main__.py`), чтобы не блокировать тесты и избежать параллельной работы фонового потока при моках HTTP. Для `GET /v1/cryptocurrency/listings/latest`: ретраи при **HTTP 429** с поддержкой **`Retry-After`** или экспоненциальным backoff (потолок **120 с**), пагинация с `CMC_LISTINGS_PAGE_SIZE`, пауза между страницами **`CMC_INTER_PAGE_SLEEP_SEC`**, переменные **`CMC_RETRY_MAX`**, **`CMC_RETRY_BACKOFF_BASE_SEC`**. Дефолтный интервал опроса (**`CMC_UPDATE_TIME`**) в коде — **90** минут и джиттер **±5%** между циклами. В **`CMC_PRO_API_KEY`** / **`X-CMC_PRO_API_KEY`** можно указать несколько ключей через **`|`**; перед каждым HTTP-запросом выбирается случайный (`secrets.choice`). Тесты: `tests/test_coinmarketcap_rank.py`.

### Добавлено

- **Админка / демо-режим (восстановлено):** аутентификация по паролю (`app/admin/auth.py`), роль **`demo`** из env (`ADMIN_DEMO_ENABLED`, `DEMO_LOGIN`, `DEMO_PASSWORD`), ACL в `app/admin/roles.py`; `POST` запрещены для demo на `global-debug`, `scanner/runtime-settings`, `signals/purge`; `GET runtime-settings` в demo — фиксированный снимок (10 / 10 мин / 24 ч / JSONL). **Логи** недоступны в demo. `SessionMiddleware` на корневом FastAPI (`app/__main__.py`). Шаблон **`login.html`**, тесты **`tests/test_admin_demo_acl.py`**.

### Документация

- **Troubleshooting / DESIGN (2026-04-28):** карточка Chrome «Смените пароль» после логина; в **DESIGN.md** маршрут **`/admin/login`**.

- **Дизайн админки (2026-04-28):** `app/docs/DESIGN.md` согласован с **`base.html`** / **`layout.html`** (темы **`mp_admin_color_scheme`**, **`#mp-admin-theme-switch`**, **`mp-admin-theme-change`**, collapsible sidebar / edge-toggle, стили коллекций DataTables); в таблицу маршрутов добавлены **редактирование скринера** и уточнён шаблон URL **Analytics Stat**; **Source Map** — пометка про опциональные скриншоты в `app/docs/design/frontend/`, строка **Настройки UI**, ссылка на спек списка скринеров — `design/Page_Screeners/old_design_Page_Screeners.md`. Обновлены `design_Page_Add_Screener.md`, `design_Page_Signals.md`, вводная в `old_design_Page_Screeners.md` про имя файла.

### Добавлено

- **Админка / Обзор (2026-04-28):** главная **`/admin/`** — дашборд сводки (скринеры, сигналы и Telegram за 24 ч, сессии аналитики по статусам, параметры Scanner runtime, компактные CPU/RAM/диск и размер каталога `app/`). API **`GET /admin_api/dashboard/summary`**; опрос раз в **20 с** с клиента; агрегация **`app/admin/dashboard_summary.py`**, **`DashboardCustomView`** (`index_view`), шаблон **`dashboard.html`**.

- **Скринеры / Telegram (2026-04-28):** токен бота и ID чата **необязательны**. Без пары (в форме и/или после подстановки из `.env`) скринер сохраняется и работает; сигналы пишутся в БД и журнал без вызова Bot API. Миграция Alembic `202604281200_tg_opt` — `settings.bot_token` и `settings.chat_id` допускают `NULL`. При ошибках Telegram (сеть, блокировки, `ok: false`) цикл скринера не прерывается; событие фиксируется как раньше, добавлен `warning` в лог приложения.

- **Сигналы / лог-файл (2026-04-28):** в `signals_log.txt` при записи сигнала в JSON добавляются **`card_snapshot`** (тот же объект, что в `signals.card_snapshot_json`) и **`tracking_id`**, чтобы режим **«Лог-файл»** в админке показывал **горизонтальные** карточки Scanner, как **«БД»**. Парсер вынесен в `parse_signals_log_line` (`app/admin/__init__.py`); в ответе API — поля `card_snapshot`, `tracking_id`, `stat_href`, `render_as_scanner` (как у `signal_orm_row_to_dict`). **Обратная совместимость:** старые строки лога **без** `card_snapshot` остаются **узкими** (legacy), как раньше.

### Изменено

- **Админка / производительность и Lighthouse (2026-04-28):** `timezone.js` перенесён из `<head>` в конец цепочки скриптов страницы (не блокирует первую отрисовку после CSS); в шапке задан явный контраст текста имени пользователя (в т.ч. **DEMO**) — класс **`admin-topbar-user-label`**. В **`EnvironmentType.PRODUCTION`**: заголовки **`Cache-Control`** для **`/admin/statics/*`** (долго, `immutable`) и **`/admin_api/ui/timezone.js`** (сутки); глобально подключён **`GZipMiddleware`** (исключён `text/event-stream` в Starlette). Код: `app/middleware/production_asset_cache.py`, `app/__main__.py`.

- **Админка / вход (2026-04-28):** на **`/admin/login`** убран верхний логотип/иконка (`login.html`); логотип в шапке после входа без изменений.

- **Админка / Обзор — производительность (2026-04-28):** сводка строится одним SQL-агрегатом + GROUP BY статусов сессий; **`signals.total`** — как в списке сигналов (`pg_stat`, иначе точный COUNT), поле **`signals.total_source`** (`estimate` \| `exact`); снимок метрик для дашборда **без** тяжёлого `os.walk` каталога (`record_snapshot_for_dashboard`); in-process TTL **~5 с** на результат сводки (сброс при рестарте воркера); на клиенте **sessionStorage** `mp_admin_dashboard_summary_v1` — быстрый первый показ и опрос сервера; общая логика estimate — **`app/admin/pg_counts.py`**.

### Исправлено

- **Админка / API (2026-04-28):** `ensure_full_admin` требует в сессии роль **`admin`**; без роли или с посторонним значением — **401** (раньше гость мог вызывать защищённые `POST`, если не был в роли demo). Demo по-прежнему **403**.

- **Сигналы / лог-файл (2026-04-28):** несколько строк в `signals_log.txt` с одним и тем же **`tracking_id`** (повторные срабатывания / ошибки Telegram при неизменном «замороженном» `card_snapshot`) больше не дают **дубликатов** карточек: при чтении лога остаётся **самая новая** запись на ключ (tracking_id, symbol, exchange, market_type) — `dedupe_signal_log_items_newest_first` в `app/admin/__init__.py`. В **`signals.html`** при SSE для **лог-файла** и **БД** событие с уже показанным `tracking_id` **обновляет** карточку вместо вставки второй (на случай новых строк при открытой странице).

### Изменено

- **Админка / форма скринера (2026-04-28):** страницы **`/admin/screeners/create`** и **`/admin/screeners/edit`** (`create_screener.html`, `edit_screener.html`): контейнер **`mp-screener-form`** — селекты **`form-select`** (и контейнер **Select2**, если подключён) с **`max-width`**, не на всю ширину карточки; заголовки секций аккордеона без **`text-dark`**, стили панелей под токены **`DESIGN.md`** (`--mp-surface`, `--mp-border-soft`, светлая тема через **`html[data-bs-theme="light"]`**); кнопки **«Развернуть все»** / **«Свернуть все»** — взаимоисключающее **`btn-primary`** / **`btn-outline-secondary`**, по умолчанию активна развёртка; при смешанном состоянии панелей (ручной клик) обе кнопки нейтральные (**outline**). Исправлен лишний символ **`>`** в разметке label обязательного поля.

- **Админка / Аналитика Scanner (2026-04-28):** **`analytics.html`** — в таблице каталога сессий ссылка **Stat →** заменена на кнопку **«График»** (класс **`btn-analytics-chart`**, без стрелки). **`signals.html`** — та же подпись и стиль для ссылки на stat у карточек Scanner.

- **Админка / UX (2026-04-28):** **`layout.html`** — переключатель темы в шапке (`#mp-admin-theme-switch`): обводка трека и hover только на input; у label сброшены отступы Bootstrap `.form-switch` (`padding` 0, `width: fit-content`, у input `float`/`margin-left` 0), чтобы не было серого «хвоста» справа при наведении; логика `localStorage` / `mp-admin-theme-change` без изменений. Меню **Экспорт** (DataTables `div.dt-button-collection`): читаемый hover/focus в **dark** / **light**, в т.ч. `button.dt-button`, без засвета vendor-стилей.

- **Админка / список скринеров (2026-04-28):** светлая тема — кнопка **«Экспорт»** и прочие `.btn-secondary` в **`.page .card`** (тулбар DataTables): на **hover** / **focus** / **active** явный тёмный `color` и чуть сильнее фон/бордер, чтобы текст и иконка не сливались с подложкой.

- **Админка / тема (2026-04-28):** светлая цветовая схема (`[data-bs-theme="light"]`) и переключатель в **верхней панели** (form-switch): выбор хранится в **`localStorage`** (`mp_admin_color_scheme`, значения `dark` / `light`), по умолчанию **тёмная**; ранний скрипт в **`base.html`** уменьшает мигание при загрузке. Семантические CSS-переменные (`--mp-c-surface`, `--mp-c-link`, …) в **`base.html`**; кастомные страницы (**Аналитика**, **Сигналы**, **Логи**, **Система**, stat, настройки, create/edit screener) переведены на эти токены где были жёсткие hex. Событие **`mp-admin-theme-change`** для перерисовки графика на stat. Топбар: **`navbar-light`** / **`navbar-dark`** по режиму (`#mp-admin-topbar`).

- **Админка / Настройки (2026-04-28):** страница **`/admin/settings`** — выбор **IANA** часового пояса (список из `Intl.supportedValuesOf('timeZone')` при поддержке браузером, иначе короткий fallback); подписи зон с UTC±; применение в **`localStorage`** только по кнопке **«Сохранить»** (активна при отличии от сохранённого; до сохранения глобальная зона не меняется). Общий скрипт **`/admin_api/ui/timezone.js`** (`MpAdminTime`) в **`layout.html`** `<head>`; время на **Аналитика**, **Сигналы**, stat — в выбранной зоне; API/БД — UTC.

- **Админка / Analytics Stat (2026-04-28):** **`app/admin/templates/analytics_stat.html`** — ось **«цена (USDT)»** (`yPrice`): явные **min/max** от массива min/max за минуту (low–high столбцы), **padding** ~5% полосы и мин. относительный зазор ~0.01% к середине диапазона; опциональный чекбокс **«Срез выбросов (цена)»** — перцентили **p1** / **p99** по low/high, чтобы единичные всплески не сжимали столбцы. Design: `app/docs/design/Page_Stst/design_Page_Stat.md`.

- **Админка / Analytics Stat (2026-04-27):** страница **`/admin/analytics/stat-…`** (`app/admin/templates/analytics_stat.html`): контейнер графика и «События» (`.stat-charts-fullbleed`) — **ширина 100% от колонки main**, без `100vw` и отрицательных margin к viewport. Иначе при **раскрытом** левом сайдбаре блок съезжал влево, перекрывался сайдбаром и оставлял пустоту справа. Design-spec: `app/docs/design/Page_Stst/design_Page_Stat.md`.

- **Админка / «Система» (2026-04-27):** `/admin/monitoring` (`app/admin/view.py`, `metr.html`) — тёмные карточки в сетке **2 колонки** (мобильно — 1), мини-графики (canvas) CPU, RAM, диск и **размер каталога `app/`**; опрос `GET /admin_api/monitoring/metrics` раз в 1 с с той же политикой доступа, что и прочие `admin_api`. История в `app/admin/monitoring_metrics.py`: кольцо **~5 мин** для процентов, **1440** поминутных точек для размера каталога (полный `walk` — не чаще **60 с**; опционально `MONITORING_APP_DIR` для другого пути). Эфемерно до рестарта воркера.

- **Админка / сайдбар (2026-04-27):** в **`app/admin/templates/layout.html`** в **`aside`** убран дубль бренда (**вордмарк / логотип**); навигация начинается с **navbar-toggler** и пунктов меню; вордмарк остаётся только в **верхней горизонтальной панели**. CSS скрывает мобильный дубль меню пользователя с **`.icon-tabler-user`** в сайдбаре (апстрим).

- **Админка / скринеры (2026-04-27):** в списке **`/admin/screeners/list`** колонка **«Отладка»** (`debug`) по умолчанию идёт сразу после **«Включить скринер»** (`enabled`): порядок полей в **`app/admin/view.py`** (`SettingsModelView.fields`). Формы create/edit: секции рендерят поля в порядке **`section.fields`**, чтобы блок **«Уведомления»** не менялся (`create_screener.html`, `edit_screener.html`).

- **Админка / topbar (2026-04-28):** **`app/admin/templates/layout.html`**: пустой **`#navbar-menu`** вынесен из прямых детей `container-xl` (он давал **третью колонку** при `justify-content: space-between` и визуально держал язык/профиль **по центру**). Кластер язык / таймзона / **avatar+username** — в **`.admin-topbar-end`** с `justify-content: flex-end`, контейнер — **`justify-content-between`**, вордмарк `flex-shrink-0`.

- **Админка / layout shell (2026-04-28):** **`app/admin/templates/layout.html`**: текстовый вордмарк **«money pulso»** в верхней панели (ссылка на index), верхняя панель видна на **всех ширинах** (чтобы **«admin»** / выход оставались после удаления дубликата в сайдбаре). Убран блок **avatar/пользователь** в верхней строке **сайдбара**; язык в `d-lg-none` оставлен, если есть переключатель. Кнопка сворачивания сайдбара на **`≥ 992px`**: **`.admin-sidebar-edge-toggle`** — **круг** (17px), `rgba(30,41,59,.95)`, обводка; центр на стыке сайдбар/контент при `translate(-50%,-50%)`; **inline SVG** (одинарный шеврон), не шрифт иконок; **`--mp-admin-aside-w`** от ширины `aside` при resize; старая **`.admin-sidebar-toggle`** (левый верх) удалена.

- **Админка / тёмная тема (2026-04-28):** **`app/admin/templates/base.html`**: `data-bs-theme="dark"` на `<html>`, токен **`--mp-shell-bg` (#0f172a)** и единый фон для `body`, `.page`, `.page-wrapper`, `.page-body`; верхняя шапка — тот же фон, не белая. **`layout.html`**: `navbar-light` → **`navbar-dark`** (полоска с «admin» в палитре shell). Убирает «плавающие» тёмные блоки на белом холсте.

- **Админка / DataTables (2026-04-27):** **`app/admin/templates/layout.html`**: в списках (в т.ч. **`/admin/screeners/list`**) тёмные оверлеи **Экспорт**, **видимость столбцов**, **SearchBuilder** — стили с якорем **`html[data-bs-theme="dark"]`** и **`!important`**, т.к. **`dt.min.css`** подключается в **`list.html` после** блока layout и задаёт светлый фон у **`div.dt-button-collection`**. Добавлены: заголовки коллекции, **split**-кнопки colvis, панель **`dtsb-searchBuilder`**, **`btn-outline-primary`**, модалка **`div.dt-button-info`**. Выпадашки **языка/профиля** в шапке не трогаются (селекторы только `dt-button-collection` / **`dataTables_wrapper`**).

- **Админка / доступность и SEO (2026-04-28):** полный шаблон **`app/admin/templates/layout.html`** (на базе `base.html`): регион **`main`** с `role="main"`, **`meta name="description"`**, **`meta robots` только при `ENVIRONMENT=production`** (на dev удобнее Lighthouse; глобаль `admin_robots_noindex` в `register_admin_routes`), `referrer`; подписи **`aria-label`** у переключателей меню, языка, часового пояса и меню пользователя; **alt** у логотипа; иконки с **`aria-hidden="true"`**; без вложенного `<h3>` в бренде (текст без логотипа — `span`). Локальные **`app/admin/templates/macros/views.html`**: `rel="noopener noreferrer"` для внешних ссылок, **aria** у dropdown в навигации. **`create_screener.html`**: заголовок страницы — **`h1.visually-hidden`** вместо пустого `<h1>`.

- **Docker (2026-04-27):** в корне репозитория добавлен **`compose.yaml`** с `include: app/docker-compose.yaml`, чтобы `docker compose up --build` работал из каталога `money_pulso/`, а не только из `app/`.

- **Админка / производительность (2026-04-28):** переопределён **`app/admin/templates/base.html`**: убран блокирующий **`@import` Inter с `rsms.me`** (при недоступности хоста — десятки секунд до первой отрисовки, NO_FCP). Шрифт — системный стек. См. [troubleshooting.md](troubleshooting.md).

- **Админка / производительность (2026-04-28):** **«Логи»** — чтение только **хвоста** `app.log` (~512 KiB) в thread pool вместо целого файла + гигантского HTML. **«Система»** — все вызовы `psutil` в одном `asyncio.to_thread`. **API `/admin_api/signals`** — для `total`/`pages` при PostgreSQL сначала **`pg_stat_user_tables.n_live_tup`** (без полного `COUNT(*)` на больших таблицах), иначе точный COUNT.

- **Админка / производительность (2026-04-27):** страница **«Система»** (`MetrCustomView`): вместо синхронного `psutil.cpu_percent(interval=1)` в async-рендере — `asyncio.to_thread(psutil.cpu_percent, 0.1)`, чтобы не блокировать event loop uvicorn на ~1 с и не тормозить остальные запросы при одном воркере. Подробнее: [troubleshooting.md](troubleshooting.md).

- **Конфиг / Docker (2026-04-27):** снова дефолт **8000**: проброс `${APP_PORT}:8000`, uvicorn в контейнере на `8000`; шаблон `APP_PORT` в `.env.example` — **8000**.

- **Документация / бренд (2026-04-27):** ребрендинг материалов `app/docs/**`, `app/docs/marketing/**`, `app/README.MD`: имя продукта **Money Pulso** (ранее в текстах: *money_pulso*). Репозиторий по-прежнему `money_pulso`. Заголовок админки / OpenAPI: `Money Pulso` (`app/config/config.py`).

- **Презентации / Marp (2026-04-14):** восстановлен каталог `presentations/`; дек `russia-economy-2022-2026.md` — **9** графиков (линия/столбцы/круговая) + **2** AI-фона; стиль **Metric Navy** из Stitch MCP (проект `1969498366242669871`); `DESIGN_TOKENS.md` и `stitch-russia-economy-deck-raw.tokens.json` обновлены; pptx: `presentations/dist/russia-economy-2022-2026.pptx`.

- **Оркестрация / агенты (2026-04-14):** добавлен агент **`imager`** (генерация изображений Marp через Polza, `presentations/scripts/polza_marp_images.py` + CLI `generate`); скилл **`.cursor/skills/ai-image-generation`** (связка с практиками [tool-belt/ai-image-generation](https://skills.sh/tool-belt/skills/ai-image-generation)); **`designer`** обновлён: делегирование **`Task(imager)`** вместо прямых вызовов API. Правила: [`workflow-selection.mdc`](../../.cursor/rules/workflow-selection.mdc), [`CREATING_ASSETS.md`](../../.cursor/docs/CREATING_ASSETS.md).

- **Презентации / Marp pptx (2026-04-14):** исправлены типичные артефакты экспорта: таблица «Риски» переведена на **HTML с inline-стилями** (тёмные ячейки в PowerPoint); слайд «Хронология» без fenced code (вместо белого блока); графики — меньший `figsize`/шрифты в `chart_from_csv.py`, колонка `![bg right:32%]`; обложка перегенерирована с **финансовой** метафорой. Скилл `marp-slide` и агент `designer` дополнены правилами про pptx и тематические AI-промпты.

- **Презентации (2026-04-14):** дек `presentations/russia-economy-2022-2026.md` — четыре графика из CSV (`gdp-growth`, `cpi-yoy`, `cbr-key-rate`, `value-added-share` → `chart-{gdp,cpi,key-rate,sectors}.png`), обложка `presentations/assets/generated/cover-economy.png` (генерация изображения). Stitch MCP в сессии не ответил — `stitch-russia-economy-deck-raw.tokens.json` заполнен вручную; стиль согласован с `DESIGN_TOKENS.md`. В `presentations/chart_from_csv.py` для `--kind bar` первая колонка CSV — текстовые метки.

### Добавлено

- **Документация / маркетинг (2026-04-27):** канон позиционирования и ICP вынесен в **`app/docs/marketing/`** (`README.md`, `context.md`); `.cursor/marketing-context.md` — короткий указатель; удалён ошибочно попавший **`marketing-sales-kit.md`** (относился к другому продукту). Оглавление: [README.md](README.md).

- **Документация / маркетинг — контракт путей (2026-04-27):** исследования и roadmap агентом `marketing-researcher` — в **`app/docs/marketing/research/`**; тактические артефакты агентом `marketing` по умолчанию — **`app/docs/marketing/artifacts/`**; инструкции в playbook, агентах и `workflow-feature` обновлены. Подкаталоги с `.gitkeep` для пустого git-трека.

- **Документация / маркетинг — прогон плана (2026-04-27):** добавлены **`research/intake|synthesis|brief-positioning|roadmap`-2026-04-27.md** и тактические черновики в **`artifacts/`** (landing, SEO, CRO, нейминг, email, соц, реклама); конкурентный веб-ресёрч не выполнялся — пометка в synthesis. Восстановлены **`context.md`** и **`README.md`** в `app/docs/marketing/`.

- **Оркестрация Cursor (2026-04-15):** скилл **`.cursor/skills/ecosystem-integrator`** и команда **`/workflow-integrate-skill`** — безопасная интеграция внешних скиллов (skills.sh / `npx skills`) с адаптацией под делегирование через **`Task`**; обновлены **`agent-intent-map.csv`** (строка `ecosystem_integration`), **`CREATING_ASSETS.md`**, **`workflow-selection.mdc`**, **`norissk.md`**, **`documentation.mdc`**, агенты **`researcher`** / **`planner`**. Подробнее: [`.cursor/docs/CREATING_ASSETS.md` § ecosystem-integrator](../../.cursor/docs/CREATING_ASSETS.md#ecosystem-integrator).

- **Конфиг / Polza:** в `app/.env` и `app/.env.example` добавлена переменная **`POLZA_MODEL`** (идентификатор модели генерации; пример по умолчанию в доке — `gpt-image-1`, см. каталог моделей на polza.ai). В `.cursor/config.json` → `polza.modelEnv`. Вспомогательная функция `get_polza_model()` в `presentations/scripts/polza_marp_images.py`.

- **Презентации / Marp (2026-04-14):** дек `presentations/russia-economy-2022-2026.md` — тема **Sovereign Analyst** (Stitch `list_projects`, проект Russia Economy Deck); шесть CSV→PNG (`chart-gdp.png`, `chart-inflation.png`, `chart-key-rate.png`, `chart-oil.png`, `chart-fiscal.png`, `chart-asia-share.png`), три narrative PNG в `presentations/assets/generated/`; слайды с **Mermaid** (в pptx могут отображаться как код — см. слайд с подсказкой); `presentations/dist/russia-economy-2022-2026.pptx` собирается `npx @marp-team/marp-cli ... --pptx --allow-local-files`. Восстановлен минимальный модуль `presentations/scripts/polza_marp_images.py` (тесты `test_polza_marp_images.py`).

- **Инструменты / Marp:** в корне репозитория добавлены `package.json` с dev-зависимостью `@marp-team/marp-cli`; каталоги `presentations/` (исходники `.md`) и вывод сборки `presentations/dist/` (пути в `.cursor/config.json` → `presentations`). См. фрагмент в [README.md](README.md) про сборку pptx/pdf/html.

- **Инструменты / Marp / графики:** модуль `presentations/chart_from_csv.py` (корень репо, не `app/`), CLI `presentations/tools/chart_from_csv.py`; optional-dependencies `presentations` (matplotlib) и `presentations-plotly` (plotly + kaleido). Для дека «Экономика России 2022–2026» построены локальные PNG (`chart-gdp-growth.png`, `chart-cpi.png`, `chart-key-rate.png`, `chart-budget-balance.png`, `chart-urals-oil.png`, `chart-real-incomes.png`) из `presentations/sample-data/*.csv`.

- **Документация / Stitch MCP:** в скилле `stitch-mcp` зафиксировано: выгрузка скриншотов/SVG по URL из Stitch для ассетов репозитория **ненадёжна**; для Marp — токены из ответа API и локальные картинки (`marp-slide`, `designer`, `CREATING_ASSETS`).

- **Презентации / дизайн-токены:** в `presentations/` добавлены `DESIGN_TOKENS.md`, `stitch-russia-economy-deck-raw.tokens.json`, скрипт `presentations/scripts/polza_marp_images.py` (Polza Media API; выбор ≤30% слайдов; ключ `POLZA_API_KEY` / `POLZA_AI_API_KEY`, опционально `POLZA_BASE_URL`). Скрипт подмешивает переменные из **`app/.env`**, если они ещё не заданы в окружении процесса, и при ошибке/пустом ответе API автоматически пишет локальные placeholder PNG через `matplotlib`, чтобы Marp-сборка не ломалась.

- **Презентации / пример:** дек «Экономика России 2022–2026» — `presentations/russia-economy-2022-2026.md`, токены Stitch **Macro Ledger** (`stitch-russia-economy-deck-raw.tokens.json`), графики PNG из `presentations/sample-data/*.csv`, narrative-background PNG (`cover.png`, `section-demand.png`, `closing.png`) под `presentations/assets/generated/`, сборка pptx в `presentations/dist/russia-economy-2022-2026.pptx`.

- **Scanner / сессии без trigger:** если по всем **включённым** фильтрам ``ok`` стали ложными (ни один не активен), не сработавшая сессия удаляется из памяти, из таблицы ``tracking_sessions`` и с диска (JSONL). Пока был хотя бы один ``ok``, запись ведётся; после **trigger** (все фильтры ok одновременно) сессия сохраняется как раньше до завершения посттрека. При **prune** сессии без trigger тоже удаляются с диска и из БД (раньше статус ``abandoned``).

- **Сигналы / БД:** в JSON снимка на trigger добавлены `scanner_duration_at_trigger_ms` и `scanner_snapshot_frozen` (только в `card_snapshot_json`, не в live SSE). API: поле `render_as_scanner` при наличии распарсенного snapshot. Тесты: `tests/test_admin_signals_api.py`.
- **Сигналы / БД (вёрстка):** записи без `card_snapshot_json` тоже показываются **горизонтальной** карточкой как Scanner (тот же шаблон), с пояснением в блоке фильтров; полная диагностика фильтров — только при наличии снимка на trigger. **Очистка:** `POST /admin_api/signals/purge?target=db|log` — только таблица `signals` или только `signals_log.txt`; в UI кнопки «Очистить БД» (режим БД) и «Очистить лог-файл» (режим лог-файла).

- **Stat (`/admin/analytics/stat-*`):** фон — полупрозрачные столбцы **low–high за минуту** по цене (ось USDT); в строках JSONL `kind: sample` поле **`last_price`** (last close из свечей оценки; для старых файлов fallback на PD `final_price` при расчёте min/max).

- **Scanner Analytics:** глобальный runtime (`screener/scanner_runtime.py`) — настройки `max_cards` / `posttracking_minutes` / `cooldown_hours` / `statistics_enabled` (таблица `scanner_runtime_settings`), top-N по score с посттреком вне top-N, сессии `tracking_id`, индекс **`tracking_sessions`**, append-only **JSONL** под `app/statistics-data/` (`session_meta`, `sample`, `event`). Точечные записи в БД на trigger / completed / closed; в **`signals`** — `tracking_id`, `card_snapshot_json` (frozen UI на trigger). API: `GET/POST /admin_api/scanner/runtime-settings`, `POST /admin_api/scanner/close`, `GET /admin_api/analytics/sessions`, `GET /admin_api/analytics/samples`, **`POST /admin_api/analytics/purge`** (полная очистка: таблица `tracking_sessions`, файлы `statistics-data`, сброс in-memory сессий Scanner). UI: меню **Аналитика** (кнопка **«Очистить»**), Stat-страница с графиком (Chart.js); на **Сигналы** — ссылка Stat, закрепление карточки (сортировка), закрытие посттрека, режим **БД** с горизонтальной карточкой из snapshot, как в Scanner. Ротация каталога по расписанию не встроена — при необходимости внешний cron/том Docker.

- **Scanner — максимумы по фильтрам:** пока пара в ленте, для каждого включённого фильтра ведётся максимум «текущего» скаляра (PD/DP/OI/FR — по модулю %/ставки; DV — суточный объём; VL — множитель; LQ — доля % от суточного объёма, иначе сумма в USDT). В SSE поле **`scanner_filter_max_list`** (порядок как у `test_filters`); во **второй колонке** карточки блок **«max …»** над текстом из Telegram. При выпадении из Scanner (ни один фильтр не OK) пики для символа сбрасываются.

- **Scanner — время срабатывания фильтра:** при переходе **ok** с «нет» на «да» фиксируются момент (UTC, в UI — как время карточки) и смещение от старта счётчика скринера (**`fire_meta`** в строке `test_filters`: `fire_at`, `fire_elapsed_ms`); при повторном срабатывании после падения **ok** значения обновляются. Внизу блока каждого фильтра на карточке — две строки в формате как у основного счётчика. Состояние **`_scanner_filter_prev_ok`** / **`_scanner_filter_fire`** сбрасывается при выходе пары из Scanner.

- **Админка**: кнопка в левом верхнем углу (desktop, ≥992px) для сворачивания левого вертикального меню; основная область на всю ширину; состояние запоминается в `localStorage`. На странице входа и без боковой панели кнопка не показывается.

- **Страница «Сигналы» — режим «Тест»**: третий источник просмотра (рядом с БД и лог-файлом). Пока открыт SSE (`GET /admin_api/signals/stream?source=test`), воркер `Consumer` для каждого символа дополнительно считает независимую оценку фильтров (`screener/test_mode_eval.py`): после гейтов (USDT, наличие свечей, чёрный/белый список) в ленту попадают только пары, где **хотя бы один включённый** контентный фильтр даёт `ok`. Карточка совпадает с обычным сигналом (тот же `generate_text`); под ней — блок «Диагностика фильтров» с текущими значениями и порогами. История не хранится; при повторных тиках одна и та же пара обновляется на месте. Пока никто не смотрит режим «Тест», лишняя оценка не выполняется.
- **Режим «Тест» — сортировка и счётчик**: карточки упорядочены по убыванию **`score`** (среднее signed-вкладов); при равенстве — по `ok_count`, затем по `tie_break_score`, затем по `id`. Карточки без `score` внизу. В тулбаре — **Онлайн: N** и выпадающий список **макс. карточек** (5 / 10 / 20 / 30 / 50 / 100, по умолчанию **10**): на экране одновременно не больше выбранного числа; лишние с более низким Score удаляются из DOM (настройка в `localStorage`). Вытеснение: при появлении новой пары с Score выше, чем у нижней из видимых, она попадает в топ-N, нижняя скрывается.
- **Режим «Тест» — Score**: для каждого включённого фильтра считается **signed-вклад** относительно порога (0 на границе, без усечения 0–100: сильные превышения/провалы дают большие положительные/отрицательные значения); в строках `test_filters` поле **`filter_score`**, в payload **`score`** — среднее арифметическое вкладов. На карточке — **Score** без «%»; в диагностике — строка **«Вклад»** по каждому фильтру.
- **Режим «Тест» — карточка**: горизонтальная компоновка (тикер и Score, тело сообщения Telegram, **полоса фильтров**, биржа и время). На широкой сетке до **пяти** колонок диагностики фильтров укладываются в строку **без горизонтальной прокрутки** (равные доли `flex`, компактная типографика); узкий экран — перестроение сетки и перенос колонок фильтров. **Режим БД:** при непустом `card_snapshot_json` — та же горизонтальная карточка, что в Scanner (frozen snapshot на trigger; длительность в UI из `scanner_duration_at_trigger_ms`; без lock/close). **Лог-файл:** с записью `card_snapshot` в JSON строки — горизонтальная карточка как БД; без снимка в строке — узкая (legacy). Строки БД без snapshot — горизонтальная с пояснением.

### Исправлено

- **Презентации / Marp:** модуль CSV→PNG перенесён из `app/presentations/` в **`presentations/chart_from_csv.py`** (один канонический каталог презентаций у корня репо). Дек `russia-economy-2022-2026.md`: слайд 7 — схема как внешний `assets/diagram-macromodel.svg` (инлайн-SVG с отступами давал блок кода в Marp/pptx); слайды 1 и 10 — заголовок разбит на `#` + `##`, уменьшены размеры шрифта для `lead`; слайд 8 — убраны «белые» панели с классами и сырой `<div class="callout">` (в pptx Marp часто теряет CSS/HTML), заменено на обычный markdown и blockquote.

- **Презентации / Marp / Polza:** `polza_marp_images.py` — выходной путь для меты `polza-file` в слайде нормализуется к **basename** и проверяется на вложенность в `--out-dir` (защита от path traversal); при отказе API в `manifest` поле `generator` остаётся `placeholder`; в stderr пишется причина fallback.

- **Презентации / Marp / Polza:** для дека `presentations/russia-economy-2022-2026.md` имена background PNG синхронизированы между markdown и `presentations/scripts/polza_marp_images.py` (`cover.png`, `section-demand.png`, `closing.png`), поэтому `manifest.json` и локальные ассеты больше не расходятся с реальными ссылками в слайдах.

- **Презентации / Marp:** CSV→PNG пайплайн для дека `presentations/russia-economy-2022-2026.md` доведён до рабочего состояния: модуль `presentations.chart_from_csv` (пакет в каталоге `presentations/` у корня репо), CLI `presentations/tools/chart_from_csv.py` импортирует его при `PYTHONPATH` = корень репозитория, `pytest app/tests/test_chart_from_csv.py app/tests/test_polza_marp_images.py -q` проходит, а `npx @marp-team/marp-cli ... --pptx --no-stdin --allow-local-files` снова собирает `presentations/dist/russia-economy-2022-2026.pptx`.

- **Сигналы / БД / Scanner:** пустой `card_snapshot_json` при продакшн-сигнале, хотя фильтры «Тест» все `ok` — символ мог **не входить в top-N по score**, из-за чего `prune_sessions_not_in_set` и ветка обогащения Scanner не выполнялись для этой пары, сессия срезалась до `mark_triggered`. В множество «оставить сессию» добавлены символы с `all_filters_ok` в текущем цикле (`scanner_eligible = allowed ∪ must_all_ok`).

- **Сигналы / БД:** дубли карточек с одним и тем же `tracking_id` — при повторных продакшн-вызовах `_send_signal` в posttracking каждый раз делался `INSERT` в `signals`. Теперь при непустом `tracking_id` вторая и последующие вставки с тем же id пропускаются (тест: `tests/test_consumer_signal_db_dedupe.py`).

- **Сигналы / БД:** повторные строки без `card_snapshot_json`: (1) на каждом цикле `pending_snap` пустой после первого `mark_triggered`; (2) кэш в `Consumer` сбрасывался при выходе символа из `allowed`, хотя продакшн-сигналы продолжались. Снимок хранится в `scanner_runtime._pending_signal_snapshots` до удаления сессии из `_sessions` (см. `get_card_snapshot_for_signal_row`).

- **Админка / Stat:** у `starlette-admin` задан **абсолютный** `templates_dir` (каталог `app/admin/templates` от `__file__`). Раньше использовалась строка `app/admin/templates` относительно **cwd**; при запуске из каталога `app/` путь превращался в несуществующий `app/app/admin/templates` → `TemplateNotFound` на `analytics_stat.html` и **500** на `/admin/analytics/stat-…`.

### Изменено

- **Админка / Сигналы:** `<title>` страницы `/admin/signals` — **«Сигналы»**.

- **Шаблон сообщения DEFAULT** (`utils/generate_text.py`): из текста убран блок **«♻️ Условия срабатывания»** (строки по PD/OI/VL/LQ за интервал). Остаются шапка с тикером/скринером, блок **«📊 Текущие данные»** и футер со ссылками. В Scanner карточке второй колонки условия дублировали диагностику фильтров; максимумы по фильтрам по-прежнему из `scanner_filter_max_list`.

- **Админка — верхняя белая шапка (desktop)**: контейнер шапки растянут на всю ширину полосы, элементы справа (пользователь и т.д.) выровнены к **правому краю окна** — при свёрнутом левом меню они больше не «уезжают» влево из‑за ограничения `max-width` у `container-xl`.
- **Режим «Тест» — числа в карточке**: значения параметров в блоках «Текущее» / «Пороги», поле «Вклад» по фильтру и строка **Score** на карточке выводятся с округлением **до 4 знаков после запятой** (снимаются длинные float-артефакты вроде `-0.000029999999999998778`).
- **Страница «Сигналы»**: убраны верхний отступ между белой шапкой админки и тулбаром (переопределён `margin-top` у `.page-body`), убрана серая линия под шапкой (inset `box-shadow` у горизонтального `navbar`), чуть уменьшен верхний внутренний отступ блока страницы.
- **Режим «Тест» — карточка (фронт)**: новая сетка `grid` + полоса `.sct-filters-strip`, общий заголовок «Диагностика фильтров», блоки фильтров с укороченными подписью и данными строками; класс контейнера `signal-card-test-frame` вместо прокрутки по оси X.
- **Режим «Тест» — карточка (апрель 2026)**:  первая колонка — тикер (копирование), строка `#ранг` + `Score` (3 знака), название скринера, ссылки Bybit / TradingView / CoinGlass, биржа и рынок через « - », время; без индикаторов Telegram, без колокольчика. Вторая колонка — только «Условия» и «Текущие данные» (шапка и футер со ссылками убраны из текста, строка «Сигналов за 24ч» скрыта). Третья зона — фильтры: статусы «да»/«нет» в строке с названием; строка **«Вклад»** и значение — ниже названия, над «Текущее»; текущие значения и пороги построчно (`key=value`). Сетка **3 колонки**: фиксированные **170px** и **250px** для первых двух, оставшаяся ширина — поровну на колонки фильтров; на узком экране перестроение без фиксированных пикселей.
- **Страница «Сигналы»**: в UI режим «Тест» переименован в **Scanner**; при открытии страницы по умолчанию включён Scanner; порядок кнопок источника: **Scanner**, **БД**, **Лог-файл**. В запросах к API по-прежнему `source=test`.
- **Scanner (карточка):** вместо времени снимка показывается момент первого попадания пары в отслеживание (`scanner_tracked_since` в SSE); под ним — длительность одной строкой **ЧЧ:ММ:СС, Ns** (например `00:01:45, 111s`). На бэкенде время старта хранится на символ, пока пара остаётся в Scanner; при выпадении из режима (ни один фильтр не OK) счётчик сбрасывается.
- **Scanner — счётчик длительности:**  при каждом SSE приходит новый `created_at` (время снимка); фронт больше не использует его как единственный fallback — для старта отслеживания выбирается **самая ранняя** метка из `scanner_tracked_since`, уже показанной на карточке и `created_at`, чтобы длительность не сбрасывалась при обновлении данных.
- **Scanner — диагностика фильтров:** статус OK/не OK показывается цветом названия фильтра (зелёный / красный), без подписей «да» / «нет».
- **Scanner — ликвидации:** в блоке «Текущее» первой строкой выводится `lq_pct_of_daily_volume` (доля ликвидаций от суточного объёма, %); на фронте порядок полей принудительно задан (ключи из SSE/JSON иначе часто шли по алфавиту).

## [1.4.0] — 2026-04-01

### Добавлено

- **Страница «Сигналы»** в админке (`/admin/signals`): история всех сигналов, отправляемых в Telegram, в дизайне Telegram-сообщений. Два источника на выбор — таблица `signals` в PostgreSQL или `signals_log.txt`. Новые сигналы появляются автоматически без перезагрузки страницы через SSE (< 100 мс). Пагинация 100 / 500 / 1000 записей на странице, новые сигналы вверху. Адаптивная вёрстка для узкого экрана, анимация подсветки новых карточек 3 с («умная»: анимация стартует только когда карточка попала в поле зрения и пользователь активен в окне). Кнопка прокрутки вверх с бейджем-счётчиком непрочитанных сигналов: при нажатии прокручивает к верху и сразу запускает 3-секундную анимацию на всех непрочитанных карточках.
- **Таблица `signals`** в PostgreSQL: каждый сигнал записывается независимо от статуса доставки в Telegram, что позволяет не терять сигналы при блокировках Telegram.

### Исправления

- Исправлено падение приложения (циклический рестарт контейнера) при запуске, возникавшее из-за ошибки инициализации внутренних модулей.
- **Страница сигналов:** CMC-ранг теперь отображается даже для сигналов, записанных когда CMC-кеш не был заполнен (race condition при одновременном старте нескольких контейнеров). API-эндпоинты `/admin_api/signals` и SSE-стрим отдают поле `cmc_rank` с live-значением из текущего кеша; фронт использует его как фолбэк если ранг отсутствует в тексте сигнала.

## [1.3.0] — 2026-03-26

### Добавлено

- **`app/logs/signals_log.txt`**: одна JSON-строка на событие — сигналы Telegram (текст сообщения, id/имя скринера, ответ API без секретов, плоские поля расчёта из `calc_debug`), жизненный цикл приложения/оператора, старт/стоп консьюмеров, рестарты WS-парсеров (причина: watchdog по устаревшим данным / плановый recycle / восстановление мёртвой задачи). Ротация **10 MB**, до **10** архивов `signals_log.YYYY-MM-DD_HH-MM-SS_usecs.txt` (**Europe/Moscow**).
- Ротация **`app.log`** и **`debug.log`**: архивы с меткой **Москва** `stem.YYYY-MM-DD_HH-MM-SS_usecs.log`, без суффиксов `.1` / `.2`; `debug.log` — по-прежнему **100 MB** и очередь, обработчик `_SafeMoscowSizeRotatingFileHandler`.
- Во всех основных логах **дата и время в начале строки** (Москва): `app.log` — `YYYY-MM-DD HH:mm:ss.SSS|level|…`; `debug.log` и `signals_log.txt` — префикс `…+03:00` (ISO), таб, затем JSON.

### Исправления

- **Telegram:** после `sendMessage` проверяется поле **`ok`** в JSON. Раньше при HTTP 200 и `ok: false` (неверный чат, битый HTML, лимиты и т.д.) ошибка не детектировалась, в логах могло быть «успешно» без доставки. См. `utils/telegram_bot.py` (`TelegramApiError`).
- Ликвидации: ключ в кеше парсера совпадает с поиском в `Consumer` (`normalize_ticker`), чтобы не терять события из‑за расхождения с `removesuffix("USDT")`.
- `app/logs/debug.log`: ротация на именованные архивы (Москва) + `_SafeMoscowSizeRotatingFileHandler` + `delay=True`, чтобы реже ловить `FileNotFoundError` при rename на томе Docker.
- Debug JSON (`cycle_start`): убрано поле `missing_klines` — оно всегда было 0 до выполнения задач; актуальное значение только в `cycle_end`.
- Operator: плановый recycle WS-парсеров `agg_trades` / `liquidations` по `WS_PERIODIC_RECYCLE_SEC`; первая отметка времени без рестарта при появлении пары.
- `docker-compose.yaml` (сервис `app`): если `WS_PERIODIC_RECYCLE_SEC` не задана в `.env`, подставляется **14400** (4 ч). Выключить: `WS_PERIODIC_RECYCLE_SEC=0` в `.env`.
- `Operator`: если переменная **не задана или пустая** (в т.ч. без Docker), по умолчанию **14400** с; `WS_PERIODIC_RECYCLE_SEC=0` — выкл.
- Старт Operator: в лог пишется интервал recycle или «off».
- Consumer: уровень **CRITICAL** при медленном цикле только если длительность **≥** `_CHECK_INTERVAL_SEC` (1 с); порог «половина секунды» убран — устраняет ложные CRITICAL при ~0.52 с под нагрузкой.
- Consumer (debug): все отказы фильтров по символам (кроме skip whitelist/USDT) в `app.log` — **DEBUG**; сводка в `cycle_end` (`missing_klines`, `lq_zero_window_failures`, `fail_reasons_top`). Построчно в `app.log`: переменная окружения **`LOG_LEVEL=DEBUG`** (см. `config/logger.py`, `.env.example`).
- Logger: при импорте подхватывается **`app/.env`** в `os.environ` для ключей, которых ещё нет в окружении (как у `python-dotenv`), затем читается `LOG_LEVEL` — чтобы локальный запуск без Docker видел уровень из файла.

### Состав релиза

- Сопутствующая документация в `app/docs/` (оглавление, архитектура, contributing, roadmap, troubleshooting) и шаблон `app/.env.example`.

### Поведение и ограничения (актуально для 1.3)

- Скринер и биржи: возможности определяются пакетом `unicex` и настройками скринеров в админке.
- Админка: провайдер авторизации не требует логина/пароля (см. `app/admin/auth.py`).
- `app/screener/producer.py` не входит в рабочий пайплайн данных; источник потоков — `app/screener/parsers/` и `Operator`.
