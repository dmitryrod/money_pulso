"""Регрессия RCA: PD not_enough_klines, LQ/trigger gate, история парсеров.

Фиксируют симптомы prod (~2026-06-18) и контракт, который должен восстановить Prompt 2.
"""

from __future__ import annotations

import time

import pytest
from unicex import Exchange, MarketType

from app.schemas.dtos import SettingsDTO
from app.schemas.enums import TextTemplateType
from app.screener.filters.pump_dump_filter import PumpDumpFilter
from app.screener.parsers.abstract import Parser
from app.screener.parsers.agg_trades import AggTradesParser
from app.screener.test_mode_eval import all_filters_ok, evaluate_test_mode_snapshot


def _settings(**kwargs: object) -> SettingsDTO:
    base: dict[str, object] = {
        "id": 1,
        "enabled": True,
        "name": "test",
        "exchange": Exchange.BYBIT,
        "market_type": MarketType.FUTURES,
        "blacklist": None,
        "whitelist": None,
        "debug": False,
        "pd_interval_sec": 3600,
        "pd_min_change_pct": 1.0,
        "oi_interval_sec": 3600,
        "oi_min_change_pct": 1.0,
        "oi_min_change_usd": None,
        "fr_min_value_pct": None,
        "fr_max_value_pct": None,
        "vl_interval_sec": None,
        "vl_min_multiplier": None,
        "lq_interval_sec": 3600,
        "lq_min_amount_usd": None,
        "lq_min_amount_pct": 2.0,
        "dv_min_usd": 100_000.0,
        "dv_max_usd": None,
        "dp_min_pct": None,
        "dp_max_pct": None,
        "max_day_alerts": None,
        "timeout_sec": 60,
        "chat_id": 1,
        "bot_token": "x",
        "text_template_type": TextTemplateType.DEFAULT,
    }
    base.update(kwargs)
    return SettingsDTO(**base)


def _single_kline(now_ms: int | None = None) -> list[dict[str, float | int | str]]:
    ts = now_ms if now_ms is not None else int(time.time() * 1000)
    return [
        {
            "s": "BELUSDT",
            "t": ts,
            "o": 0.094,
            "h": 0.0941,
            "l": 0.0939,
            "c": 0.09405,
            "v": 1000.0,
            "q": 94.0,
            "T": None,
            "x": False,
        }
    ]


def test_pump_dump_single_kline_in_hour_window_reports_not_enough_klines() -> None:
    """Симптом prod: одна свеча в буфере agg_trades → reason=not_enough_klines."""
    result = PumpDumpFilter.process(
        klines=_single_kline(),
        pd_interval_sec=3600,
        pd_min_change_pct=1.0,
    )
    assert result.ok is False
    assert result.metadata.get("reason") == "not_enough_klines"
    assert result.price_change_pct is None


def test_pump_dump_two_klines_in_window_can_compute_pct() -> None:
    """Контракт: >=2 свечей в окне pd_interval_sec — PD считается."""
    now_ms = int(time.time() * 1000)
    klines = [
        {
            "s": "BELUSDT",
            "t": now_ms - 3_600_000 + 60_000,
            "o": 0.090,
            "h": 0.091,
            "l": 0.089,
            "c": 0.090,
            "v": 1.0,
            "q": 1.0,
            "T": None,
            "x": True,
        },
        {
            "s": "BELUSDT",
            "t": now_ms - 30_000,
            "o": 0.090,
            "h": 0.095,
            "l": 0.090,
            "c": 0.092,
            "v": 1.0,
            "q": 1.0,
            "T": None,
            "x": False,
        },
    ]
    result = PumpDumpFilter.process(
        klines=klines,
        pd_interval_sec=3600,
        pd_min_change_pct=1.0,
    )
    assert result.ok is True
    assert result.price_change_pct is not None
    assert result.metadata.get("reason") is None


def test_evaluate_test_mode_pd_row_shows_not_enough_klines_with_single_kline() -> None:
    """Интеграция test_mode: карточка есть (OI ok), PD — not_enough_klines."""
    now_ms = int(time.time() * 1000)
    oi = [
        {"t": now_ms - 3_600_000, "v": 100.0, "u": "coins"},
        {"t": now_ms, "v": 110.0, "u": "coins"},
    ]
    out = evaluate_test_mode_snapshot(
        "BELUSDT",
        "BEL",
        MarketType.FUTURES,
        _settings(),
        {"q": 1_500_000.0, "p": 5.0},
        _single_kline(now_ms),
        oi,
        0.005,
        [],
        set(),
        set(),
        daily_signal_count=1,
    )
    assert out is not None
    pd_row = next(r for r in out["test_filters"] if r["id"] == "pd")
    assert pd_row["ok"] is False
    assert pd_row["current"].get("reason") == "not_enough_klines"
    assert pd_row["current"].get("price_change_pct") is None


def test_all_filters_ok_false_when_pd_or_lq_fail_blocks_trigger_gate() -> None:
    """triggered/completed: all_filters_ok требует ok у всех строк, включая PD и LQ."""
    rows = [
        {"id": "pd", "enabled": True, "ok": False},
        {"id": "oi", "enabled": True, "ok": True},
        {"id": "lq", "enabled": True, "ok": False},
        {"id": "dv", "enabled": True, "ok": True, "is_gate": True},
    ]
    assert all_filters_ok(rows) is False


def test_parser_max_history_shorter_than_prod_filter_intervals() -> None:
    """Failing until fix: парсеры хранят 15m, скринер test — интервалы 3600s.

    Не единственная причина not_enough_klines (нужно >=2 точки), но ломает семантику
    «часового» окна PD/LQ/OI — фактически смотрят только последние 15 минут истории.
    """
    prod_interval_sec = 3600
    assert Parser._MAX_HISTORY_LEN >= prod_interval_sec


def test_lq_zero_amount_yields_negative_contribution_when_pct_threshold_set() -> None:
    """LQ вклад -1 при нулевых ликвидациях — ожидаемая математика score, не отдельный баг."""
    from app.screener.test_mode_eval import _filter_score_contribution_for_row

    row = {
        "id": "lq",
        "ok": False,
        "current": {"amount_usdt": 0.0, "lq_pct_of_daily_volume": 0.0},
        "thresholds": {"lq_min_amount_pct": 2.0},
    }
    assert _filter_score_contribution_for_row(row) == pytest.approx(-1.0)


def _rest_kline(symbol: str, open_ms: int, close: float) -> dict[str, float | int | str | None]:
    return {
        "s": symbol,
        "t": open_ms,
        "o": close,
        "h": close,
        "l": close,
        "c": close,
        "v": 1.0,
        "q": close,
        "T": open_ms + 60_000,
        "x": True,
    }


def test_merge_klines_seeds_two_points_for_pd_hour_window() -> None:
    """REST bootstrap + merge: >=2 свечей в pd_interval_sec 3600s."""
    parser = AggTradesParser(Exchange.BYBIT, MarketType.FUTURES)
    now_ms = int(time.time() * 1000)
    incoming = [
        _rest_kline("BELUSDT", now_ms - 3_600_000, 0.090),
        _rest_kline("BELUSDT", now_ms - 60_000, 0.092),
    ]
    parser._merge_klines("BELUSDT", incoming)

    klines = parser._klines["BELUSDT"]
    assert len(klines) >= 2
    result = PumpDumpFilter.process(
        klines=klines,
        pd_interval_sec=3600,
        pd_min_change_pct=1.0,
    )
    assert result.metadata.get("reason") != "not_enough_klines"
    assert result.price_change_pct is not None


def test_merge_klines_ws_overrides_rest_on_same_open_time() -> None:
    """WS-свеча с тем же open_time перекрывает REST при merge."""
    parser = AggTradesParser(Exchange.BYBIT, MarketType.FUTURES)
    open_ms = 1_700_000_000_000
    parser._klines["BELUSDT"] = [
        {
            "s": "BELUSDT",
            "t": open_ms,
            "o": 0.10,
            "h": 0.11,
            "l": 0.09,
            "c": 0.105,
            "v": 2.0,
            "q": 2.0,
            "T": None,
            "x": False,
        }
    ]
    incoming = [_rest_kline("BELUSDT", open_ms, 0.08)]

    parser._merge_klines("BELUSDT", incoming)

    assert len(parser._klines["BELUSDT"]) == 1
    assert parser._klines["BELUSDT"][0]["c"] == pytest.approx(0.105)


def test_merge_klines_trims_beyond_max_history_len() -> None:
    """Merge обрезает буфер до Parser._MAX_HISTORY_LEN секунд."""
    parser = AggTradesParser(Exchange.BYBIT, MarketType.FUTURES)
    now_ms = int(time.time() * 1000)
    span_sec = Parser._MAX_HISTORY_LEN + 120
    incoming = [
        _rest_kline("BELUSDT", now_ms - span_sec * 1000, 0.08),
        _rest_kline("BELUSDT", now_ms - 60_000, 0.09),
    ]

    parser._merge_klines("BELUSDT", incoming)

    klines = parser._klines["BELUSDT"]
    assert len(klines) == 1
    assert klines[0]["t"] == now_ms - 60_000



@pytest.mark.asyncio
async def test_clear_klines_empties_buffer_after_stop_like_recycle() -> None:
    """После stop()/clear_klines буфер пуст — bootstrap не skip по len>=2."""
    parser = AggTradesParser(Exchange.BYBIT, MarketType.FUTURES)
    now_ms = int(time.time() * 1000)
    parser._klines["BELUSDT"] = [
        _rest_kline("BELUSDT", now_ms - 3_600_000, 0.090),
        _rest_kline("BELUSDT", now_ms - 180_000, 0.091),
    ]
    assert len(parser._klines["BELUSDT"]) >= 2

    await parser.clear_klines()

    assert len(parser._klines) == 0
    assert parser._klines_need_rest_bootstrap("BELUSDT") is True


def test_klines_need_rest_bootstrap_true_when_newest_stale() -> None:
    """Stale-aware: len>=2 но newest старше KLINES_BOOTSTRAP_STALE_SEC → REST нужен."""
    parser = AggTradesParser(Exchange.BYBIT, MarketType.FUTURES)
    now_ms = int(time.time() * 1000)
    stale_sec = AggTradesParser.KLINES_BOOTSTRAP_STALE_SEC + 30
    parser._klines["BELUSDT"] = [
        _rest_kline("BELUSDT", now_ms - 600_000, 0.090),
        _rest_kline("BELUSDT", now_ms - stale_sec * 1000, 0.091),
    ]
    assert parser._klines_need_rest_bootstrap("BELUSDT", now_ms=now_ms) is True


def test_klines_need_rest_bootstrap_false_when_fresh() -> None:
    """Свежий буфер >=2 — REST bootstrap не нужен."""
    parser = AggTradesParser(Exchange.BYBIT, MarketType.FUTURES)
    now_ms = int(time.time() * 1000)
    parser._klines["BELUSDT"] = [
        _rest_kline("BELUSDT", now_ms - 120_000, 0.090),
        _rest_kline("BELUSDT", now_ms - 30_000, 0.092),
    ]
    assert parser._klines_need_rest_bootstrap("BELUSDT", now_ms=now_ms) is False


@pytest.mark.asyncio
async def test_stale_klines_after_recycle_bootstrap_refills_for_pd(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Симптом RCA: stale >=2 после recycle → bootstrap merge → PD не not_enough_klines."""
    from contextlib import asynccontextmanager

    parser = AggTradesParser(Exchange.BYBIT, MarketType.FUTURES)
    now_ms = int(time.time() * 1000)
    stale_open = now_ms - (AggTradesParser.KLINES_BOOTSTRAP_STALE_SEC + 60) * 1000
    # Устаревшие 2 свечи: старый skip по len>=2 блокировал REST.
    parser._klines["BELUSDT"] = [
        _rest_kline("BELUSDT", stale_open - 60_000, 0.090),
        _rest_kline("BELUSDT", stale_open, 0.091),
    ]
    assert parser._klines_need_rest_bootstrap("BELUSDT", now_ms=now_ms) is True

    rest_incoming = [
        _rest_kline("BELUSDT", now_ms - 3_600_000, 0.090),
        _rest_kline("BELUSDT", now_ms - 60_000, 0.092),
    ]

    @asynccontextmanager
    async def fake_client_context(self, **kwargs):  # noqa: ANN001, ANN003
        yield object()

    async def fake_fetch(self, client, symbol):  # noqa: ANN001
        assert symbol == "BELUSDT"
        return list(rest_incoming)

    monkeypatch.setattr(AggTradesParser, "_client_context", fake_client_context)
    monkeypatch.setattr(AggTradesParser, "_fetch_futures_klines", fake_fetch)
    parser._is_running = True
    # Ускоряем sleep между батчами
    monkeypatch.setattr(AggTradesParser, "KLINES_BOOTSTRAP_DELAY_SEC", 0)

    await parser._bootstrap_klines_from_rest([["BELUSDT"]])

    klines = parser._klines["BELUSDT"]
    assert len(klines) >= 2
    # newest из REST должен быть свежим
    assert max(int(k["t"]) for k in klines) == now_ms - 60_000
    result = PumpDumpFilter.process(
        klines=klines,
        pd_interval_sec=3600,
        pd_min_change_pct=1.0,
    )
    assert result.metadata.get("reason") != "not_enough_klines"
    assert result.price_change_pct is not None


@pytest.mark.asyncio
async def test_stop_clears_klines_so_pd_not_stuck_on_stale_buffer() -> None:
    """stop() очищает _klines — контракт recycle/restart."""
    parser = AggTradesParser(Exchange.BYBIT, MarketType.FUTURES)
    now_ms = int(time.time() * 1000)
    parser._klines["BELUSDT"] = [
        _rest_kline("BELUSDT", now_ms - 200_000, 0.09),
        _rest_kline("BELUSDT", now_ms - 150_000, 0.091),
    ]
    parser._websockets = []

    await parser.stop()

    assert len(parser._klines) == 0
    # Пустой буфер → PD no_klines до REST bootstrap (не stuck на stale not_enough).
    result = PumpDumpFilter.process(
        klines=[],
        pd_interval_sec=3600,
        pd_min_change_pct=1.0,
    )
    assert result.metadata.get("reason") == "no_klines"
