"""Точка входа FastAPI-приложения."""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import Response
from sqlalchemy import text
from unicex import start_exchanges_info

from .admin import register_admin_routes
from .config import config, logger
from .database import Base, Database
from .schemas import EnvironmentType
from .screener import Operator
from .utils import start_support_task
from .utils.connectivity import is_transient_network_error, wait_for_internet


def _add_lq_min_amount_pct_if_missing(sync_conn):
    """Добавляет колонку lq_min_amount_pct в settings, если её нет (миграция без Alembic)."""
    sync_conn.execute(text("ALTER TABLE settings ADD COLUMN IF NOT EXISTS lq_min_amount_pct DOUBLE PRECISION"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения."""
    # Launch logs
    logger.info (f"Admin panel startup! Environment: {config.environment}")

    # Создаём таблицы, если их ещё нет (для чистого БД / Docker без миграций)
    while True:
        try:
            async with Database.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
                await conn.run_sync(_add_lq_min_amount_pct_if_missing)
            break
        except Exception as exc:
            logger.exception("Database init failed: {}", exc)
            if is_transient_network_error(exc):
                await wait_for_internet(logger=logger, log_name="database_init")
            else:
                raise
    if config.environment == EnvironmentType.DEVELOPMENT:
        logger.debug("Admin panel url: http://127.0.0.1:8000/admin")

    # Start exchanges info (унифицированные метаданные бирж; при обрыве сети — ждём)
    while True:
        try:
            await start_exchanges_info()
            break
        except Exception as exc:
            logger.exception("start_exchanges_info failed: {}", exc)
            if is_transient_network_error(exc):
                await wait_for_internet(logger=logger, log_name="unicex_exchanges_info")
            else:
                raise
    
    # Register admin routes
    register_admin_routes(app)

    # Create and start screener operator
    operator = Operator()
    asyncio.create_task(operator.start())

    # Start supporting task (фон, можно не ждать)
    support_task = start_support_task()

    # Give control to FastAPI
    yield

    # Stop screener operator
    await operator.stop()

    # Shutdown logs
    logger.info ("Admin panel shutdown!")


# Main FastAPI object
app = FastAPI(
    lifespan=lifespan,
    **{
        "docs_url": None,
        "redoc_url": None,
        "openapi_url": None,
    }
    if config.environment == EnvironmentType.PRODUCTION
    else {}, # type: ignore
)


@app.get("/.well-known/appspecific/com.chrome.devtools.json")
def _chrome_devtools_well_known() -> Response:
    """Chrome DevTools запрашивает этот URL; отдаём 204, чтобы не светить 404 в логах."""
    return Response(status_code=204)