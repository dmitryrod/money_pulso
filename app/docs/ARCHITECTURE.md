# Архитектура

## Назначение

Веб-приложение на **FastAPI**: админка для настройки скринеров (PostgreSQL) + фоновый **Operator**, который поднимает парсеры рыночных данных через **unicex** и **Consumer**-ы, проверяющие фильтры и отправляющие уведомления в **Telegram**.

## Точка входа и жизненный цикл

- Модуль `app/__main__.py`: приложение `app`, `lifespan` при старте:
  1. Инициализация БД: `Base.metadata.create_all` + добавление колонки `lq_min_amount_pct`, если отсутствует (fallback без отдельной миграции для этой колонки).
  2. При сетевых/БД сбоях класса «transient» — ожидание через `utils.connectivity` (не выход процесса).
  3. `unicex.start_exchanges_info()` — единая инициализация метаданных бирж.
  4. Регистрация админ-маршрутов (`admin.register_admin_routes`).
  5. Запуск `Operator.start()` в `asyncio.create_task`.
  6. Фоновая `start_support_task()` (пока заглушка с периодическим sleep).
- При остановке: `operator.stop()`.

В **production** (`ENVIRONMENT=production`) у FastAPI отключены публичные `docs`, `redoc`, `openapi`.

## Слои данных

| Слой | Роль |
|------|------|
| `database/` | SQLAlchemy async engine, `SettingsORM`, `SignalORM`, `ScannerRuntimeSettingsORM`, `TrackingSessionORM`, репозитории, Alembic-миграции |
| `schemas/dtos.py` | `SettingsDTO` и прочие DTO для передачи между слоями |
| `models/` | Доп. модели/DTO при необходимости (не путать с `database/models`) |

Подключение к БД: строка из `config.Configuration.db` (`postgresql+asyncpg://...`).

## Operator (`screener/operator.py`)

- Периодически (порядка **3 с**) читает из БД список настроек скринеров.
- Для каждой уникальной пары **(Exchange, MarketType)** держит набор **парсеров** (`ParsersDTO`: agg trades, funding, liquidations, open interest, ticker daily — по необходимости).
- Для каждого **включённого** скринера создаёт/обновляет **Consumer**, привязанный к тем же парсерам.
- Следит за «зависшими» WebSocket-парсерами: пороги устаревания данных, backoff при перезапусках, восстановление упавших задач парсеров.
- Плановый recycle `agg_trades` и `liquidations`: `WS_PERIODIC_RECYCLE_SEC` (сек); **не задана / пусто** → дефолт **14400**; **`0`** — выкл. В Docker Compose та же подстановка через `environment`, если переменной нет в `.env`.

## Парсеры (`screener/parsers/`)

- Базовый класс `Parser`: лимит истории, throttling меток `last_update_ts`, контекст клиента `get_uni_client(exchange)`.
- Конкретные реализации подписываются на потоки биржи и наполняют структуры данных для фильтров.

## Consumer (`screener/consumer.py`)

- Цикл с интервалом проверки порядка **1 с**.
- Цепочка фильтров в `screener/filters/` (whitelist/blacklist, pump/dump, OI, funding, volume multiplier, liquidations, суточный объём/цена, only USDT, лимиты сигналов в сутки и т.д.).
- Кэш ставки финансирования с TTL **55 с** на символ (`_FUNDING_RATE_CACHE_TTL_SEC`) — снижение нагрузки на REST/API биржи.
- Тяжёлая часть фильтров может выполняться в `ThreadPoolExecutor` (до 4 воркеров).
- **Режим «Тест» / Scanner (админка):** если активен SSE `source=test` **или** в БД включён **`statistics_enabled`** (`screener/scanner_runtime.py` — кэш настроек), в том же `run_in_executor` после `_check_filters_for_symbol` вызывается `evaluate_test_mode_snapshot` (`screener/test_mode_eval.py`) — гейты как у продакшена, затем независимые `Filter.process` по всем включённым фильтрам; при «хотя бы один ok» строится payload. **`broadcast_test_payload`** вызывается только при активном SSE. Параллельно **`scanner_runtime`** ведёт top-N по score ∪ posttracking, сессии `tracking_id`, append-only **JSONL** в `app/statistics-data/` (`kind`: `session_meta` / `sample` / `event`), без блокирующих записей в PostgreSQL на каждый тик. При одновременном `all_filters_ok` — снимок в `signals.card_snapshot_json`, строка в **`tracking_sessions`**, событие `triggered` в JSONL; тот же JSON дублируется в **`scanner_runtime._pending_signal_snapshots`** до конца сессии, чтобы каждая последующая запись в `signals` при повторных продакшн-сигналах получала `card_snapshot_json`. Запись в БД — точечно (lifecycle), не hot-path цикла. В JSON: `score`, `ok_count`, `tie_break_score`, **`scanner_tracked_since`**, **`scanner_filter_max_list`**, **`fire_meta`**, **`tracking_id`**, **`stat_href`** (страница `/admin/analytics/stat-<symbol>-<id>`). Telegram при тестовой ветке не затрагивается до реального сигнала.
- Уведомления: `utils.telegram_bot`, формат текста — `utils.generate_text` и шаблоны из настроек.
- При каждом вызове `_send_signal` → `_save_signal_to_db` в таблицу `signals` (PostgreSQL) попадает строка независимо от успеха Telegram-доставки; ошибка записи в БД не прерывает основной поток. Если задан непустой **`tracking_id`**, повторная вставка с тем же id пропускается (одна строка на сессию Scanner / posttracking); при `tracking_id is NULL` каждый вызов по-прежнему добавляет строку.
- **Scanner — кому не резать сессию:** множество `scanner_eligible` = top-N по score ∪ posttracking ∪ символы с **`all_filters_ok`** в текущем цикле. Им передаётся `prune_sessions_not_in_set`, и только для них выполняется ветка обогащения/ `mark_triggered` в `Consumer`. Иначе пара вне top-N по score, но с полным проходом фильтров, теряла сессию до trigger и попадала в БД без `card_snapshot_json`.
- **Scanner — сессия без trigger:** если ни у одного **включённого** фильтра нет `ok` (`no_enabled_filters_ok`), не сработавшая сессия удаляется из `_sessions`, с диска (JSONL) и из `tracking_sessions` (`remove_untriggered_session_and_artifacts`). После **trigger** при последующем «все выключены» посттрек продолжается (сэмплы, пока сессия жива). При **prune** сессии без trigger тоже удаляются с диска и из БД, а не помечаются `abandoned`.

## Админка (`admin/`)

- **Главная** (`/admin/`, **Обзор**): дашборд сводки скринеров, сигналов (в т.ч. за 24 ч), сессий аналитики (`tracking_sessions`), настроек Scanner runtime (`scanner_runtime_settings`) и компактных метрик процесса (subset из psutil / размер `app/`, как на «Система»); `GET /admin_api/dashboard/summary` — JSON для первой отрисовки и автообновления в браузере; `DashboardCustomView` как `index_view` при создании `Admin`, шаблон `dashboard.html`, агрегация в `app/admin/dashboard_summary.py` (один SQL-агрегат по счётчикам, `pg_stat` для оценки «всего» по `signals` как в списке сигналов, снимок метрик без `os.walk` размера каталога, краткий TTL в памяти воркера; клиент — `sessionStorage` для быстрого повторного показа).
- **starlette-admin** поверх SQLAlchemy engine: CRUD скринеров, просмотр логов, кастомная страница мониторинга, **страница сигналов**, **«Аналитика»** (`/admin/analytics`) — каталог сессий из `tracking_sessions` + ссылки на **Stat** (`/admin/analytics/stat-<slug>-<tracking_id>`), графики по выборкам из JSONL через `GET /admin_api/analytics/samples`; полная очистка статистики — `POST /admin_api/analytics/purge` (таблица `tracking_sessions`, каталог `app/statistics-data/`, сброс in-memory `scanner_runtime`). В строках `kind: sample` в JSONL есть **`last_price`** (last close из свечей оценки). На Stat: полупрозрачные столбцы **low–high за UTC‑минуту** (min/max `last_price` по сэмплам в минуте) на фоне, линии score/фильтров поверх.
- Сессии: `SessionMiddleware` с `secret_key=config.cypher_key`.
- `AdminAuthProvider`: всегда считает пользователя аутентифицированным (без проверки пароля).
- **Страница «Система»** (`/admin/monitoring`): UI с сеткой карточек и мини-графиками; `GET /admin_api/monitoring/metrics` — JSON (psutil + история). История CPU/RAM/диск и поминутный ряд размера каталога `app/` — **только в памяти процесса** (сброс при реперезапуске); размер каталога пересчитывается не чаще **60 с** (`app/admin/monitoring_metrics.py`). Переопределение корня диск-метрики: переменная окружения `MONITORING_APP_DIR`.
- **Страница сигналов** (`/admin/signals`): отображает историю сигналов в дизайне Telegram-сообщений; три источника — таблица `signals` в PostgreSQL, `signals_log.txt` или **режим «Тест»** (только live, без истории в БД). Real-time: `GET /admin_api/signals/stream?source=db|file|test` (`source=test` — очередь снимков из `test_signal_broadcast`); для БД/лога браузер переподключается при разрыве; пагинация 100/500/1000 — для БД и лога, в режиме «Тест» скрыта. Новые карточки подсвечиваются анимацией 3 с — «умная» подсветка через `IntersectionObserver` + события мыши: анимация начинается только когда карточка видна и пользователь активен. Кнопка прокрутки вверх содержит бейдж-счётчик непрочитанных (`#unread-badge`); клик вызывает `markAllAsRead()` — принудительно запускает анимацию на всех непрочитанных карточках через `card._forceRead()` и прокручивает страницу вверх. Сериализаторы `signal_orm_row_to_dict` и `parse_signals_log_line` включают поле `cmc_rank` — live-значение из `get_cmc_rank_for_symbol`; снимки «Тест» тоже содержат `cmc_rank`. **Режим БД:** фронт всегда использует горизонтальную вёрстку Scanner (`signal-card--test`): при непустом `card_snapshot_json` подставляется frozen-снимок; без снимка — тот же шаблон с текстом из БД и пояснением в блоке фильтров (`db_legacy_no_snapshot`). **Режим лог-файла:** при непустом `card_snapshot` в строке `signals_log.txt` — тот же горизонтальный layout; иначе — узкая legacy-карточка. В лог пишет `Consumer._send_signal` (поля `card_snapshot`, `tracking_id` в JSON, паритет с БД). API: `card_snapshot`, `render_as_scanner`, `stat_href`; `POST /admin_api/signals/purge?target=db` — только `signals`, `?target=log` — только `signals_log.txt`. SSE для `source=db` не обновляет карточки на месте как live Scanner (только новые строки сверху). Режим «Тест»: поле `mode: "test"`, `test_filters` — массив диагностики по фильтрам; фронт обновляет существующую карточку по стабильному `id` вида `test-{screener_id}-{symbol}`; карточка в шаблоне `signals.html` с классом `signal-card--test`: сетка колонок (тикер / текст / полоса фильтров / мета), полоса фильтров — равномерное распределение до ~5 колонок без горизонтальной прокрутки на десктопе. Лента пересортировывается по убыванию `score` (`data-test-score`, `reorderTestFeed`), при равенстве — `ok_count`, затем `tie_break_score`; затем обрезка до лимита видимых карточек (`trimTestFeedToMax`, ключ `localStorage` `signals_test_max_visible`). В тулбаре — счётчик «Онлайн» (`#test-feed-count`) и выбор максимума карточек (`#test-max-cards`).

## Интеграции

- **unicex**: биржи, типы рынков, WebSocket/клиенты. В Docker-образе подменяется файл `unicex/_base/websocket.py` на версию из репозитория (backoff при 403 и очистка очереди).
- **CoinMarketCap** (`utils/coinmarketcap_rank.py`): опционально, по API-ключу из окружения; без ключа ранги не обновляются (warning в логах).

## Логирование

- Основной поток: **loguru** → `app/logs/app.log` (ротация **10 MB**, до **10** архивов `app.YYYY-MM-DD_HH-MM-SS_usecs.log`, время в **Europe/Moscow**). Уровень: **`LOG_LEVEL`** в окружении (по умолчанию `INFO`), см. `config/logger.py`.
- Отладочные JSON-события: `config/debug_json_logger.py` → `app/logs/debug.log` (ротация **100 MB**, до **10** архивов `debug.YYYY-MM-DD_HH-MM-SS_usecs.log`, Москва; очередь).
- Сводный журнал сигналов и событий: `config/signals_log.py` → `app/logs/signals_log.txt` (ротация **10 MB**, архивы `signals_log.…txt`, Москва): в начале строки — метка времени (Москва), таб, JSON (`kind=signal` / `lifecycle`), см. `log_signals_event` и вызовы в `Consumer`, `Operator`, `__main__.py`.
- `debug.log`: аналогично — префикс времени (Москва) + таб + JSON-событие.

## Контейнеры

- `docker-compose.yaml` (запуск из каталога `app/`): сервис `postgres`, сервис `app` — `alembic upgrade head` и `uvicorn app.__main__:app`. Тома: код `app` примонтирован для разработки, `./logs` → `/app/logs`.
- Сборка: контекст родительской директории, `Dockerfile` в `app/Dockerfile`.

## Архитектурные преимущества и производительность

1. **Shared parser set на пару `(exchange, market_type)`**
   В `Operator` словарь `_parsers` индексируется ключом `(exchange, market_type)`. Для каждой уникальной пары создаётся ровно один `ParsersDTO`, а все скринеры с той же парой получают ссылку на этот общий набор парсеров.
   Это убирает дублирование WebSocket-подписок и фоновых parser-task на уровне каждого скринера. При добавлении второго и последующих скринеров на ту же биржу и тип рынка система не открывает второй комплект соединений и не держит вторую копию тех же рыночных буферов в RAM. Практический эффект: рост нагрузки по WebSocket и памяти определяется числом уникальных пар `(exchange, market_type)`, а не числом скринеров. Это улучшает вертикальное масштабирование в сценарии "много стратегий на одном рынке": дополнительный скринер в основном добавляет только свой `Consumer`, а не полный стек источников данных.

2. **Один `Consumer` на `settings.id` с hot-update настроек**
   В `Operator` активные consumer-ы хранятся по ключу `(settings.id, exchange, market_type)` в `_consumers`, а при очередном цикле синхронизации существующий экземпляр не пересоздаётся: вызывается `existing_consumer.update_settings(settings)`.
   Это даёт обновление параметров скринера без полного перезапуска процесса, без переподнятия общих парсеров и без повторного прогрева их состояния. Для event loop это важно тем, что изменение настроек не превращается в всплеск `stop/start` задач, отмен WebSocket-потоков и повторных подписок. Для WebSocket-слоя это снижает churn соединений. Для RAM и CPU это также выгодно: не создаются новые объекты Consumer/Parser там, где достаточно заменить `SettingsDTO`. Масштабирование получается более предсказуемым при частых изменениях конфигурации из админки: цена изменения настроек близка к цене обновления in-memory объекта, а не к полной пересборке конвейера.

3. **Проверки по символам вынесены в `ThreadPoolExecutor(max_workers=4)`**
   Каждый `Consumer` создаёт собственный `ThreadPoolExecutor(max_workers=4)`, а проверки символов запускаются через `loop.run_in_executor(...)`. В executor уходит `_symbol_check_pair`, внутри которого выполняется основная `_check_filters_for_symbol(...)` и, при необходимости, логика тестового снимка.
   Архитектурный смысл здесь не в "ускорении любой ценой", а в разгрузке основного event loop от большого числа синхронных вычислений по каждому символу. Event loop продолжает управлять async-задачами, WebSocket-парсерами, Telegram I/O и БД-операциями, пока тяжёлые проверки выполняются в рабочих потоках. Это уменьшает риск, что один длинный цикл фильтрации задержит обработку других async-событий. При этом линейный рост CPU throughput не гарантируется: итог зависит от профиля фильтров, доли Python CPU-bound работы, накладных расходов на переключение потоков и ограничений GIL. Но даже без линейного speedup схема обычно улучшает отзывчивость event loop и ограничивает "залипание" цикла Consumer на больших списках символов.

4. **Scanner/Test вычисления — при SSE или включённой статистике**
   В начале цикла `Consumer._check_filters()` вычисляется `test_enabled = test_stream_is_active() or scanner_runtime.should_compute_scanner_snapshot(...)` (флаг **`statistics_enabled`** в таблице `scanner_runtime_settings`, кэш с TTL ~3 с). Пока оба выключены, `evaluate_test_mode_snapshot` не вызывается и `broadcast_test_payload` не идёт в SSE. Если включена только статистика (без подписчика на `/admin_api/signals/stream?source=test`), снимки считаются для JSONL/трекинга, но SSE не рассылается — разгрузка сети/UI.
   Важная граница: базовая проверка фильтров всё равно выполняется для боевых сигналов; экономия на полном отключении — только на ветке scanner/test-диагностики, пока не нужен ни live-просмотр, ни сбор статистики.

5. **Запись в БД выполняется только на событие сигнала**
   `Consumer` не пишет промежуточные результаты проверки в PostgreSQL. Вставка в таблицу `signals` происходит только внутри `_send_signal()`, где после попытки отправки в Telegram вызывается `_save_signal_to_db(...)` — как для успешной отправки, так и для ошибки доставки; при непустом `tracking_id` дубликаты по тому же id не вставляются (см. п. «При каждом вызове `_send_signal`» выше).
   Это принципиально снижает write amplification: частота записей в БД зависит от числа реальных сигналов, а не от числа тиков, символов или циклов проверки. Для БД это означает меньше `INSERT`/`COMMIT`, меньше конкуренции за соединения и меньше рост таблицы на "шумовых" проходах фильтров. Для event loop и общей латентности это тоже полезно: основной цикл не обременён постоянным async I/O в PostgreSQL на каждом проходе. С точки зрения масштабирования такое решение лучше переносит расширение universe символов: увеличение количества проверяемых инструментов растит в первую очередь CPU-нагрузку на фильтрацию и объём данных в памяти, но не умножает линейно БД-нагрузку, пока частота реальных сигналов остаётся умеренной.

## Инварианты

- Один набор парсеров на пару (биржа, рынок); много скринеров на ту же пару **делят** один экземпляр парсеров.
- Смена настроек скринера подхватывается Operator без перезапуска всего процесса (в пределах реализованной логики обновления consumers).
