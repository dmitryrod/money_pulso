"""Интерфейс доступа к конфигурации и логированию."""

__all__ = [
"get_logger",
"logger",
"log_debug_event",
"log_debug_event_async",
"config",
]

from .config import config
from .logger import get_logger, logger
from .debug_json_logger import log_debug_event, log_debug_event_async