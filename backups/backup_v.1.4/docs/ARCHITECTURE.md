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
- Уведомления: `utils.telegram_bot`, формат текста — `utils.generate_text` и шаблоны из настроек.
- При каждом сигнале `_save_signal_to_db` записывает строку в таблицу `signals` (PostgreSQL) независимо от успеха Telegram-доставки; ошибка записи в БД не прерывает основной поток.

## Админка (`admin/`)

- **starlette-admin** поверх SQLAlchemy engine: CRUD скринеров, просмотр логов, кастомная страница мониторинга, **страница сигналов**.
- Сессии: `SessionMiddleware` с `secret_key=config.cypher_key`.
- `AdminAuthProvider`: всегда считает пользователя аутентифицированным (без проверки пароля).
- **Страница сигналов** (`/admin/signals`): отображает историю сигналов в дизайне Telegram-сообщений; два источника — таблица `signals` в PostgreSQL или `signals_log.txt`; real-time обновление через SSE (`GET /admin_api/signals/stream?source=db|file`), браузер автоматически переподключается при разрыве; пагинация 100/500/1000 записей на странице; новые карточки подсвечиваются анимацией 3 с — «умная» подсветка через `IntersectionObserver` + события мыши: анимация начинается только когда карточка видна и пользователь активен. Кнопка прокрутки вверх (`#scroll-top-wrap`) содержит бейдж-счётчик непрочитанных (`#unread-badge`); клик вызывает `markAllAsRead()` — принудительно запускает анимацию на всех непрочитанных карточках через `card._forceRead()` и прокручивает страницу вверх. Оба сериализатора (`_signal_orm_to_dict`, `_parse_log_line`) включают поле `cmc_rank` — live-значение из `get_cmc_rank_for_symbol` на момент запроса; фронт использует его как фолбэк, если ранг не попал в `telegram_text` (например, при старте контейнера CMC-кеш не был заполнен).

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
