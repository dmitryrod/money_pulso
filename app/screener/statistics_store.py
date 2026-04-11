"""Append-only JSONL для сессий Scanner (statistics-data)."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_STAT_ROOT = Path(__file__).resolve().parents[1] / "statistics-data"


def _ensure_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def session_file_path(
    *,
    exchange: str,
    market_type: str,
    symbol: str,
    tracking_id: str,
    day: datetime | None = None,
) -> Path:
    """Относительный к app/ путь: statistics-data/YYYY-MM-DD/{exchange}-{market}-{symbol}-{id}.jsonl"""
    d = day or datetime.now(timezone.utc)
    day_s = d.strftime("%Y-%m-%d")
    ex = exchange.lower().replace(" ", "_")
    mt = market_type.lower().replace(" ", "_")
    sym = symbol.upper().replace("/", "")
    name = f"{ex}-{mt}-{sym}-{tracking_id}.jsonl"
    return _STAT_ROOT / day_s / name


def append_line(path: Path, obj: dict[str, Any]) -> None:
    """Синхронная запись одной NDJSON-строки (вызывать через asyncio.to_thread)."""
    _ensure_dir(path)
    line = json.dumps(obj, ensure_ascii=False, default=str) + "\n"
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line)


def relative_stat_path(path: Path) -> str:
    """Путь относительно каталога app/."""
    try:
        app_root = Path(__file__).resolve().parents[1]
        return str(path.relative_to(app_root)).replace(os.sep, "/")
    except ValueError:
        return str(path)
