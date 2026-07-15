"""Тесты Scanner Analytics: runtime helpers и контракт JSONL sample."""

from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.screener import scanner_runtime
from app.screener.statistics_store import (
    absolute_stat_path,
    append_line,
    relative_stat_path,
    resolve_statistics_jsonl,
    session_file_path,
)


@pytest.fixture(autouse=True)
def _reset_scanner_runtime_state():
    """Изолировать глобальные кэши сессий между тестами."""
    scanner_runtime._sessions.clear()  # noqa: SLF001
    scanner_runtime._pending_signal_snapshots.clear()  # noqa: SLF001
    scanner_runtime._manual_close_ids.clear()  # noqa: SLF001
    scanner_runtime._cooldown_until.clear()  # noqa: SLF001
    scanner_runtime._triggered_tracking_ids.clear()  # noqa: SLF001
    scanner_runtime._startup_reconcile_done = False  # noqa: SLF001
    yield
    scanner_runtime._sessions.clear()  # noqa: SLF001
    scanner_runtime._pending_signal_snapshots.clear()  # noqa: SLF001
    scanner_runtime._manual_close_ids.clear()  # noqa: SLF001
    scanner_runtime._cooldown_until.clear()  # noqa: SLF001
    scanner_runtime._triggered_tracking_ids.clear()  # noqa: SLF001


def test_stat_url_path_slug_and_tracking() -> None:
    assert scanner_runtime.stat_url_path("BTCUSDT", "tid-1") == (
        "/admin/analytics/stat-btcusdt-tid-1"
    )
    assert scanner_runtime.stat_url_path("BTC/USDT", "tid-1") == (
        "/admin/analytics/stat-btcusdt-tid-1"
    )


def test_parse_stat_page_path_split_first_hyphen() -> None:
    assert scanner_runtime.parse_stat_page_path("stat-btcusdt-tid-1") == ("btcusdt", "tid-1")
    assert scanner_runtime.parse_stat_page_path(
        "stat-btcusdt-9b27ef45-2f0f-4419-bc72"
    ) == ("btcusdt", "9b27ef45-2f0f-4419-bc72")
    assert scanner_runtime.parse_stat_page_path("stat-zkusdt-c3b6fbbe62a9475db600") == (
        "zkusdt",
        "c3b6fbbe62a9475db600",
    )
    assert scanner_runtime.parse_stat_page_path("analytics") is None
    assert scanner_runtime.parse_stat_page_path("stat-nohyphen") is None


def test_is_posttracking_false_without_session() -> None:
    assert scanner_runtime.is_posttracking(1, "ETHUSDT") is False


def test_is_posttracking_true_when_triggered_and_window_open() -> None:
    st = scanner_runtime._SessionState(  # noqa: SLF001
        tracking_id="abc",
        entered_monotonic=time.monotonic(),
        triggered=True,
        posttracking_until=time.time() + 3600.0,
    )
    scanner_runtime._sessions[(7, "SOLUSDT")] = st  # noqa: SLF001
    assert scanner_runtime.is_posttracking(7, "SOLUSDT") is True


def test_session_is_triggered() -> None:
    assert scanner_runtime.session_is_triggered(1, "XXXUSDT") is False
    st = scanner_runtime._SessionState(  # noqa: SLF001
        tracking_id="tid1",
        entered_monotonic=0.0,
        triggered=True,
        posttracking_until=None,
    )
    scanner_runtime._sessions[(3, "AAAUSDT")] = st  # noqa: SLF001
    assert scanner_runtime.session_is_triggered(3, "AAAUSDT") is True


def test_build_sample_line_kind_and_filters() -> None:
    payload = {
        "symbol": "X",
        "exchange": "bybit",
        "market_type": "futures",
        "screener_id": 3,
        "screener_name": "S",
        "score": 1.5,
        "last_price": 1.2345,
        "ok_count": 2,
        "test_filters": [{"id": "pd", "ok": True, "title": "P", "current": {}, "thresholds": {}}],
        "scanner_filter_max_list": [],
        "scanner_tracked_since": None,
    }
    line = scanner_runtime.build_sample_line(
        payload,
        tracking_id="tid",
        phase="active",
        seq=1,
        reason="heartbeat",
    )
    assert line["kind"] == "sample"
    assert line["tracking_id"] == "tid"
    assert line["phase"] == "active"
    assert line["seq"] == 1
    assert line["score"] == 1.5
    assert line["last_price"] == 1.2345
    assert line["all_filters_ok"] is True


def test_attach_tracking_meta_adds_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fake_ensure(
        screener_id: int,
        symbol: str,
        screener_name: str,
        exchange: str,
        market_type: str,
    ):
        return scanner_runtime._SessionState(  # noqa: SLF001
            tracking_id="tid-fixed",
            entered_monotonic=0.0,
        )

    monkeypatch.setattr(scanner_runtime, "_ensure_session", _fake_ensure)
    payload: dict = {}
    scanner_runtime.attach_tracking_meta(
        payload,
        screener_id=1,
        symbol="AA",
        screener_name="N",
        exchange="bybit",
        market_type="futures",
    )
    assert payload["tracking_id"] == "tid-fixed"
    assert payload["stat_href"] == "/admin/analytics/stat-aa-tid-fixed"


def test_analytics_stat_template_path_not_cwd_relative() -> None:
    """Регрессия: Admin с templates_dir=app/admin/templates ломался при cwd внутри app/."""
    tpl_dir = Path(__file__).resolve().parents[1] / "admin" / "templates"
    assert (tpl_dir / "analytics_stat.html").is_file()


def test_resolve_statistics_jsonl_finds_file_by_tracking_id_suffix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Регрессия: API читает JSONL по tracking_id, если путь в БД указывает на другой день."""
    stat_root = tmp_path / "statistics-data"
    monkeypatch.setattr(
        "app.screener.statistics_store._STAT_ROOT",
        stat_root,
    )
    monkeypatch.setattr(
        "app.screener.statistics_store.app_root_dir",
        lambda: tmp_path,
    )

    day_old = datetime(2026, 6, 8, tzinfo=timezone.utc)
    day_new = datetime(2026, 6, 9, tzinfo=timezone.utc)
    tid = "b94c28b5fe3141399b45"
    stale_rel = relative_stat_path(
        session_file_path(
            exchange="bybit",
            market_type="futures",
            symbol="DYDXUSDT",
            tracking_id=tid,
            day=day_old,
        )
    )
    actual = session_file_path(
        exchange="bybit",
        market_type="futures",
        symbol="DYDXUSDT",
        tracking_id=tid,
        day=day_new,
    )
    append_line(actual, {"kind": "sample", "tracking_id": tid, "seq": 1})

    resolved = resolve_statistics_jsonl(stale_rel, tracking_id=tid)
    assert resolved is not None
    assert resolved == actual
    first_line = resolved.read_text(encoding="utf-8").strip().splitlines()[0]
    lines = json.loads(first_line)
    assert lines["tracking_id"] == tid


@pytest.mark.asyncio
async def test_maybe_persist_sample_uses_frozen_statistics_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Регрессия: samples пишутся в st.statistics_path, а не в session_file_path() с текущей датой."""
    frozen_day = datetime(2026, 6, 8, 12, 0, tzinfo=timezone.utc)
    tid = "frozenpath0000000001"
    frozen_path = session_file_path(
        exchange="bybit",
        market_type="futures",
        symbol="ETHUSDT",
        tracking_id=tid,
        day=frozen_day,
    )
    frozen_rel = relative_stat_path(frozen_path)
    st = scanner_runtime._SessionState(  # noqa: SLF001
        tracking_id=tid,
        entered_monotonic=time.monotonic(),
        statistics_path=frozen_rel,
    )
    scanner_runtime._sessions[(1, "ETHUSDT")] = st  # noqa: SLF001

    written: list[Path] = []

    async def _capture_append(path: Path, obj: dict) -> None:
        written.append(path)

    monkeypatch.setattr(scanner_runtime, "_async_append", _capture_append)
    monkeypatch.setattr(
        scanner_runtime,
        "_ensure_session",
        lambda *a, **k: st,
    )
    monkeypatch.setattr(scanner_runtime, "_cache", scanner_runtime.ScannerRuntimeCache(statistics_enabled=True))

    await scanner_runtime.maybe_persist_sample(
        screener_id=1,
        symbol="ETHUSDT",
        screener_name="S",
        exchange="bybit",
        market_type="futures",
        enriched_payload={
            "symbol": "ETHUSDT",
            "exchange": "bybit",
            "market_type": "futures",
            "screener_id": 1,
            "screener_name": "S",
            "score": 1.0,
            "last_price": 100.0,
            "ok_count": 1,
            "test_filters": [],
        },
        force=True,
    )

    assert len(written) == 1
    assert written[0] == absolute_stat_path(frozen_rel)


def test_should_compute_scanner_snapshot_always_true() -> None:
    scanner_runtime._cache.statistics_enabled = False  # noqa: SLF001
    assert scanner_runtime.should_compute_scanner_snapshot(False) is True
    assert scanner_runtime.should_compute_scanner_snapshot(True) is True
    scanner_runtime._cache.statistics_enabled = True  # noqa: SLF001


def test_jsonl_persistence_enabled_alias() -> None:
    scanner_runtime._cache.statistics_enabled = False  # noqa: SLF001
    assert scanner_runtime.jsonl_persistence_enabled() is False
    assert scanner_runtime.collection_enabled() is False
    scanner_runtime._cache.statistics_enabled = True  # noqa: SLF001
    assert scanner_runtime.jsonl_persistence_enabled() is True


@pytest.mark.asyncio
async def test_ensure_session_upserts_db_without_jsonl_when_statistics_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scanner_runtime._cache.statistics_enabled = False  # noqa: SLF001
    upsert_calls: list[dict] = []
    append_calls: list[tuple] = []
    pending: list[object] = []

    async def _fake_upsert(**kwargs: object) -> None:
        upsert_calls.append(dict(kwargs))

    async def _fake_append(path: object, obj: dict) -> None:
        append_calls.append((path, obj))

    def _capture_task(coro: object) -> None:
        pending.append(coro)

    monkeypatch.setattr(scanner_runtime, "_upsert_tracking_row", _fake_upsert)
    monkeypatch.setattr(scanner_runtime, "_async_append", _fake_append)
    monkeypatch.setattr(scanner_runtime.asyncio, "create_task", _capture_task)

    st = scanner_runtime._ensure_session(  # noqa: SLF001
        9, "BTCUSDT", "Test", "bybit", "futures",
    )
    assert st is not None
    for coro in pending:
        await coro  # type: ignore[misc]
    assert upsert_calls
    assert upsert_calls[0]["symbol"] == "BTCUSDT"
    assert upsert_calls[0]["status"] == "active"
    assert append_calls == []


def test_merge_tracking_kwargs_does_not_downgrade_triggered() -> None:
    from app.database.models import TrackingSessionORM

    t1 = datetime(2026, 6, 20, 12, 0, 0, tzinfo=timezone.utc)
    row = TrackingSessionORM(
        tracking_id="tid-merge",
        screener_id=1,
        screener_name="S",
        exchange="bybit",
        market_type="futures",
        symbol="BTCUSDT",
        status="triggered",
        triggered_at=t1,
    )
    merged = scanner_runtime._merge_tracking_kwargs(  # noqa: SLF001
        row,
        {"tracking_id": "tid-merge", "status": "active"},
    )
    assert "status" not in merged


@pytest.mark.asyncio
async def test_concurrent_active_and_triggered_upsert_preserves_trigger(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Гонка ensure_session(active) vs mark_triggered не должна терять triggered_at."""
    from app.database.models import TrackingSessionORM

    rows: dict[str, TrackingSessionORM] = {}
    t_trig = datetime(2026, 6, 29, 12, 0, 0, tzinfo=timezone.utc)

    class _FakeSession:
        async def get(self, _model: type, tid: str) -> TrackingSessionORM | None:
            return rows.get(tid)

        def add(self, row: TrackingSessionORM) -> None:
            rows[row.tracking_id] = row

        async def commit(self) -> None:
            return None

    class _FakeDb:
        session = _FakeSession()

    class _FakeCtx:
        async def __aenter__(self) -> _FakeDb:
            return _FakeDb()

        async def __aexit__(self, *_a: object) -> None:
            return None

    monkeypatch.setattr(
        "app.screener.scanner_runtime.Database.session_context",
        lambda: _FakeCtx(),
    )
    monkeypatch.setattr(
        "app.screener.scanner_runtime.log_signals_event",
        lambda _payload: None,
    )

    tid = "tid-race-1"
    await asyncio.gather(
        scanner_runtime._upsert_tracking_row(  # noqa: SLF001
            tracking_id=tid,
            screener_id=1,
            screener_name="S",
            exchange="bybit",
            market_type="futures",
            symbol="ETHUSDT",
            status="active",
            statistics_file_path="statistics-data/x.jsonl",
        ),
        scanner_runtime._upsert_tracking_row(  # noqa: SLF001
            tracking_id=tid,
            screener_id=1,
            screener_name="S",
            exchange="bybit",
            market_type="futures",
            symbol="ETHUSDT",
            status="triggered",
            statistics_file_path="statistics-data/x.jsonl",
            triggered_at=t_trig,
        ),
    )

    row = rows[tid]
    assert row.triggered_at == t_trig
    assert row.status == "triggered"


@pytest.mark.asyncio
async def test_maybe_persist_sample_skips_disk_when_statistics_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scanner_runtime._cache.statistics_enabled = False  # noqa: SLF001
    st = scanner_runtime._SessionState(  # noqa: SLF001
        tracking_id="tid-nodisk",
        entered_monotonic=time.monotonic(),
        statistics_path="statistics-data/x.jsonl",
    )
    scanner_runtime._sessions[(2, "SOLUSDT")] = st  # noqa: SLF001
    written: list[object] = []

    async def _capture_append(path: object, obj: dict) -> None:
        written.append(path)

    monkeypatch.setattr(scanner_runtime, "_async_append", _capture_append)

    await scanner_runtime.maybe_persist_sample(
        screener_id=2,
        symbol="SOLUSDT",
        screener_name="S",
        exchange="bybit",
        market_type="futures",
        enriched_payload={"symbol": "SOLUSDT", "test_filters": []},
        force=True,
    )
    assert written == []


def test_symbol_check_pair_runs_test_eval_without_sse(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Регрессия: evaluate_test_mode_snapshot вызывается при test_enabled=True без SSE."""
    from app.screener.consumer import _symbol_check_pair

    eval_called: list[bool] = []

    class _FakeCounter:
        def get(self, _symbol: str) -> int:
            return 0

    def _fake_eval(*_a: object, **_k: object) -> dict:
        eval_called.append(True)
        return {"score": 1.0, "test_filters": [{"id": "pd", "ok": True}]}

    monkeypatch.setattr(
        "app.screener.consumer.evaluate_test_mode_snapshot",
        _fake_eval,
    )
    monkeypatch.setattr(
        "app.screener.consumer.Consumer._check_filters_for_symbol",
        lambda *_a, **_k: (None, None),
    )

    _symbol_check_pair(
        _FakeCounter(),  # type: ignore[arg-type]
        True,
        ("ETHUSDT", "ETH", None, None, {}, [], [], 0.0, [], set(), set()),
    )
    assert eval_called == [True]


def test_build_tracking_timeline_start_and_triggered() -> None:
    from types import SimpleNamespace

    from app.screener.tracking_timeline import build_tracking_timeline

    t0 = datetime(2026, 6, 9, 17, 5, 6, tzinfo=timezone.utc)
    t1 = datetime(2026, 6, 9, 20, 10, 0, tzinfo=timezone.utc)
    row = SimpleNamespace(
        status="triggered",
        entered_scanner_at=t0,
        created_at=t0,
        triggered_at=t1,
        completed_at=None,
        closed_at=None,
        updated_at=t1,
    )
    tl = build_tracking_timeline(row)
    assert len(tl) == 2
    assert tl[0] == {"label": "start", "at": t0.isoformat()}
    assert tl[1] == {"label": "triggered", "at": t1.isoformat()}


def test_build_tracking_timeline_deleted() -> None:
    from types import SimpleNamespace

    from app.screener.tracking_timeline import analytics_category, build_tracking_timeline

    t0 = datetime(2026, 6, 9, 17, 5, 6, tzinfo=timezone.utc)
    t1 = datetime(2026, 6, 9, 18, 0, 0, tzinfo=timezone.utc)
    row = SimpleNamespace(
        status="deleted",
        entered_scanner_at=t0,
        created_at=t0,
        triggered_at=None,
        completed_at=None,
        closed_at=t1,
        updated_at=t1,
    )
    tl = build_tracking_timeline(row)
    assert tl == [
        {"label": "start", "at": t0.isoformat()},
        {"label": "deleted", "at": t1.isoformat()},
    ]
    assert analytics_category("deleted") == "other"


def test_analytics_category_mapping() -> None:
    from app.screener.tracking_timeline import analytics_category

    assert analytics_category("active") == "active"
    assert analytics_category("triggered") == "active"
    assert analytics_category("completed") == "completed"
    assert analytics_category("closed") == "completed"
    assert analytics_category("deleted") == "other"


def test_build_session_events_jsonl_chronology() -> None:
    from types import SimpleNamespace

    from app.screener.tracking_timeline import build_session_events

    t0 = "2026-06-16T08:00:00+00:00"
    t1 = "2026-06-16T08:10:00+00:00"
    t2 = "2026-06-16T08:11:00+00:00"
    t3 = "2026-06-16T08:40:00+00:00"
    rows = [
        {"kind": "session_meta", "entered_scanner_at": t0},
        {"kind": "event", "event": "start", "ts": t0},
        {"kind": "event", "event": "triggered", "ts": t1},
        {"kind": "event", "event": "triggered", "ts": t2, "refire": True},
        {"kind": "event", "event": "completed", "ts": t3},
    ]
    events = build_session_events(rows, None)
    assert [e["event"] for e in events] == [
        "start",
        "triggered",
        "triggered",
        "completed",
    ]
    assert events[0]["ts"] == t0
    assert events[2]["ts"] == t2


def test_build_session_events_db_backfill_legacy() -> None:
    from types import SimpleNamespace

    from app.screener.tracking_timeline import build_session_events

    t0 = datetime(2026, 6, 16, 8, 0, 0, tzinfo=timezone.utc)
    t1 = datetime(2026, 6, 16, 8, 27, 50, tzinfo=timezone.utc)
    t2 = datetime(2026, 6, 16, 8, 57, 51, tzinfo=timezone.utc)
    row = SimpleNamespace(
        status="completed",
        entered_scanner_at=t0,
        created_at=t0,
        triggered_at=t1,
        completed_at=t2,
        closed_at=None,
    )
    rows = [
        {"kind": "session_meta", "entered_scanner_at": t0.isoformat()},
        {"kind": "event", "event": "triggered", "ts": t1.isoformat()},
        {"kind": "event", "event": "completed", "ts": t2.isoformat()},
    ]
    events = build_session_events(rows, row)
    assert events[0] == {"ts": t0.isoformat(), "event": "start"}
    assert len(events) == 3


def test_record_trigger_refire_appends_event(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    from app.screener.statistics_store import relative_stat_path

    appended: list[dict] = []

    def _capture_append(path: object, obj: dict) -> None:
        appended.append(obj)

    monkeypatch.setattr(
        "app.screener.scanner_runtime.jsonl_persistence_enabled", lambda: True,
    )
    monkeypatch.setattr(
        "app.screener.scanner_runtime._schedule_jsonl_append", _capture_append,
    )
    jsonl = tmp_path / "s.jsonl"
    rel = relative_stat_path(jsonl)
    tid = "tid-refire"
    scanner_runtime._sessions[(1, "HUSDT")] = scanner_runtime._SessionState(  # noqa: SLF001
        tracking_id=tid,
        entered_monotonic=time.monotonic(),
        triggered=True,
        statistics_path=rel,
    )
    monkeypatch.setattr(
        "app.screener.scanner_runtime.absolute_stat_path", lambda _r: jsonl,
    )

    scanner_runtime.record_trigger_refire(1, "HUSDT", {"symbol": "HUSDT"})

    assert len(appended) == 1
    assert appended[0]["event"] == "triggered"
    assert appended[0]["refire"] is True
    scanner_runtime._sessions.clear()


@pytest.mark.asyncio
async def test_tombstone_untriggered_keeps_db_row(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """Untriggered tombstone: JSONL removed, DB row kept with status=deleted."""
    from app.database.models import TrackingSessionORM
    from app.screener.statistics_store import relative_stat_path

    t0 = datetime(2026, 6, 9, 12, 0, 0, tzinfo=timezone.utc)
    jsonl = tmp_path / "sess.jsonl"
    jsonl.write_text('{"kind":"session_meta"}\n', encoding="utf-8")
    rel = relative_stat_path(jsonl)

    row = TrackingSessionORM(
        tracking_id="tid-tomb-1",
        screener_id=1,
        screener_name="S",
        exchange="bybit",
        market_type="futures",
        symbol="BTCUSDT",
        status="active",
        statistics_file_path=rel,
        entered_scanner_at=t0,
        created_at=t0,
        updated_at=t0,
    )

    class _FakeSession:
        async def get(self, _model: type, tid: str) -> TrackingSessionORM | None:
            return row if tid == "tid-tomb-1" else None

        async def commit(self) -> None:
            return None

    class _FakeDb:
        session = _FakeSession()

    class _FakeCtx:
        async def __aenter__(self) -> _FakeDb:
            return _FakeDb()

        async def __aexit__(self, *_a: object) -> None:
            return None

    logged: list[dict] = []

    def _log(payload: dict) -> None:
        logged.append(payload)

    monkeypatch.setattr(
        "app.screener.scanner_runtime.Database.session_context",
        lambda: _FakeCtx(),
    )
    monkeypatch.setattr(
        "app.screener.scanner_runtime.absolute_stat_path",
        lambda _rel: jsonl,
    )
    monkeypatch.setattr("app.screener.scanner_runtime.log_signals_event", _log)

    await scanner_runtime._async_tombstone_untriggered_session(  # noqa: SLF001
        "tid-tomb-1", rel,
    )

    assert not jsonl.is_file()
    assert row.status == "deleted"
    assert row.statistics_file_path is None
    assert row.closed_at is not None
    assert logged and logged[0]["action"] == "tombstone_deleted"
    assert logged[0]["tracking_id"] == "tid-tomb-1"


@pytest.mark.asyncio
async def test_tombstone_skips_when_triggered_at_in_db(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """Triggered session must not be tombstoned even if called directly."""
    from app.database.models import TrackingSessionORM
    from app.screener.statistics_store import relative_stat_path

    t0 = datetime(2026, 6, 9, 12, 0, 0, tzinfo=timezone.utc)
    t1 = datetime(2026, 6, 9, 12, 5, 0, tzinfo=timezone.utc)
    jsonl = tmp_path / "sess-triggered.jsonl"
    jsonl.write_text('{"kind":"session_meta"}\n', encoding="utf-8")
    rel = relative_stat_path(jsonl)

    row = TrackingSessionORM(
        tracking_id="tid-triggered-guard",
        screener_id=1,
        screener_name="S",
        exchange="bybit",
        market_type="futures",
        symbol="ETHUSDT",
        status="triggered",
        statistics_file_path=rel,
        triggered_at=t1,
        entered_scanner_at=t0,
        created_at=t0,
        updated_at=t1,
    )

    class _FakeSession:
        async def get(self, _model: type, tid: str) -> TrackingSessionORM | None:
            return row if tid == "tid-triggered-guard" else None

        async def commit(self) -> None:
            return None

    class _FakeDb:
        session = _FakeSession()

    class _FakeCtx:
        async def __aenter__(self) -> _FakeDb:
            return _FakeDb()

        async def __aexit__(self, *_a: object) -> None:
            return None

    logged: list[dict] = []

    monkeypatch.setattr(
        "app.screener.scanner_runtime.Database.session_context",
        lambda: _FakeCtx(),
    )
    monkeypatch.setattr(
        "app.screener.scanner_runtime.absolute_stat_path",
        lambda _rel: jsonl,
    )
    monkeypatch.setattr("app.screener.scanner_runtime.log_signals_event", logged.append)

    await scanner_runtime._async_tombstone_untriggered_session(  # noqa: SLF001
        "tid-triggered-guard", rel,
    )

    assert jsonl.is_file()
    assert row.status == "triggered"
    assert row.statistics_file_path == rel
    assert row.triggered_at == t1
    assert logged == []


@pytest.mark.asyncio
async def test_tombstone_skips_when_jsonl_has_triggered_event(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """JSONL with triggered event blocks tombstone when DB row still active."""
    from app.database.models import TrackingSessionORM
    from app.screener.statistics_store import append_line, relative_stat_path, session_file_path

    monkeypatch.setattr(
        "app.screener.statistics_store._STAT_ROOT",
        tmp_path / "statistics-data",
    )
    monkeypatch.setattr(
        "app.screener.statistics_store.app_root_dir",
        lambda: tmp_path,
    )

    t0 = datetime(2026, 6, 9, 12, 0, 0, tzinfo=timezone.utc)
    tid = "tidjsonltrigger00001"
    jsonl = session_file_path(
        exchange="bybit",
        market_type="futures",
        symbol="SOLUSDT",
        tracking_id=tid,
        day=t0,
    )
    append_line(jsonl, {"kind": "session_meta", "tracking_id": tid})
    append_line(
        jsonl,
        {
            "kind": "event",
            "tracking_id": tid,
            "event": "triggered",
            "ts": t0.isoformat(),
        },
    )
    rel = relative_stat_path(jsonl)

    row = TrackingSessionORM(
        tracking_id=tid,
        screener_id=1,
        screener_name="S",
        exchange="bybit",
        market_type="futures",
        symbol="SOLUSDT",
        status="active",
        statistics_file_path=rel,
        entered_scanner_at=t0,
        created_at=t0,
        updated_at=t0,
    )

    class _FakeSession:
        async def get(self, _model: type, key: str) -> TrackingSessionORM | None:
            return row if key == tid else None

        async def commit(self) -> None:
            return None

    class _FakeDb:
        session = _FakeSession()

    class _FakeCtx:
        async def __aenter__(self) -> _FakeDb:
            return _FakeDb()

        async def __aexit__(self, *_a: object) -> None:
            return None

    monkeypatch.setattr(
        "app.screener.scanner_runtime.Database.session_context",
        lambda: _FakeCtx(),
    )
    monkeypatch.setattr("app.screener.scanner_runtime.log_signals_event", lambda _p: None)

    await scanner_runtime._async_tombstone_untriggered_session(tid, rel)  # noqa: SLF001

    assert jsonl.is_file()
    assert row.status == "active"
    assert row.statistics_file_path == rel


def test_prune_triggered_session_schedules_finalize_not_tombstone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Triggered session evicted from top-N after posttrack → finalize, not tombstone."""
    finalized: list[str] = []
    tombstones: list[str] = []

    def _capture_completion(st: object, sc: int, sym: str) -> None:
        finalized.append(getattr(st, "tracking_id", ""))

    async def _fake_tombstone(tid: str, _rel: str | None) -> None:
        tombstones.append(tid)

    monkeypatch.setattr(scanner_runtime, "_maybe_emit_completion", _capture_completion)
    monkeypatch.setattr(
        scanner_runtime, "_async_tombstone_untriggered_session", _fake_tombstone,
    )

    tid = "tid-prune-triggered"
    st = scanner_runtime._SessionState(  # noqa: SLF001
        tracking_id=tid,
        entered_monotonic=time.monotonic(),
        triggered=True,
        posttracking_until=time.time() - 1.0,
        statistics_path="statistics-data/x.jsonl",
    )
    scanner_runtime._sessions[(2, "XRPUSDT")] = st  # noqa: SLF001
    scanner_runtime._triggered_tracking_ids.add(tid)

    scanner_runtime.prune_sessions_not_in_set(2, set())

    assert tid in finalized
    assert tombstones == []
    assert (2, "XRPUSDT") not in scanner_runtime._sessions


@pytest.mark.asyncio
async def test_session_is_triggered_async_heals_from_db(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """session_is_triggered_async reads triggered_at when memory flag is stale."""
    from app.database.models import TrackingSessionORM

    t0 = datetime(2026, 6, 16, 10, 0, 0, tzinfo=timezone.utc)
    t1 = datetime(2026, 6, 16, 10, 1, 0, tzinfo=timezone.utc)
    tid = "tid-async-heal"
    row = TrackingSessionORM(
        tracking_id=tid,
        screener_id=5,
        screener_name="S",
        exchange="bybit",
        market_type="futures",
        symbol="LINKUSDT",
        status="triggered",
        triggered_at=t1,
        entered_scanner_at=t0,
        created_at=t0,
        updated_at=t1,
    )

    class _FakeSession:
        async def get(self, _model: type, key: str) -> TrackingSessionORM | None:
            return row if key == tid else None

    class _FakeDb:
        session = _FakeSession()

    class _FakeCtx:
        async def __aenter__(self) -> _FakeDb:
            return _FakeDb()

        async def __aexit__(self, *_a: object) -> None:
            return None

    monkeypatch.setattr(
        "app.screener.scanner_runtime.Database.session_context",
        lambda: _FakeCtx(),
    )
    monkeypatch.setattr(
        "app.screener.scanner_runtime._jsonl_contains_triggered_event",
        lambda *_a, **_k: False,
    )

    scanner_runtime._sessions[(5, "LINKUSDT")] = scanner_runtime._SessionState(  # noqa: SLF001
        tracking_id=tid,
        entered_monotonic=time.monotonic(),
        triggered=False,
        statistics_path="statistics-data/link.jsonl",
    )

    assert await scanner_runtime.session_is_triggered_async(5, "LINKUSDT") is True
    st = scanner_runtime._sessions[(5, "LINKUSDT")]
    assert st.triggered is True
    assert tid in scanner_runtime._triggered_tracking_ids


@pytest.mark.asyncio
async def test_session_is_triggered_async_backfills_triggered_at_from_jsonl(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """JSONL event triggered без triggered_at в БД — backfill для каталога analytics."""
    from app.database.models import TrackingSessionORM

    t0 = datetime(2026, 6, 16, 10, 0, 0, tzinfo=timezone.utc)
    tid = "tid-jsonl-backfill"
    rel = "statistics-data/backfill.jsonl"
    row = TrackingSessionORM(
        tracking_id=tid,
        screener_id=5,
        screener_name="S",
        exchange="bybit",
        market_type="futures",
        symbol="XRPUSDT",
        status="active",
        triggered_at=None,
        entered_scanner_at=t0,
        created_at=t0,
        updated_at=t0,
        statistics_file_path=rel,
    )
    jsonl = tmp_path / "statistics-data" / "backfill.jsonl"
    jsonl.parent.mkdir(parents=True)
    jsonl.write_text(
        json.dumps(
            {
                "kind": "event",
                "tracking_id": tid,
                "event": "triggered",
                "ts": t0.isoformat(),
            }
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "app.screener.statistics_store._STAT_ROOT",
        tmp_path / "statistics-data",
    )
    monkeypatch.setattr(
        "app.screener.statistics_store.app_root_dir",
        lambda: tmp_path,
    )

    class _FakeSession:
        async def get(self, _model: type, key: str) -> TrackingSessionORM | None:
            return row if key == tid else None

        async def commit(self) -> None:
            return None

    class _FakeDb:
        session = _FakeSession()

    class _FakeCtx:
        async def __aenter__(self) -> _FakeDb:
            return _FakeDb()

        async def __aexit__(self, *_a: object) -> None:
            return None

    upsert_calls: list[dict] = []

    async def _capture_upsert(**kwargs: object) -> None:
        upsert_calls.append(dict(kwargs))
        if kwargs.get("triggered_at") is not None:
            row.triggered_at = kwargs["triggered_at"]  # type: ignore[assignment]
            row.status = str(kwargs.get("status", row.status))

    monkeypatch.setattr(
        "app.screener.scanner_runtime.Database.session_context",
        lambda: _FakeCtx(),
    )
    monkeypatch.setattr(
        "app.screener.scanner_runtime._upsert_tracking_row",
        _capture_upsert,
    )

    scanner_runtime._sessions[(5, "XRPUSDT")] = scanner_runtime._SessionState(  # noqa: SLF001
        tracking_id=tid,
        entered_monotonic=time.monotonic(),
        triggered=False,
        statistics_path=rel,
    )

    assert await scanner_runtime.session_is_triggered_async(5, "XRPUSDT") is True
    assert upsert_calls
    assert upsert_calls[-1].get("triggered_at") is not None
    assert upsert_calls[-1].get("status") == "triggered"


def test_resolve_statistics_jsonl_empty_path_uses_tracking_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Регрессия API: пустой statistics_file_path — fallback по tracking_id."""
    stat_root = tmp_path / "statistics-data"
    monkeypatch.setattr("app.screener.statistics_store._STAT_ROOT", stat_root)
    monkeypatch.setattr(
        "app.screener.statistics_store.app_root_dir",
        lambda: tmp_path,
    )
    tid = "apifallback000000001"
    actual = session_file_path(
        exchange="bybit",
        market_type="futures",
        symbol="BTCUSDT",
        tracking_id=tid,
    )
    append_line(actual, {"kind": "sample", "tracking_id": tid, "seq": 1})
    assert resolve_statistics_jsonl("", tracking_id=tid) == actual


@pytest.mark.asyncio
async def test_maybe_emit_completion_scheduled_without_jsonl(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Посттрек завершается без statistics_enabled (без записи sample)."""
    scanner_runtime._cache.statistics_enabled = False  # noqa: SLF001
    finalized: list[tuple[str, object | None]] = []

    async def _capture_finalize(
        tid: str, path: object | None, _sc: int, _sym: str,
    ) -> None:
        finalized.append((tid, path))

    monkeypatch.setattr(
        scanner_runtime, "_finalize_completed_session", _capture_finalize,
    )
    tid = "tid-comp-no-jsonl"
    st = scanner_runtime._SessionState(  # noqa: SLF001
        tracking_id=tid,
        entered_monotonic=time.monotonic(),
        triggered=True,
        posttracking_until=time.time() - 1.0,
        statistics_path="statistics-data/x.jsonl",
    )
    scanner_runtime._sessions[(4, "SOLUSDT")] = st  # noqa: SLF001

    scanner_runtime.maybe_emit_completion_if_due(4, "SOLUSDT")
    await asyncio.sleep(0.05)

    assert len(finalized) == 1
    assert finalized[0][0] == tid


@pytest.mark.asyncio
async def test_finalize_completed_updates_db_when_jsonl_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """completed в БД пишется даже если JSONL persistence выключен."""
    from app.database.models import TrackingSessionORM

    scanner_runtime._cache.statistics_enabled = False  # noqa: SLF001
    t0 = datetime(2026, 6, 16, 8, 0, 0, tzinfo=timezone.utc)
    row = TrackingSessionORM(
        tracking_id="tid-finalize-db",
        screener_id=1,
        screener_name="S",
        exchange="bybit",
        market_type="futures",
        symbol="BTCUSDT",
        status="triggered",
        triggered_at=t0,
        created_at=t0,
        updated_at=t0,
    )

    class _FakeSession:
        async def get(self, _model: type, tid: str) -> TrackingSessionORM | None:
            return row if tid == "tid-finalize-db" else None

        async def commit(self) -> None:
            return None

    class _FakeDb:
        session = _FakeSession()

    class _FakeCtx:
        async def __aenter__(self) -> _FakeDb:
            return _FakeDb()

        async def __aexit__(self, *_a: object) -> None:
            return None

    append_calls: list[object] = []
    monkeypatch.setattr(
        "app.screener.scanner_runtime.Database.session_context",
        lambda: _FakeCtx(),
    )
    monkeypatch.setattr(
        "app.screener.scanner_runtime._schedule_jsonl_append",
        lambda path, obj: append_calls.append((path, obj)),
    )

    await scanner_runtime._finalize_completed_session(  # noqa: SLF001
        "tid-finalize-db", None, 1, "BTCUSDT",
    )

    assert append_calls == []
    assert row.status == "completed"
    assert row.completed_at is not None


@pytest.mark.asyncio
async def test_finalize_completed_backfills_missing_triggered_at(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """completed с пустым triggered_at — backfill для каталога analytics."""
    from app.database.models import TrackingSessionORM

    t0 = datetime(2026, 6, 16, 8, 0, 0, tzinfo=timezone.utc)
    row = TrackingSessionORM(
        tracking_id="tid-finalize-backfill",
        screener_id=1,
        screener_name="S",
        exchange="bybit",
        market_type="futures",
        symbol="ETHUSDT",
        status="active",
        triggered_at=None,
        created_at=t0,
        updated_at=t0,
    )

    class _FakeSession:
        async def get(self, _model: type, tid: str) -> TrackingSessionORM | None:
            return row if tid == "tid-finalize-backfill" else None

        async def commit(self) -> None:
            return None

    class _FakeDb:
        session = _FakeSession()

    class _FakeCtx:
        async def __aenter__(self) -> _FakeDb:
            return _FakeDb()

        async def __aexit__(self, *_a: object) -> None:
            return None

    monkeypatch.setattr(
        "app.screener.scanner_runtime.Database.session_context",
        lambda: _FakeCtx(),
    )

    await scanner_runtime._finalize_completed_session(  # noqa: SLF001
        "tid-finalize-backfill", None, 1, "ETHUSDT",
    )

    assert row.status == "completed"
    assert row.triggered_at is not None
    assert row.completed_at is not None


@pytest.mark.asyncio
async def test_reconcile_stale_tracking_sessions_on_startup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """После restart orphan active/triggered в БД → closed."""
    from app.database.models import TrackingSessionORM

    scanner_runtime.reset_statistics_runtime_state()
    t0 = datetime(2026, 6, 16, 7, 0, 0, tzinfo=timezone.utc)
    orphan = TrackingSessionORM(
        tracking_id="tid-orphan",
        screener_id=1,
        screener_name="S",
        exchange="bybit",
        market_type="futures",
        symbol="OLDUSDT",
        status="active",
        entered_scanner_at=t0,
        created_at=t0,
        updated_at=t0,
    )
    live_row = TrackingSessionORM(
        tracking_id="tid-live",
        screener_id=1,
        screener_name="S",
        exchange="bybit",
        market_type="futures",
        symbol="LIVEUSDT",
        status="active",
        entered_scanner_at=t0,
        created_at=t0,
        updated_at=t0,
    )
    scanner_runtime._sessions[(1, "LIVEUSDT")] = scanner_runtime._SessionState(  # noqa: SLF001
        tracking_id="tid-live",
        entered_monotonic=time.monotonic(),
    )

    class _FakeSession:
        async def execute(self, _stmt: object) -> object:
            class _R:
                def scalars(self) -> object:
                    class _S:
                        def all(self) -> list[TrackingSessionORM]:
                            return [orphan, live_row]

                    return _S()

            return _R()

        async def commit(self) -> None:
            return None

    class _FakeDb:
        session = _FakeSession()

    class _FakeCtx:
        async def __aenter__(self) -> _FakeDb:
            return _FakeDb()

        async def __aexit__(self, *_a: object) -> None:
            return None

    monkeypatch.setattr(
        "app.screener.scanner_runtime.Database.session_context",
        lambda: _FakeCtx(),
    )

    closed_n = await scanner_runtime.reconcile_stale_tracking_sessions_on_startup()
    assert closed_n == 1
    assert orphan.status == "closed"
    assert orphan.closed_at is not None
    assert live_row.status == "active"


def _make_session_row(
    *,
    tracking_id: str,
    symbol: str,
    created_at: datetime,
    triggered_at: datetime | None = None,
    completed_at: datetime | None = None,
    closed_at: datetime | None = None,
    status: str = "active",
) -> object:
    from types import SimpleNamespace

    return SimpleNamespace(
        tracking_id=tracking_id,
        symbol=symbol,
        screener_name="S",
        screener_id=1,
        exchange="bybit",
        market_type="futures",
        status=status,
        triggered_at=triggered_at,
        completed_at=completed_at,
        closed_at=closed_at,
        entered_scanner_at=created_at,
        created_at=created_at,
        updated_at=closed_at or completed_at or triggered_at or created_at,
        statistics_file_path=None,
    )


def test_merge_analytics_session_catalog_includes_old_triggered_outside_tail() -> None:
    """Регрессия PORTALUSDT: triggered вне top-1000 по created_at остаётся в каталоге."""
    from app.screener.tracking_timeline import (
        ANALYTICS_RECENT_TAIL_LIMIT,
        merge_analytics_session_catalog,
    )

    t_old = datetime(2026, 6, 16, 20, 50, 48, tzinfo=timezone.utc)
    t_trig = datetime(2026, 6, 16, 21, 5, 23, tzinfo=timezone.utc)
    t_done = datetime(2026, 6, 16, 21, 35, 23, tzinfo=timezone.utc)
    portal = _make_session_row(
        tracking_id="43faeb01a30c480086f9",
        symbol="PORTALUSDT",
        created_at=t_old,
        triggered_at=t_trig,
        completed_at=t_done,
        status="completed",
    )
    recent_tail = [
        _make_session_row(
            tracking_id=f"recent-{i:04d}",
            symbol=f"SYM{i}",
            created_at=datetime(2026, 6, 17, 12, 0, i % 60, tzinfo=timezone.utc),
        )
        for i in range(ANALYTICS_RECENT_TAIL_LIMIT + 1)
    ]
    merged = merge_analytics_session_catalog([portal], recent_tail[:ANALYTICS_RECENT_TAIL_LIMIT])
    ids = {r.tracking_id for r in merged}
    assert "43faeb01a30c480086f9" in ids
    assert len(merged) == ANALYTICS_RECENT_TAIL_LIMIT + 1


def test_merge_analytics_session_catalog_dedupes_triggered_in_tail() -> None:
    from app.screener.tracking_timeline import merge_analytics_session_catalog

    t0 = datetime(2026, 6, 17, 10, 0, 0, tzinfo=timezone.utc)
    t1 = datetime(2026, 6, 17, 10, 5, 0, tzinfo=timezone.utc)
    row = _make_session_row(
        tracking_id="dup-tid",
        symbol="BTCUSDT",
        created_at=t0,
        triggered_at=t1,
        status="triggered",
    )
    merged = merge_analytics_session_catalog([row], [row])
    assert len(merged) == 1
    assert merged[0].tracking_id == "dup-tid"


def test_merge_analytics_session_catalog_sorts_by_latest_activity() -> None:
    from app.screener.tracking_timeline import merge_analytics_session_catalog

    older = _make_session_row(
        tracking_id="old-triggered",
        symbol="AAAUSDT",
        created_at=datetime(2026, 6, 15, 8, 0, 0, tzinfo=timezone.utc),
        triggered_at=datetime(2026, 6, 15, 9, 0, 0, tzinfo=timezone.utc),
        status="triggered",
    )
    newer = _make_session_row(
        tracking_id="new-active",
        symbol="BBBUSDT",
        created_at=datetime(2026, 6, 17, 12, 0, 0, tzinfo=timezone.utc),
    )
    merged = merge_analytics_session_catalog([older], [newer])
    assert merged[0].tracking_id == "old-triggered"
    assert merged[1].tracking_id == "new-active"


def test_merge_analytics_session_catalog_keeps_only_newest_deleted_tail() -> None:
    from app.screener.tracking_timeline import (
        ANALYTICS_DELETED_RETENTION,
        merge_analytics_session_catalog,
    )

    base = datetime(2026, 6, 17, 10, 0, 0, tzinfo=timezone.utc)
    deleted_tail = [
        _make_session_row(
            tracking_id=f"deleted-{i:03d}",
            symbol=f"DEL{i}",
            created_at=base,
            closed_at=datetime(2026, 6, 17, 10, i % 60, 0, tzinfo=timezone.utc),
            status="deleted",
        )
        for i in range(ANALYTICS_DELETED_RETENTION)
    ]
    older_deleted = _make_session_row(
        tracking_id="deleted-old",
        symbol="OLD",
        created_at=datetime(2026, 6, 10, 8, 0, 0, tzinfo=timezone.utc),
        closed_at=datetime(2026, 6, 10, 8, 5, 0, tzinfo=timezone.utc),
        status="deleted",
    )
    merged = merge_analytics_session_catalog([], [], deleted_tail)
    ids = {r.tracking_id for r in merged}
    assert len(ids) == ANALYTICS_DELETED_RETENTION
    assert "deleted-old" not in ids
    assert older_deleted.tracking_id not in ids


def test_build_tracking_timeline_completed_passes_default_status_labels() -> None:
    from app.screener.tracking_timeline import build_tracking_timeline

    t0 = datetime(2026, 6, 16, 20, 50, 48, tzinfo=timezone.utc)
    t_done = datetime(2026, 6, 16, 21, 35, 23, tzinfo=timezone.utc)
    row = _make_session_row(
        tracking_id="43faeb01a30c480086f9",
        symbol="PORTALUSDT",
        created_at=t0,
        triggered_at=datetime(2026, 6, 16, 21, 5, 23, tzinfo=timezone.utc),
        completed_at=t_done,
        status="completed",
    )
    labels = {e["label"] for e in build_tracking_timeline(row)}  # type: ignore[arg-type]
    default_enabled = {
        "start", "abandoned", "active", "triggered", "posttracking", "completed", "closed",
    }
    assert labels <= default_enabled
    assert "triggered" in labels
    assert "completed" in labels
