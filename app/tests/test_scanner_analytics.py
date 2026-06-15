"""Тесты Scanner Analytics: runtime helpers и контракт JSONL sample."""

from __future__ import annotations

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
    yield
    scanner_runtime._sessions.clear()  # noqa: SLF001
    scanner_runtime._pending_signal_snapshots.clear()  # noqa: SLF001
    scanner_runtime._manual_close_ids.clear()  # noqa: SLF001
    scanner_runtime._cooldown_until.clear()  # noqa: SLF001


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
