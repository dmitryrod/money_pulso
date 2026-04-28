# Money Pulso

Крипто-скринер (репозиторий: `money_pulso`): админка (FastAPI + PostgreSQL), фоновый сбор данных через **unicex**, фильтры и уведомления в **Telegram**.

## Быстрый старт (Docker)

Из **корня репозитория** (`money_pulso/`, рядом с каталогом `app/`):

```bash
docker compose up --build
```

Либо из каталога **`app/`** (тот же набор сервисов, см. `docker-compose.yaml`):

```bash
docker compose up --build
```

Остановка: `docker compose down`. Переменные окружения — из `.env` (шаблон: [.env.example](.env.example)).

Админка: `http://localhost:<APP_PORT>/admin/screeners/list` (по умолчанию `APP_PORT=8000`).

## Документация

Полное оглавление, архитектура, changelog, troubleshooting и гайд по скринеру: **[app/docs/README.md](docs/README.md)**.

Правила ведения доков: [SYSTEM_PROMPT.MD](docs/SYSTEM_PROMPT.MD).

## Миграции БД

В контейнере при старте выполняется `alembic upgrade head`. Локально: `uv run alembic upgrade head` из `app/`.
