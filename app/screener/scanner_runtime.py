"""Глобальный runtime Scanner: настройки из БД, top-N, JSONL samples, tracking_sessions."""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.database import Database
from app.database.models import ScannerRuntimeSettingsORM, TrackingSessionORM
from app.screener.statistics_store import append_line, relative_stat_path, session_file_path


@dataclass
class ScannerRuntimeCache:
    max_cards: int = 10
    posttracking_minutes: int = 30
    cooldown_hours: int = 24
    statistics_enabled: bool = True
    last_refresh_monotonic: float = 0.0


_cache = ScannerRuntimeCache()
_refresh_lock = asyncio.Lock()
_REFRESH_INTERVAL_SEC = 3.0


def bump_cache_refresh() -> None:
    """Форсирует следующую подгрузку настроек из БД."""
    _cache.last_refresh_monotonic = 0.0

# (screener_id, symbol) -> session
@dataclass
class _SessionState:
    tracking_id: str
    entered_monotonic: float
    triggered: bool = False
    posttracking_until: float | None = None
    statistics_path: str | None = None
    last_sample_wall: float = 0.0
    completion_emitted: bool = False


_sessions: dict[tuple[int, str], _SessionState] = {}
_manual_close_ids: set[str] = set()
_cooldown_until: dict[tuple[int, str], float] = {}


async def maybe_refresh_cache() -> None:
    """Периодически подгружает настройки из БД."""
    now = time.monotonic()
    if now - _cache.last_refresh_monotonic < _REFRESH_INTERVAL_SEC:
        return
    async with _refresh_lock:
        if now - _cache.last_refresh_monotonic < _REFRESH_INTERVAL_SEC:
            return
        try:
            async with Database.session_context() as db:
                row = await db.session.get(ScannerRuntimeSettingsORM, 1)
                if row is None:
                    row = ScannerRuntimeSettingsORM(
                        id=1,
                        max_cards=10,
                        posttracking_minutes=30,
                        cooldown_hours=24,
                        statistics_enabled=True,
                    )
                    db.session.add(row)
                    await db.commit()
                else:
                    await db.session.refresh(row)
                _cache.max_cards = max(1, min(200, int(row.max_cards or 10)))
                _cache.posttracking_minutes = max(0, int(row.posttracking_minutes or 0))
                _cache.cooldown_hours = max(0, int(row.cooldown_hours or 0))
                _cache.statistics_enabled = bool(row.statistics_enabled)
        except Exception:
            pass
        _cache.last_refresh_monotonic = time.monotonic()


def collection_enabled() -> bool:
    return _cache.statistics_enabled


def max_cards() -> int:
    return _cache.max_cards


def posttracking_seconds() -> float:
    return max(0.0, float(_cache.posttracking_minutes) * 60.0)


def cooldown_seconds() -> float:
    return max(0.0, float(_cache.cooldown_hours) * 3600.0)


def should_compute_scanner_snapshot(sse_active: bool) -> bool:
    return sse_active or _cache.statistics_enabled


def is_under_cooldown(screener_id: int, symbol: str) -> bool:
    until = _cooldown_until.get((screener_id, symbol))
    if until is None:
        return False
    if time.time() >= until:
        _cooldown_until.pop((screener_id, symbol), None)
        return False
    return True


def request_manual_close(tracking_id: str, screener_id: int, symbol: str) -> None:
    _manual_close_ids.add(tracking_id)
    _cooldown_until[(screener_id, symbol)] = time.time() + cooldown_seconds()
    # session state dropped when prune runs
    for key, st in list(_sessions.items()):
        if st.tracking_id == tracking_id:
            _sessions.pop(key, None)
            break


def _ensure_session(
    screener_id: int,
    symbol: str,
    screener_name: str,
    exchange: str,
    market_type: str,
) -> _SessionState | None:
    if is_under_cooldown(screener_id, symbol):
        return None
    key = (screener_id, symbol)
    now = time.monotonic()
    if key not in _sessions:
        tid = uuid4().hex[:20]
        path = session_file_path(
            exchange=exchange,
            market_type=market_type,
            symbol=symbol,
            tracking_id=tid,
        )
        rel = relative_stat_path(path)
        st = _SessionState(tracking_id=tid, entered_monotonic=now, statistics_path=rel)
        _sessions[key] = st
        meta = {
            "kind": "session_meta",
            "tracking_id": tid,
            "symbol": symbol.upper(),
            "exchange": exchange.lower(),
            "market_type": market_type.lower(),
            "screener_id": screener_id,
            "screener_name": screener_name,
            "entered_scanner_at": datetime.now(timezone.utc).isoformat(),
            "scanner_source": "scanner",
            "statistics_file_path": rel,
        }
        asyncio.create_task(_async_append(path, meta))
        asyncio.create_task(
            _upsert_tracking_row(
                tracking_id=tid,
                screener_id=screener_id,
                screener_name=screener_name,
                exchange=exchange,
                market_type=market_type,
                symbol=symbol,
                status="active",
                statistics_file_path=rel,
            )
        )
    return _sessions[key]


async def _async_append(path: Any, obj: dict[str, Any]) -> None:
    await asyncio.to_thread(append_line, path, obj)


async def _upsert_tracking_row(**kwargs: Any) -> None:
    try:
        async with Database.session_context() as db:
            row = await db.session.get(TrackingSessionORM, kwargs["tracking_id"])
            if row is None:
                row = TrackingSessionORM(**kwargs)
                if row.entered_scanner_at is None:
                    row.entered_scanner_at = datetime.now(timezone.utc)
                db.session.add(row)
            else:
                for k, v in kwargs.items():
                    setattr(row, k, v)
            await db.commit()
    except Exception:
        pass


def is_posttracking(screener_id: int, symbol: str) -> bool:
    st = _sessions.get((screener_id, symbol))
    if not st or not st.triggered or st.posttracking_until is None:
        return False
    return time.time() < st.posttracking_until


def symbols_in_posttracking(screener_id: int) -> set[str]:
    """Символы, у которых ещё идёт постотслеживание после trigger (вне top-N тоже)."""
    now_wall = time.time()
    out: set[str] = set()
    for (sid, sym), st in _sessions.items():
        if sid != screener_id:
            continue
        if (
            st.triggered
            and st.posttracking_until is not None
            and now_wall < st.posttracking_until
        ):
            out.add(sym)
    return out


def prune_sessions_not_in_set(screener_id: int, keep_symbols: set[str]) -> None:
    now_wall = time.time()
    for key in list(_sessions.keys()):
        if key[0] != screener_id:
            continue
        sym = key[1]
        if sym not in keep_symbols:
            st = _sessions.get(key)
            if (
                st
                and st.triggered
                and st.posttracking_until is not None
                and now_wall < st.posttracking_until
            ):
                continue
            st = _sessions.pop(key, None)
            if st and not st.triggered:
                asyncio.create_task(
                    _mark_abandoned(st.tracking_id)
                )


async def _mark_abandoned(tracking_id: str) -> None:
    try:
        async with Database.session_context() as db:
            row = await db.session.get(TrackingSessionORM, tracking_id)
            if row and row.status in ("active",):
                row.status = "abandoned"
                row.updated_at = datetime.now(timezone.utc)
                await db.commit()
    except Exception:
        pass


def build_sample_line(
    payload: dict[str, Any],
    *,
    tracking_id: str,
    phase: str,
    seq: int,
    reason: str,
) -> dict[str, Any]:
    return {
        "kind": "sample",
        "tracking_id": tracking_id,
        "symbol": payload.get("symbol"),
        "exchange": payload.get("exchange"),
        "market_type": payload.get("market_type"),
        "screener_id": payload.get("screener_id"),
        "screener_name": payload.get("screener_name"),
        "ts": datetime.now(timezone.utc).isoformat(),
        "seq": seq,
        "phase": phase,
        "reason": reason,
        "score": payload.get("score"),
        "last_price": payload.get("last_price"),
        "ok_count": payload.get("ok_count"),
        "all_filters_ok": all(bool(r.get("ok")) for r in (payload.get("test_filters") or [])),
        "test_filters": payload.get("test_filters"),
        "scanner_filter_max_list": payload.get("scanner_filter_max_list"),
        "scanner_tracked_since": payload.get("scanner_tracked_since"),
    }


_sample_seq: dict[str, int] = {}


async def maybe_persist_sample(
    *,
    screener_id: int,
    symbol: str,
    screener_name: str,
    exchange: str,
    market_type: str,
    enriched_payload: dict[str, Any],
    force: bool = False,
) -> None:
    st = _ensure_session(screener_id, symbol, screener_name, exchange, market_type)
    if st is None:
        return
    if st.tracking_id in _manual_close_ids:
        return
    now_wall = time.time()
    if not force and now_wall - st.last_sample_wall < 5.0:
        return
    st.last_sample_wall = now_wall
    tid = st.tracking_id
    seq = _sample_seq.get(tid, 0) + 1
    _sample_seq[tid] = seq
    phase = "active"
    if st.triggered and st.posttracking_until:
        if now_wall < st.posttracking_until:
            phase = "posttracking"
        else:
            phase = "completed"
    line = build_sample_line(
        enriched_payload,
        tracking_id=tid,
        phase=phase,
        seq=seq,
        reason="changed" if force else "heartbeat",
    )
    path = session_file_path(
        exchange=exchange,
        market_type=market_type,
        symbol=symbol,
        tracking_id=tid,
    )
    await _async_append(path, line)
    if (
        phase == "completed"
        and st.triggered
        and not st.completion_emitted
    ):
        st.completion_emitted = True
        asyncio.create_task(_finalize_completed_session(tid, path, screener_id, symbol))


def mark_triggered(
    screener_id: int,
    symbol: str,
    snapshot: dict[str, Any],
) -> tuple[str | None, str | None]:
    """Помечает сессию как triggered, включает posttracking. Возвращает (tracking_id, json snapshot)."""
    key = (screener_id, symbol)
    st = _sessions.get(key)
    if st is None or st.triggered:
        return None, None
    st.triggered = True
    st.posttracking_until = time.time() + posttracking_seconds()
    tid = st.tracking_id
    snap = json.dumps(snapshot, ensure_ascii=False, default=str)
    ev = {
        "kind": "event",
        "tracking_id": tid,
        "event": "triggered",
        "ts": datetime.now(timezone.utc).isoformat(),
        "card_snapshot": snapshot,
    }
    path = session_file_path(
        exchange=str(snapshot.get("exchange", "")),
        market_type=str(snapshot.get("market_type", "")),
        symbol=str(snapshot.get("symbol", symbol)),
        tracking_id=tid,
    )
    asyncio.create_task(_async_append(path, ev))
    asyncio.create_task(
        _upsert_tracking_row(
            tracking_id=tid,
            screener_id=screener_id,
            screener_name=str(snapshot.get("screener_name", "")),
            exchange=str(snapshot.get("exchange", "")),
            market_type=str(snapshot.get("market_type", "")),
            symbol=str(snapshot.get("symbol", symbol)),
            status="triggered",
            statistics_file_path=st.statistics_path,
            triggered_at=datetime.now(timezone.utc),
        )
    )
    return tid, snap


def get_tracking_id_for_symbol(screener_id: int, symbol: str) -> str | None:
    st = _sessions.get((screener_id, symbol))
    return st.tracking_id if st else None


def attach_tracking_meta(
    payload: dict[str, Any],
    *,
    screener_id: int,
    symbol: str,
    screener_name: str,
    exchange: str,
    market_type: str,
) -> None:
    st = _ensure_session(screener_id, symbol, screener_name, exchange, market_type)
    if st is None:
        return
    payload["tracking_id"] = st.tracking_id
    payload["stat_href"] = stat_url_path(symbol, st.tracking_id)


def stat_url_path(symbol: str, tracking_id: str) -> str:
    slug = symbol.upper().replace("/", "").lower()
    return f"/admin/analytics/stat-{slug}-{tracking_id}"


def parse_stat_page_path(page: str) -> tuple[str, str] | None:
    """Разбор сегмента пути после ``/analytics/`` (обратно к ``stat_url_path``).

    Символ в slug без дефисов; ``tracking_id`` может содержать дефисы (UUID), поэтому
    отделяем slug от id только по **первому** дефису после префикса ``stat-``.
    """
    if not page.startswith("stat-"):
        return None
    body = page[5:]
    if "-" not in body:
        return None
    sym_slug, tid = body.split("-", 1)
    if not sym_slug or not tid:
        return None
    return sym_slug, tid


async def _finalize_completed_session(
    tracking_id: str, path: Any, screener_id: int, symbol: str
) -> None:
    ev = {
        "kind": "event",
        "tracking_id": tracking_id,
        "event": "completed",
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    await _async_append(path, ev)
    try:
        async with Database.session_context() as db:
            row = await db.session.get(TrackingSessionORM, tracking_id)
            if row:
                row.status = "completed"
                row.completed_at = datetime.now(timezone.utc)
                row.updated_at = datetime.now(timezone.utc)
                await db.commit()
    except Exception:
        pass
    key = (screener_id, symbol)
    _sessions.pop(key, None)
