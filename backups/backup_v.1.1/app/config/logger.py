from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from loguru import logger as _loguru_logger


LOG_LEVEL = "INFO"
LOG_DIR = Path(__file__).resolve().parents[1] / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)


def _configure_loguru() -> None:
    _loguru_logger.remove()
    _loguru_logger.add(
        LOG_DIR / "app.log",
        rotation="10 MB",
        retention=10,  # хранить только 10 последних ротированных файлов
        level=LOG_LEVEL,
        enqueue=True,
        backtrace=True,
        diagnose=False,
        format="{time:DD.MM HH:mm:ss}|{level}| {message}",
    )


_configure_loguru()


def get_logger(name: str | None = None):
    """Возвращает объект логгера loguru."""
    if name:
        return _loguru_logger.bind(logger=name)
    return _loguru_logger


logger = get_logger()

