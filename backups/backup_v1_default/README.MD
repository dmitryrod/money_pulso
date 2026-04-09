# Paid Screener

## Инструкция по работе со скринером
Скринер ищет монеты, которые подходят под ваши условия, и отправляет сигнал в Telegram. Ниже короткая и понятная инструкция,
чтобы настроить все без лишних сложностей.
Быстрый старт:
    1. Откройте раздел Скринер в админке.
    2. Создайте новый скринер.
    3. Выберите биржу и тип рынка (спот или фьючерсы).
    4. Заполните хотя бы один фильтр (все фильтры заполнять не обязательно).
    5. Укажите ID Telegram-чата и Токен Telegram-бота. Их можно получить в и соответственно.
    6. Сохраните - скринер начнет работу.
Общие настройки:
    • Включить скринер - главный переключатель. Если выключено, сигналы не будут приходить.
    • Биржа - откуда берутся данные и где будут строиться ссылки в сигнале.
    • Тип рынка - с какого типа рынка берутся данные для анализа.
    • Белый список - если заполнен, скринер анализирует только эти тикеры.
    • Черный список - тикеры, которые всегда игнорируются.
Фильтры: что они означают:
    Каждый фильтр - это условие. Скринер отправляет сигнал, если монета проходит все включенные условия.
    Фильтр "Рост цены": Цена выросла на заданный процент за выбранный интервал времени.
    Фильтр "Открытый интерес": Открытый интерес вырос на заданный процент или сумму в долларах. Работает только на фьючерсах.
    Фильтр "Ставка финансирования": Фандинг попадает в заданный диапазон. Работает только на фьючерсах.
    Фильтр "Множитель объема": Текущий объем в Х раз больше среднего за сутки за тот же интервал времени.
    Фильтр "Ликвидации": Сумма ликвидаций за интервал превышает указанное значение. Работает только на фьючерсах.
    Фильтр "Суточный объем": Отсекает монеты с слишком маленьким или слишком большим суточным объемом.
    Фильтр "Изменение цены за сутки": Отсекает монеты которые слишком сильно или слишком мало изменились за последние сутки.
    Важно: чтобы фильтр считался включенным, заполните все его обязательные поля. Например, для роста цены нужны и интервал, и процент.
Уведомления в Telegram:
    • ID Telegram-чата для уведомлений - ID чата, куда приходят сигналы. Можно узнать через @username_to_id bot
    • Токен Telegram-бота - токен вашего Telegram-бота, берется у @BotFather.
    • Максимум сигналов на тикер в сутки - защитит от спама по одной монете.
    • Таймаут между сигналами - минимальное время между повторными сигналами по одному тикеру.
    • Отладка - добавляет в сообщение технические данные. Обычно выключено.
Как читать сигнал:
    В сигнале вы увидите причины срабатывания (условия) и текущие данные по монете: фандинг, изменение цены за 24ч, объем,
    последнюю цену. Также будут ссылки на биржу, CoinGlass и TradingView.
    Подсказка: сигнал - это не рекомендация к покупке или продаже, а повод посмотреть на монету.
Частые ошибки новичков:
    • Не выбран ни один фильтр - скринер ничего не ищет.
    • Выбран спот, но заполнены фильтры фьючерсов - такие условия не сработают.
    • Слишком жесткие значения или большое количество фильтров - сигналы приходят редко или совсем не приходят.
    • Слишком мягкие значения или малое количество фильтров - сигналов слишком много.
    • Белый список заполнен случайно - вы видите только выбранные тикеры.
    • Формула множителя объема: (объем за интервал / длительность интервала) / (суточный объем / 86400)
    • Для биржи Binance минимальный интервал для фильтра открытого интереса = 40 секунд
    • На бирже Aster не поддерживается спотовый рынок
    • Для каждого скринера желательно использовать разные токены Telegram бота, чтобы избежать лимитов от API Telegram



## Архитектура
В одной из версий фильтры были переписаны с Python на С, поэтому теперь можно создавать больше скринеров на одно ядро сервера.
alembic      # Делает миграцию

# Команды
dc down -v ; make create-migrations   # снести миграции docker-compose down -v ; make create-migrations
dc up                                 # Запуск приложения docker-compose up
"Enter migration massage:" initial    # инициализация
make migrate                          # создание миграции


Логи из терминала после запуска приложения:
paid-screener git:(main) dc up
Running 15/15
postgres Pulled
2a80b8df8f70 Pull complete
26f3966302f5 Pull complete
d637807aba98 Pull complete
6be5ff533868 Pull complete
48bb3c3185f6 Pull complete
91bf75daf7f5 Pull complete
66cf8f189b0d Pull complete
0062edb7bb84 Pull complete
12cd95217c0c Pull complete
49d636a047b4 Pull complete
8401b2c82bf9 Pull complete
00a8b15719db Pull complete
34f7c774a5db Pull complete
08724fee5eb4 Pull complete
Compose now can delegate build to bake for better performances
Just set COMPOSE_BAKE=true
[+] Building 0.9s (2/3)
[app internal] load build definition from Dockerfile
transferring dockerfile: 594B
=>[app internal] load metadata for docker.io/library/python:3.13-slim
=>[app auth] library/python:pull token for registry-1.docker.io
=> [app internal] load .dockerignore
=> transferring context: 648B
=> [app 1/7] FROM docker.io/library/python:3.13-slim@sha256:51e1a0a317fdb6e170dc791bbeae63fac5272c82f43958ef74a34e170c6f8b18
=> resolve docker.io/library/python:3.13-slim@sha256:51e1a0a317fdb6e170dc791bbeae63fac5272c82f43958ef74a34e170c6f8b18
=> sha256:3310e4c0a9dc07e65205534e74daeee1d62ca99453b259bc7c0a10ad6b6b802a11,72MB / 11.72MB
=> sha256.4cc556234b57f37a358cdc5528347cb750f2ca9fb6d2e8f6beb8e5ac020c69e3 248B / 248B
=> sha256:a390baeefb5b4121f252f65d48df6ca3ebee458cce1f4cb8d1da53707dfb4726 1.27MB / 1.27MB
=> extracting sha256:a390baeefb5b4121f252f65d48df6ca3ebee458cce1f4cb8d1da53707dfb4726
=> extracting sha256:3310e4c0a9dc07e65205534e74daeee1d62ca99453b259bc7c0a10ad6b6b802a
=> extracting sha256:4cc556234b57f37a358cdc5528347cb750f2ca9fb6d2e8f6beb8e5ac020c69e3
=> [app internal] load build context
=> transferring context: 487.73kB
=> [app 2/7] WORKDIR /app
=> [app 3/7] RUN pip install --no-cache-dir uv
=> [app 4/7] COPY uv.lock pyproject.toml /app/
=> [app 5/7] RUN uv sync
=> [app 6/7] COPY alembic.ini /app/alembic.ini
=> [app 7/7] COPY app /app/app
=> [app] exporting to image
=> [app] exporting layers
=> exporting manifest sha256:b83216fc5197ae7892fbe69c64598ba33632e553c963fe2c8ba893ff08b1bea8
=> exporting config sha256:a4b27f690624309eb1b682a1d6e7ff72d39d596c90334dc8d82e64e81477ed96
=> exporting attestation manifest sha256:686d494e6d03e37e9e781ad5e1fddd447cc365c0a43a145f30f15928515c87e5
=> exporting manifest list sha256:4c0263887a5db40c7f98b0dace2808721ae65622f3fd34c0f92b301c235703ed
=>  naming to docker.io/library/paid-screener-app:latest
=>  unpacking to docker.io/library/paid-screener-app:latest
=> [app] resolving provenance for metadata file
[+] Running 4/5
app Built
Network paid-screener_default Created
Volume "paid-screener_postgres_data" Created
Container paid-screener-postgres-1 Created
Container paid-screener-app-1  Creating
Attaching to app-1, postgres-1
postgres-1 | The files belonging to this database system will be owned by user "postgres".
postgres-1 | This user must also own the server process.
postgres-1 | 
postgres-1 | The database cluster will be initialized with locale "en_US.utf8".
postgres-1 | The default database encoding has accordingly been set to "UTF8".
postgres-1 | The default text search configuration will be set to "english".
postgres-1 | 
postgres-1 | Data page checksums are disabled.
postgres-1 | 
postgres-1 | fixing permissions on existing directory /var/lib/postgresql/data … ok
postgres-1 | creating subdirectories … ok
postgres-1 | selecting dynamic shared memory implementation … posix
postgres-1 | selecting default max_connections … 100
postgres-1 | selecting default shared_buffers … 128MB
postgres-1 | selecting default time zone … Etc/UTC
postgres-1 | creating configuration files … ok
postgres-1 | running bootstrap script … ok
и тд.
app-1      | INFO [alembic.runtime.migration] Context impl PostgresqlImpl.
app-1      | INFO [alembic.runtime.migration] Will assume transactional DDL.
app-1      | INFO [alembic.runtime.migration] Running upgrade -> fdbd484b49b6, initial
app-1      | INFO:Started server process [17]
app-1      | Waiting for application startup.
app-1      | 18.01 13:40:59|INFO| Admin panel startup! Environment: development
app-1      | 18.01 13:40:59| DEBUG| Admin panel url: http://127.0.0.1:8000/admin
app-1      | INFO:Application startup complete.
app-1      | INFO:Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C toquit)