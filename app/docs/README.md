# Документация Money Pulso

Канонические материалы по приложению в `app/docs/`. Код и точка входа — в каталоге `app/` (см. [SYSTEM_PROMPT.MD](SYSTEM_PROMPT.MD) для правил сопровождения доков).

## Навигация

| Документ | Содержание |
|----------|------------|
| [README.md](README.md) | Это оглавление и краткое руководство пользователя |
| [CHANGELOG.md](CHANGELOG.md) | Версии и заметные изменения поведения |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Потоки данных, модули, интеграции, архитектурные преимущества и производительность |
| [DESIGN.md](DESIGN.md) | Текущее состояние frontend, design tokens и направление редизайна для Google Stitch |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Окружение разработчика, проверки, стиль |
| [ROADMAP.md](ROADMAP.md) | Планы (не дублирует историю из CHANGELOG) |
| [TODO.md](TODO.md) | Отложенные задачи из активных планов (исторический бэктест и др.) |
| [troubleshooting.md](troubleshooting.md) | Симптом → причина → шаги |
| [marketing/](marketing/README.md) | Позиционирование, ICP, голос бренда (канон для маркетинга) |

Быстрый старт установки и Docker: [../README.MD](../README.MD).

Переменные окружения (без секретов): [../.env.example](../.env.example).

### Презентации Marp (инструменты)

**Где лежит дек:** исходники — Markdown в **`presentations/`** (см. `.cursor/config.json` → `presentations.source`). Актуальный пример: `presentations/russia-economy-2022-2026.md` — CSV в `presentations/sample-data/{gdp-growth,cpi-yoy,cbr-key-rate,value-added-share}.csv`, PNG — `presentations/assets/chart-{gdp,cpi,key-rate,sectors}.png`, обложка (AI/метафора) — `presentations/assets/generated/cover-economy.png`. Сборка **pptx** / **pdf** / **html** — в **`presentations/dist/`** (`presentations.output`). Оркестрация агентов и скилл — `.cursor/skills/marp-slide/SKILL.md`, ассеты — `.cursor/docs/CREATING_ASSETS.md`.

**Графики CSV → PNG (`chart_from_csv`):** в каталоге `app/` установить extra **`presentations`** (`matplotlib`): `uv sync --extra presentations`. Из **корня репозитория** (где лежат `app/` и `presentations/`):

`uv run --project app python presentations/tools/chart_from_csv.py presentations/sample-data/gdp-growth.csv -o presentations/assets/chart-gdp.png --title "ВВП РФ, % г/г" --dark`

(`--no-dark` — светлая тема; `--kind bar` — столбцы; путь `-o` любой под каталогом `presentations/`.) Реализация: модуль `presentations/chart_from_csv.py` (корень репо), обёртка CLI — `presentations/tools/chart_from_csv.py`. В `pyproject.toml` также есть extra `presentations-plotly`; фактический рендер в CLI сейчас через **`matplotlib`**. Внешние API картинок (Polza и т.д.) — только для обложек/метафор, не для точных рядов — см. скилл marp-slide.

**Сборка pptx (`npx marp`):** из корня репозитория, с зависимостью `@marp-team/marp-cli` из корневого `package.json`:

`npx @marp-team/marp-cli presentations/russia-economy-2022-2026.md -o presentations/dist/russia-economy-2022-2026.pptx --pptx --no-stdin --allow-local-files`

(или `--pdf` / `--html`; на Windows у `npx` нужен `--no-stdin`, а для локальных PNG/SVG — `--allow-local-files`). Пример выхода для дека выше: `presentations/dist/russia-economy-2022-2026.pptx` — см. [CHANGELOG.md](CHANGELOG.md).

**Токены и Polza:** канонический спек — `presentations/DESIGN_TOKENS.md`; сырой Stitch snapshot для этого дека — `presentations/stitch-russia-economy-deck-raw.tokens.json`. Генерация картинок через Polza — скрипт `presentations/scripts/polza_marp_images.py` (подкоманда `generate`, функция `generate_image_polza`); в оркестрации агентов — **`.cursor/agents/imager.md`**, **`designer`** только планирует и делегирует. Ключи `POLZA_API_KEY` / `POLZA_AI_API_KEY`, опционально `POLZA_BASE_URL`, **`POLZA_MODEL`** — см. `app/.env.example`. Обложки — **локальные** PNG под `presentations/assets/generated/`. См. `CHANGELOG.md` и `.cursor/docs/CREATING_ASSETS.md`.

**Типовой пайплайн для дека Russia 2022-2026:**

`python presentations/tools/chart_from_csv.py presentations/sample-data/gdp-growth.csv -o presentations/assets/chart-gdp.png --title "ВВП РФ, % г/г" --dark`

`npx @marp-team/marp-cli presentations/russia-economy-2022-2026.md -o presentations/dist/russia-economy-2022-2026.pptx --pptx --no-stdin --allow-local-files`

---

## Краткое руководство по скринеру

Скринер отбирает инструменты по условиям; при настроенном Telegram дополнительно шлёт уведомления.

1. Откройте в админке раздел **Скринеры**.
2. Создайте скринер: биржа, тип рынка (спот / фьючерсы), при необходимости белый/чёрный список.
3. Заполните **хотя бы один фильтр** полностью (все обязательные поля) — иначе условий нет.
4. **Telegram (необязательно):** токен бота и ID чата в карточке скринера и/или дефолты `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` в `.env` (см. `.env.example`). Нужны **оба** значения, иначе отправки нет — скринер всё равно работает, сигналы пишутся в БД и `signals_log.txt`.
5. Включите скринер и сохраните.

**Фильтры (логика):** сигнал возможен, если инструмент проходит **все включённые** фильтры. Фьючерсные фильтры (фандинг, OI, ликвидации) на споте не применимы.

**Подсказки:**

- Формула множителя объёма: `(объём за интервал / длительность интервала) / (суточный объём / 86400)`.
- Для Binance минимальный интервал фильтра открытого интереса — порядка 40 с (ограничение стека данных).
- Aster: спот может быть недоступен в зависимости от биржи в `unicex`.
- Разные скринеры лучше вешать на **разные** боты Telegram, чтобы не упираться в лимиты API.

**Важно:** сигнал — не торговая рекомендация, а повод вручную посмотреть рынок.

---

## Админка и API

- UI: `http://localhost:<APP_PORT>/admin/` — **Обзор** (дашборд сводки); список скринеров: `/admin/screeners/list`; **Аналитика** Scanner: `/admin/analytics`.
- **Вход:** форма логина/пароля (`/admin/login`). Учётные данные полного доступа: **`ADMIN_LOGIN`** / **`ADMIN_PASSWORD`** (env). Опционально публичный демо-вход: **`ADMIN_DEMO_ENABLED=1`** и пара **`DEMO_LOGIN`** / **`DEMO_PASSWORD`** — сессия с ролью `demo` (ограничения: нет CRUD скринеров, нет мутаций `global-debug` / `runtime-settings` / `signals/purge`, пункт **Логи** скрыт и недоступен; страница **Сигналы** — только просмотр и фиксированные параметры Scanner в UI; **Аналитика** и **Система** без доп. ограничений). **`SessionMiddleware`** один на корневом `app`; данные сессии хранятся в **подписанной cookie** (роль в **`SESSION_ROLE_KEY`**, см. `app/admin/roles.py`), у **каждого браузера свой** cookie — несколько посетителей с **одной и той же парой** demo не конфликтуют: состояние не привязано к строке `username` без id сессии. Реальные **`ADMIN_*`** в публичных инструкциях не публикуйте. Если Chrome показывает «Смените пароль» после входа — это проверка браузера на утечки, не баг админки; см. [troubleshooting.md](troubleshooting.md). Масштабирование нескольких процессов: см. тот же файл и [ARCHITECTURE.md](ARCHITECTURE.md) (раздел админки).
- Доп. endpoints: `GET/POST /admin_api/screeners/global-debug` — массовое включение/выключение отладки по скринерам; JS подключается на странице списка скринеров.

Подробнее об устройстве системы и влиянии архитектуры на производительность: [ARCHITECTURE.md](ARCHITECTURE.md).

**Логи** (ротация, московское время в именах архивов): `app/logs/app.log`, `debug.log`, **`signals_log.txt`** — единый журнал сигналов Telegram и событий жизненного цикла; детали в разделе «Логирование» в [ARCHITECTURE.md](ARCHITECTURE.md).
