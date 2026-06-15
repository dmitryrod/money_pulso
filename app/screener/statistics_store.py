"""Append-only JSONL для сессий Scanner (statistics-data)."""

from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_STAT_ROOT = Path(__file__).resolve().parents[1] / "statistics-data"


def purge_statistics_data_files() -> int:
    """Удаляет всё содержимое ``app/statistics-data`` и пересоздаёт пустой каталог.

    Returns:
        Число удалённых файлов (до удаления дерева).
    """
    if not _STAT_ROOT.exists():
        _STAT_ROOT.mkdir(parents=True, exist_ok=True)
        return 0
    n_files = sum(1 for p in _STAT_ROOT.rglob("*") if p.is_file())
    shutil.rmtree(_STAT_ROOT)
    _STAT_ROOT.mkdir(parents=True, exist_ok=True)
    return n_files


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


def app_root_dir() -> Path:
    """Корень каталога ``app/``."""
    return Path(__file__).resolve().parents[1]


def relative_stat_path(path: Path) -> str:
    """Путь относительно каталога app/."""
    try:
        return str(path.relative_to(app_root_dir())).replace(os.sep, "/")
    except ValueError:
        return str(path)


def absolute_stat_path(rel_path: str) -> Path:
    """Относительный путь из БД/session_meta → абсолютный Path под ``app/``."""
    return app_root_dir() / rel_path.replace("/", os.sep)


def resolve_statistics_jsonl(
    rel_path: str,
    *,
    tracking_id: str | None = None,
) -> Path | None:
    """Ищет JSONL сессии: сначала ``rel_path``, иначе ``*{tracking_id}.jsonl`` в ``statistics-data``."""
    primary = absolute_stat_path(rel_path)
    if primary.is_file():
        return primary
    if not tracking_id:
        return None
    stat_root = app_root_dir() / "statistics-data"
    if not stat_root.is_dir():
        return None
    matches = list(stat_root.rglob(f"*{tracking_id}.jsonl"))
    if not matches:
        return None
    if len(matches) == 1:
        return matches[0]
    return max(matches, key=lambda p: p.stat().st_mtime)
