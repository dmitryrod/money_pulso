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
| `database/` | SQLAlchemy async engine, `SettingsORM`, `SignalORM`, репозитории, Alembic-миграции |
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
- **Режим «Тест» (админка):** если активен хотя бы один SSE-клиент `source=test` (`test_signal_broadcast.test_stream_is_active()`), в том же `run_in_executor` после `_check_filters_for_symbol` вызывается `evaluate_test_mode_snapshot` (`screener/test_mode_eval.py`) — гейты как у продакшена, затем независимые `Filter.process` по всем включённым фильтрам; при «хотя бы один ok» снимок уходит в `broadcast_test_payload` → очереди подписчиков SSE. В JSON: `score` — среднее signed-вкладов по фильтрам (`enrich_fulfillment_and_score`, `filter_score` в строках `test_filters`); `ok_count` и `tie_break_score` — для сортировки-развязки и диагностики (`compute_ok_count_and_tie_score`, `_tie_margin_for_row`). Поле **`scanner_tracked_since`** (ISO UTC) — момент первого попадания символа в ленту Scanner при открытом SSE; при сбое условий (снимок не формируется) время сбрасывается и при следующем входе начинается заново. Для каждого символа ведётся **`_scanner_filter_peaks`**: по строкам `test_filters` извлекается скаляр (`extract_peak_metric_for_scanner_row`), накапливается максимум за сессию Scanner; в payload добавляется **`scanner_filter_max_list`** для UI. Дополнительно **`_scanner_filter_prev_ok`** и **`_scanner_filter_fire`**: на фронте перехода `ok` false→true в строку `test_filters` добавляется **`fire_meta`** (`fire_at`, `fire_elapsed_ms` от старта отслеживания); при повторном срабатывании после падения `ok` метка обновляется. При выпадении из режима пики и fire-состояние для символа очищаются. Telegram и БД не затрагиваются.
- Уведомления: `utils.telegram_bot`, формат текста — `utils.generate_text` и шаблоны из настроек.
- При каждом сигнале `_save_signal_to_db` записывает строку в таблицу `signals` (PostgreSQL) независимо от успеха Telegram-доставки; ошибка записи в БД не прерывает основной поток.

## Админка (`admin/`)

- **starlette-admin** поверх SQLAlchemy engine: CRUD скринеров, просмотр логов, кастомная страница мониторинга, **страница сигналов**.
- Сессии: `SessionMiddleware` с `secret_key=config.cypher_key`.
- `AdminAuthProvider`: всегда считает пользователя аутентифицированным (без проверки пароля).
- **Страница сигналов** (`/admin/signals`): отображает историю сигналов в дизайне Telegram-сообщений; три источника — таблица `signals` в PostgreSQL, `signals_log.txt` или **режим «Тест»** (только live, без истории в БД). Real-time: `GET /admin_api/signals/stream?source=db|file|test` (`source=test` — очередь снимков из `test_signal_broadcast`); для БД/лога браузер переподключается при разрыве; пагинация 100/500/1000 — для БД и лога, в режиме «Тест» скрыта. Новые карточки подсвечиваются анимацией 3 с — «умная» подсветка через `IntersectionObserver` + события мыши: анимация начинается только когда карточка видна и пользователь активен. Кнопка прокрутки вверх содержит бейдж-счётчик непрочитанных (`#unread-badge`); клик вызывает `markAllAsRead()` — принудительно запускает анимацию на всех непрочитанных карточках через `card._forceRead()` и прокручивает страницу вверх. Сериализаторы `_signal_orm_to_dict` и `_parse_log_line` включают поле `cmc_rank` — live-значение из `get_cmc_rank_for_symbol`; снимки «Тест» тоже содержат `cmc_rank`. Режим «Тест»: поле `mode: "test"`, `test_filters` — массив диагностики по фильтрам; фронт обновляет существующую карточку по стабильному `id` вида `test-{screener_id}-{symbol}`; карточка в шаблоне `signals.html` с классом `signal-card--test`: сетка колонок (тикер / текст / полоса фильтров / мета), полоса фильтров — равномерное распределение до ~5 колонок без горизонтальной прокрутки на десктопе. Лента пересортировывается по убыванию `score` (`data-test-score`, `reorderTestFeed`), при равенстве — `ok_count`, затем `tie_break_score`; затем обрезка до лимита видимых карточек (`trimTestFeedToMax`, ключ `localStorage` `signals_test_max_visible`). В тулбаре — счётчик «Онлайн» (`#test-feed-count`) и выбор максимума карточек (`#test-max-cards`).

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

## Инварианты

- Один набор парсеров на пару (биржа, рынок); много скринеров на ту же пару **делят** один экземпляр парсеров.
- Смена настроек скринера подхватывается Operator без перезапуска всего процесса (в пределах реализованной логики обновления consumers).
