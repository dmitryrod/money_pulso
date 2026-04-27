# Money Pulso

Крипто-скринер (репозиторий: `money_pulso`): админка (FastAPI + PostgreSQL), фоновый сбор данных через **unicex**, фильтры и уведомления в **Telegram**.

## Быстрый старт (Docker)

Из каталога **`app/`** (родитель — корень репозитория с контекстом сборки):

```bash
docker compose up --build
```

Остановка: `docker compose down`. Переменные окружения — из `.env` (шаблон: [.env.example](.env.example)).

Админка: `http://localhost:<APP_PORT>/admin/screeners/list` (по умолчанию `APP_PORT=8000`).

## Документация

Полное оглавление, архитектура, changelog, troubleshooting и гайд по скринеру: **[app/docs/README.md](docs/README.md)**.

Правила ведения доков: [SYSTEM_PROMPT.MD](SYSTEM_PROMPT.MD).

## Миграции БД

В контейнере при старте выполняется `alembic upgrade head`. Локально: `uv run alembic upgrade head` из `app/`.
