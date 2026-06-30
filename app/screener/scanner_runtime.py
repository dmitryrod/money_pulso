"""Глобальный runtime Scanner: настройки из БД, top-N, JSONL samples, tracking_sessions."""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import select

from app.config.signals_log import log_signals_event
from app.database import Database
from app.database.models import ScannerRuntimeSettingsORM, TrackingSessionORM
from app.screener.statistics_store import (
    absolute_stat_path,
    append_line,
    relative_stat_path,
    resolve_statistics_jsonl,
    session_file_path,
)


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


def reset_statistics_runtime_state() -> None:
    """Сбрасывает in-memory сессии Scanner после полной очистки статистики (БД + JSONL)."""
    global _startup_reconcile_done
    _startup_reconcile_done = False
    _sessions.clear()
    _pending_signal_snapshots.clear()
    _manual_close_ids.clear()
    _cooldown_until.clear()
    _sample_seq.clear()
    _triggered_tracking_ids.clear()


_startup_reconcile_done = False


async def reconcile_stale_tracking_sessions_on_startup() -> int:
    """Закрывает в БД сессии без in-memory пары после restart consumer.

    Returns:
        Число строк, переведённых в ``status=closed``.
    """
    global _startup_reconcile_done
    if _startup_reconcile_done:
        return 0
    _startup_reconcile_done = True
    live_pairs = set(_sessions.keys())
    live_ids = {st.tracking_id for st in _sessions.values()}
    closed = 0
    now = datetime.now(timezone.utc)
    try:
        async with Database.session_context() as db:
            rows = (
                await db.session.execute(
                    select(TrackingSessionORM).where(
                        TrackingSessionORM.status.in_(
                            ("active", "triggered", "posttracking")
                        )
                    )
                )
            ).scalars().all()
            for row in rows:
                key = (row.screener_id, row.symbol)
                if key in live_pairs and row.tracking_id in live_ids:
                    continue
                row.status = "closed"
                row.closed_at = now
                row.updated_at = now
                closed += 1
            if closed:
                await db.commit()
    except Exception:
        pass
    return closed

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
# (screener_id, symbol) -> (tracking_id, card_snapshot_json); живёт пока сессия в _sessions.
_pending_signal_snapshots: dict[tuple[int, str], tuple[str, str]] = {}
_manual_close_ids: set[str] = set()
_cooldown_until: dict[tuple[int, str], float] = {}
# tracking_id с хотя бы одним trigger в текущем процессе (до admin purge).
_triggered_tracking_ids: set[str] = set()
_upsert_locks: dict[str, asyncio.Lock] = {}
_STATUS_RANK: dict[str, int] = {
    "active": 0,
    "triggered": 1,
    "posttracking": 2,
    "abandoned": 2,
    "completed": 3,
    "closed": 4,
}


def _upsert_lock(tracking_id: str) -> asyncio.Lock:
    lock = _upsert_locks.get(tracking_id)
    if lock is None:
        lock = asyncio.Lock()
        _upsert_locks[tracking_id] = lock
    return lock


def _merge_tracking_kwargs(
    row: TrackingSessionORM | None,
    kwargs: dict[str, Any],
) -> dict[str, Any]:
    """Не откатывать lifecycle-статус и ``triggered_at`` при гонке active/triggered."""
    if row is None:
        return kwargs
    merged = dict(kwargs)
    new_status = merged.get("status")
    old_status = row.status
    if isinstance(new_status, str) and isinstance(old_status, str):
        new_rank = _STATUS_RANK.get(new_status, -2)
        old_rank = _STATUS_RANK.get(old_status, -2)
        if new_rank < old_rank:
            merged.pop("status", None)
    if row.triggered_at is not None and merged.get("triggered_at") is None:
        merged.pop("triggered_at", None)
    if row.triggered_at is not None and merged.get("status") == "active":
        merged.pop("status", None)
    return merged


def _jsonl_contains_triggered_event(
    statistics_path_rel: str | None,
    tracking_id: str,
) -> bool:
    """True если в JSONL сессии есть event ``triggered``."""
    path = resolve_statistics_jsonl(statistics_path_rel or "", tracking_id=tracking_id)
    if path is None:
        return False
    try:
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(obj, dict) and obj.get("kind") == "event":
                    if str(obj.get("event") or "").strip() == "triggered":
                        return True
    except OSError:
        return False
    return False


async def _tracking_id_has_trigger_history(
    tracking_id: str,
    statistics_path_rel: str | None,
) -> bool:
    """True если trigger зафиксирован в памяти, БД или JSONL."""
    if tracking_id in _triggered_tracking_ids:
        return True
    try:
        async with Database.session_context() as db:
            row = await db.session.get(TrackingSessionORM, tracking_id)
            if row is not None and row.triggered_at is not None:
                return True
    except Exception:
        pass
    return _jsonl_contains_triggered_event(statistics_path_rel, tracking_id)


async def _backfill_triggered_at_in_db(
    *,
    tracking_id: str,
    screener_id: int,
    symbol: str,
    statistics_path: str | None,
    snapshot: dict[str, Any] | None = None,
) -> None:
    """Записать ``triggered_at`` в БД, если trigger есть в памяти/JSONL, а в строке нет.

    Каталог ``/admin_api/analytics/sessions`` включает только строки с
    ``triggered_at IS NOT NULL``; без backfill сессии остаются в хвосте ``active``.
    """
    has_history = tracking_id in _triggered_tracking_ids or _jsonl_contains_triggered_event(
        statistics_path, tracking_id
    )
    if not has_history:
        return
    try:
        async with Database.session_context() as db:
            row = await db.session.get(TrackingSessionORM, tracking_id)
            if row is not None and row.triggered_at is not None:
                return
    except Exception:
        return
    snap = snapshot or {}
    screener_name = str(snap.get("screener_name", ""))
    exchange = str(snap.get("exchange", ""))
    market_type = str(snap.get("market_type", ""))
    sym = str(snap.get("symbol", symbol))
    if not screener_name:
        try:
            async with Database.session_context() as db:
                row = await db.session.get(TrackingSessionORM, tracking_id)
                if row is not None:
                    screener_name = row.screener_name
                    exchange = row.exchange
                    market_type = row.market_type
                    sym = row.symbol
        except Exception:
            pass
    await _upsert_tracking_row(
        tracking_id=tracking_id,
        screener_id=screener_id,
        screener_name=screener_name,
        exchange=exchange,
        market_type=market_type,
        symbol=sym,
        status="triggered",
        statistics_file_path=statistics_path,
        triggered_at=datetime.now(timezone.utc),
    )


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
    """Запись JSONL на диск (алиас ``jsonl_persistence_enabled``)."""
    return _cache.statistics_enabled


def jsonl_persistence_enabled() -> bool:
    """True — append-only сэмплы и события в ``app/statistics-data/``."""
    return _cache.statistics_enabled


def max_cards() -> int:
    return _cache.max_cards


def posttracking_seconds() -> float:
    return max(0.0, float(_cache.posttracking_minutes) * 60.0)


def cooldown_seconds() -> float:
    return max(0.0, float(_cache.cooldown_hours) * 3600.0)


def should_compute_scanner_snapshot(sse_active: bool = False) -> bool:
    """Scanner snapshot и сессии всегда при работающем consumer (SSE не влияет)."""
    del sse_active
    return True


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
            _pending_signal_snapshots.pop(key, None)
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
        if jsonl_persistence_enabled():
            asyncio.create_task(_async_append(path, meta))
            _schedule_status_event(path, tid, "start")
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


def _make_status_event(tracking_id: str, event: str, **extra: Any) -> dict[str, Any]:
    """Build a JSONL status line for the Stat page events list."""
    line: dict[str, Any] = {
        "kind": "event",
        "tracking_id": tracking_id,
        "event": event,
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    if extra:
        line.update(extra)
    return line


def _schedule_status_event(path: Any, tracking_id: str, event: str, **extra: Any) -> None:
    """Append status event to JSONL when persistence is enabled."""
    _schedule_jsonl_append(path, _make_status_event(tracking_id, event, **extra))


async def append_status_event_for_path(
    statistics_path_rel: str | None,
    tracking_id: str,
    event: str,
    **extra: Any,
) -> None:
    """Append one status event to the session JSONL (awaitable, for admin close)."""
    if not statistics_path_rel or not jsonl_persistence_enabled():
        return
    path = absolute_stat_path(statistics_path_rel)
    await _async_append(path, _make_status_event(tracking_id, event, **extra))


def _schedule_jsonl_append(path: Any, obj: dict[str, Any]) -> None:
    """Пишет строку JSONL только при включённом ``statistics_enabled``."""
    if jsonl_persistence_enabled():
        asyncio.create_task(_async_append(path, obj))


async def _upsert_tracking_row(**kwargs: Any) -> None:
    tracking_id = kwargs.get("tracking_id")
    if not tracking_id:
        return
    async with _upsert_lock(str(tracking_id)):
        try:
            async with Database.session_context() as db:
                row = await db.session.get(TrackingSessionORM, str(tracking_id))
                merge_kwargs = _merge_tracking_kwargs(row, kwargs)
                if row is None:
                    row = TrackingSessionORM(**merge_kwargs)
                    if row.entered_scanner_at is None:
                        row.entered_scanner_at = datetime.now(timezone.utc)
                    db.session.add(row)
                else:
                    for k, v in merge_kwargs.items():
                        setattr(row, k, v)
                await db.commit()
        except Exception as exc:
            log_signals_event(
                {
                    "kind": "scanner_tracking",
                    "action": "upsert_failed",
                    "tracking_id": str(tracking_id),
                    "error": str(exc),
                }
            )


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
            _pending_signal_snapshots.pop(key, None)
            if st:
                _sample_seq.pop(st.tracking_id, None)
                if st.triggered:
                    _maybe_emit_completion(st, screener_id, sym)
                else:
                    asyncio.create_task(
                        _async_tombstone_untriggered_session(
                            st.tracking_id, st.statistics_path
                        )
                    )


async def _async_tombstone_untriggered_session(
    tracking_id: str, statistics_path_rel: str | None
) -> None:
    """Tombstone untriggered session: unlink JSONL, retain minimal ``tracking_sessions`` row."""
    if await _tracking_id_has_trigger_history(tracking_id, statistics_path_rel):
        return
    now = datetime.now(timezone.utc)
    entered_at_iso: str | None = None
    symbol: str | None = None
    try:
        async with Database.session_context() as db:
            row = await db.session.get(TrackingSessionORM, tracking_id)
            if row is not None:
                if row.entered_scanner_at is not None:
                    entered_at_iso = row.entered_scanner_at.isoformat()
                symbol = row.symbol
                row.status = "deleted"
                row.closed_at = now
                row.statistics_file_path = None
                row.updated_at = now
                await db.commit()
    except Exception:
        pass
    if statistics_path_rel:
        path = absolute_stat_path(statistics_path_rel)
        try:
            if path.is_file():
                path.unlink()
        except OSError:
            pass
    log_signals_event(
        {
            "kind": "scanner_tracking",
            "action": "tombstone_deleted",
            "tracking_id": tracking_id,
            "symbol": symbol,
            "entered_scanner_at": entered_at_iso,
            "deleted_at": now.isoformat(),
        }
    )


def remove_untriggered_session_and_artifacts(
    screener_id: int, symbol: str,
) -> bool:
    """Tombstone сессию без trigger: память, JSONL; строка ``tracking_sessions`` → ``deleted``.

    Returns:
        True если сессия была и была без trigger.
    """
    key = (screener_id, symbol)
    st = _sessions.get(key)
    if st is None or st.triggered or st.tracking_id in _triggered_tracking_ids:
        return False
    _sessions.pop(key, None)
    _pending_signal_snapshots.pop(key, None)
    _sample_seq.pop(st.tracking_id, None)
    _manual_close_ids.discard(st.tracking_id)
    asyncio.create_task(
        _async_tombstone_untriggered_session(st.tracking_id, st.statistics_path)
    )
    return True


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


def maybe_emit_completion_if_due(screener_id: int, symbol: str) -> None:
    """Завершает посттрек в БД (и JSONL при включённом persistence), не требуя sample."""
    st = _sessions.get((screener_id, symbol))
    if st is not None:
        _maybe_emit_completion(st, screener_id, symbol)


def _maybe_emit_completion(
    st: _SessionState, screener_id: int, symbol: str,
) -> None:
    if not st.triggered or st.posttracking_until is None:
        return
    if time.time() < st.posttracking_until:
        return
    if st.completion_emitted:
        return
    st.completion_emitted = True
    tid = st.tracking_id
    path = absolute_stat_path(st.statistics_path) if st.statistics_path else None
    asyncio.create_task(_finalize_completed_session(tid, path, screener_id, symbol))


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
    _maybe_emit_completion(st, screener_id, symbol)
    if not jsonl_persistence_enabled():
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
    if not st.statistics_path:
        return
    path = absolute_stat_path(st.statistics_path)
    await _async_append(path, line)


async def mark_triggered(
    screener_id: int,
    symbol: str,
    snapshot: dict[str, Any],
) -> tuple[str | None, str | None]:
    """Помечает сессию как triggered, включает posttracking. Возвращает (tracking_id, json snapshot)."""
    key = (screener_id, symbol)
    st = _sessions.get(key)
    if st is None:
        return None, None
    if st.triggered:
        await _backfill_triggered_at_in_db(
            tracking_id=st.tracking_id,
            screener_id=screener_id,
            symbol=symbol,
            statistics_path=st.statistics_path,
            snapshot=snapshot,
        )
        return None, None
    st.triggered = True
    st.posttracking_until = time.time() + posttracking_seconds()
    tid = st.tracking_id
    _triggered_tracking_ids.add(tid)
    snap = json.dumps(snapshot, ensure_ascii=False, default=str)
    await _upsert_tracking_row(
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
    if st.statistics_path:
        path = absolute_stat_path(st.statistics_path)
        _schedule_status_event(
            path, tid, "triggered", card_snapshot=snapshot,
        )
    _pending_signal_snapshots[key] = (tid, snap)
    return tid, snap


def record_trigger_refire(
    screener_id: int,
    symbol: str,
    snapshot: dict[str, Any],
) -> None:
    """Log another ``triggered`` event when all filters pass again after first trigger."""
    st = _sessions.get((screener_id, symbol))
    if st is None or not st.triggered or not st.statistics_path:
        return
    path = absolute_stat_path(st.statistics_path)
    _schedule_status_event(
        path,
        st.tracking_id,
        "triggered",
        refire=True,
        card_snapshot=snapshot,
    )


def get_card_snapshot_for_signal_row(
    screener_id: int, symbol: str,
) -> tuple[str | None, str | None]:
    """Снимок для строки `signals`; очищается при удалении сессии из `_sessions`."""
    return _pending_signal_snapshots.get((screener_id, symbol), (None, None))


def get_tracking_id_for_symbol(screener_id: int, symbol: str) -> str | None:
    st = _sessions.get((screener_id, symbol))
    return st.tracking_id if st else None


def session_is_triggered(screener_id: int, symbol: str) -> bool:
    """True, если in-memory сессия уже прошла фазу trigger."""
    st = _sessions.get((screener_id, symbol))
    if st is None:
        return False
    if st.triggered or st.tracking_id in _triggered_tracking_ids:
        return True
    return False


async def session_is_triggered_async(screener_id: int, symbol: str) -> bool:
    """Как ``session_is_triggered``, плюс проверка ``triggered_at`` / JSONL в БД."""
    st = _sessions.get((screener_id, symbol))
    if st is None:
        return False
    if st.triggered or st.tracking_id in _triggered_tracking_ids:
        await _backfill_triggered_at_in_db(
            tracking_id=st.tracking_id,
            screener_id=screener_id,
            symbol=symbol,
            statistics_path=st.statistics_path,
        )
        return True
    if await _tracking_id_has_trigger_history(st.tracking_id, st.statistics_path):
        st.triggered = True
        _triggered_tracking_ids.add(st.tracking_id)
        await _backfill_triggered_at_in_db(
            tracking_id=st.tracking_id,
            screener_id=screener_id,
            symbol=symbol,
            statistics_path=st.statistics_path,
        )
        return True
    return False


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
    tracking_id: str, path: Any | None, screener_id: int, symbol: str
) -> None:
    if path is not None:
        _schedule_status_event(path, tracking_id, "completed")
    try:
        async with Database.session_context() as db:
            row = await db.session.get(TrackingSessionORM, tracking_id)
            if row:
                now = datetime.now(timezone.utc)
                if row.triggered_at is None:
                    row.triggered_at = now
                row.status = "completed"
                row.completed_at = now
                row.updated_at = now
                await db.commit()
    except Exception:
        pass
    key = (screener_id, symbol)
    _sessions.pop(key, None)
    _pending_signal_snapshots.pop(key, None)
