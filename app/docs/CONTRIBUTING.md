# Участие в разработке

## Требования

- **Python ≥ 3.13** (`pyproject.toml`).
- Менеджер зависимостей: в Docker используется **uv** (`uv sync`, `uv run`).

## Локальная работа (без Docker)

Из каталога `app/`:

```bash
uv sync
uv run uvicorn app.__main__:app --reload --host 127.0.0.1 --port 8000
```

Нужен доступный PostgreSQL; переменные — как в `.env.example`. Миграции:

```bash
uv run alembic upgrade head
```

## Docker

Из каталога `app/`:

```bash
docker compose up --build
```

Контекст сборки — родительская папка относительно `app/` (см. `docker-compose.yaml`).

## Линтинг

- Конфиг **Ruff**: `app/ruff.toml`.
- Запуск из `app/`:

```bash
uv run ruff check .
uv run ruff format .
```

Тесты и миграции в исключениях линтера — см. `ruff.toml`.

## Тесты

- Каталог `app/tests/` (парсеры и др.).
- Запуск (пример):

```bash
uv run pytest app/tests -q
```

При отсутствии `pytest` в зависимостях добавьте его в окружение или используйте `uv run python -m pytest` после добавления dev-зависимости.

## Стиль кода

- Соответствовать существующим модулям: типы, именование, структура пакетов.
- Не коммитить секреты; для примеров — `.env.example` и плейсхолдеры.

## Документация

После изменений, затрагивающих поведение, CLI, конфиг или контракты — обновлять файлы по матрице в [SYSTEM_PROMPT.MD](SYSTEM_PROMPT.MD).
