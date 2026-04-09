"""Точка входа FastAPI-приложения."""

import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from unicex import start_exchanges_info

from .admin import register_admin_routes
from .config import config, logger
from .schemas import EnvironmentType
from .screener import Operator
from .utils import start_support_task


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения."""
    # Launch logs
    logger.info (f"Admin panel startup! Environment: {config.environment}")
    if config.environment == EnvironmentType.DEVELOPMENT:
        logger.debug("Admin panel url: http://127.0.0.1:8000/admin")

    # Start exchanges info
    await start_exchanges_info()
    
    # Register admin routes
    register_admin_routes(app)

    # Create and start screener operator
    operator = Operator()
    asyncio.create_task(operator.start())

    # Start supporting task
    support_task = start_support_task

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