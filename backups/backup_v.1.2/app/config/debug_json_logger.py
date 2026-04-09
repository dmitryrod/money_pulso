from __future__ import annotations

import asyncio
import json
import logging
import queue
import traceback
from datetime import datetime, timezone
from logging.handlers import QueueHandler, QueueListener, RotatingFileHandler
from pathlib import Path
from typing import Any


LOG_DIR = Path(__file__).resolve().parents[1] / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

DEBUG_LOG_PATH = LOG_DIR / "debug.log"


_queue: queue.Queue[logging.LogRecord] = queue.Queue(maxsize=250_000)
_listener: QueueListener | None = None


class _JsonLineFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:  # noqa: A003
        msg = record.getMessage()
        # Если msg уже JSON (строка) — просто отдаем как есть.
        # Но гарантируем 1 строку.
        return msg.replace("\n", "\\n")


def _ensure_listener_started() -> None:
    global _listener
    if _listener is not None:
        return

    file_handler = RotatingFileHandler(
        DEBUG_LOG_PATH,
        maxBytes=100 * 1024 * 1024,  # 100MB
        backupCount=10,
        encoding="utf-8",
    )
    file_handler.setFormatter(_JsonLineFormatter())

    _listener = QueueListener(_queue, file_handler, respect_handler_level=True)
    _listener.daemon = True
    _listener.start()


def get_debug_json_logger() -> logging.Logger:
    _ensure_listener_started()
    logger = logging.getLogger("debug_json")
    if not any(isinstance(h, QueueHandler) for h in logger.handlers):
        logger.setLevel(logging.INFO)
        logger.propagate = False
        logger.addHandler(QueueHandler(_queue))
    return logger


def _utc_ts() -> str:
    # ISO 8601 с миллисекундами, UTC
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def log_debug_event(
    *,
    level: str,
    screener_name: str,
    screener_id: int,
    exchange: str,
    market_type: str,
    event: str,
    symbol: str | None,
    payload: dict[str, Any] | None,
    run_id: str,
    cycle_id: int,
    exc: BaseException | None = None,
) -> None:
    """
    Пишет 1 JSON-строку в app/logs/debug.log.
    Формат: ts, screener_name, screener_id, level, exchange, market_type, event, symbol, payload, run_id, cycle_id
    """
    logger = get_debug_json_logger()

    data: dict[str, Any] = {
        "ts": _utc_ts(),
        "screener_name": screener_name,
        "screener_id": screener_id,
        "level": level,
        "exchange": exchange,
        "market_type": market_type,
        "event": event,
        "symbol": symbol,
        "payload": payload or {},
        "run_id": run_id,
        "cycle_id": cycle_id,
    }

    if exc is not None:
        data["payload"] = dict(data["payload"] or {})
        data["payload"]["exception"] = {
            "type": type(exc).__name__,
            "message": str(exc),
            "stacktrace": "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
        }

    try:
        line = json.dumps(data, ensure_ascii=False, default=str)
    except Exception as dump_exc:
        fallback = {
            "ts": _utc_ts(),
            "screener_name": screener_name,
            "screener_id": screener_id,
            "level": "error",
            "exchange": exchange,
            "market_type": market_type,
            "event": "debug_log_dump_error",
            "symbol": symbol,
            "payload": {
                "original_event": event,
                "dump_error": str(dump_exc),
            },
            "run_id": run_id,
            "cycle_id": cycle_id,
        }
        line = json.dumps(fallback, ensure_ascii=False, default=str)

    try:
        logger.info(line)
    except Exception:
        # Очередь QueueHandler переполнена или запись сломалась — не роняем consumer.
        logging.getLogger(__name__).exception("debug_json logger.info failed")


async def log_debug_event_async(**kwargs: Any) -> None:
    """Тяжёлый json.dumps + запись в очередь — вне event loop, чтобы не голодали websocket-коллбеки."""

    def _run() -> None:
        log_debug_event(**kwargs)

    await asyncio.to_thread(_run)

