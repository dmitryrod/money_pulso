"""Тесты режима «Тест» (оценка фильтров для админки)."""

from __future__ import annotations

import time

import pytest
from unicex import Exchange, MarketType

from app.schemas.dtos import SettingsDTO
from app.schemas.enums import TextTemplateType
from app.screener.test_mode_eval import (
    evaluate_test_mode_snapshot,
    no_enabled_filters_ok,
)


def _settings(**kwargs: object) -> SettingsDTO:
    base: dict[str, object] = {
        "id": 1,
        "enabled": True,
        "name": "TestScr",
        "exchange": Exchange.BYBIT,
        "market_type": MarketType.FUTURES,
        "blacklist": None,
        "whitelist": None,
        "debug": False,
        "pd_interval_sec": None,
        "pd_min_change_pct": None,
        "oi_interval_sec": None,
        "oi_min_change_pct": None,
        "oi_min_change_usd": None,
        "fr_min_value_pct": None,
        "fr_max_value_pct": None,
        "vl_interval_sec": None,
        "vl_min_multiplier": None,
        "lq_interval_sec": None,
        "lq_min_amount_usd": None,
        "lq_min_amount_pct": None,
        "dv_min_usd": 1.0,
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


def test_gates_fail_without_klines() -> None:
    s = _settings()
    out = evaluate_test_mode_snapshot(
        "BTCUSDT",
        "BTC",
        MarketType.FUTURES,
        s,
        {"q": 1e9, "p": 1.0},
        [],
        [],
        0.0,
        [],
        set(),
        set(),
        daily_signal_count=1,
    )
    assert out is None


def test_all_content_filters_fail_returns_none() -> None:
    """DV включён, объём ниже порога — ни один фильтр не ok → None."""
    s = _settings(dv_min_usd=1e15, dv_max_usd=None)
    now_ms = 1_700_000_000_000
    klines = [
        {"t": now_ms - 120_000, "o": 1.0, "c": 1.0, "q": 1.0},
        {"t": now_ms, "o": 1.0, "c": 1.0, "q": 1.0},
    ]
    out = evaluate_test_mode_snapshot(
        "BTCUSDT",
        "BTC",
        MarketType.FUTURES,
        s,
        {"q": 1_000_000.0, "p": 2.5},
        klines,
        [],
        0.0,
        [],
        set(),
        set(),
        daily_signal_count=1,
    )
    assert out is None


def test_no_enabled_filters_ok_empty_or_none_is_false() -> None:
    assert no_enabled_filters_ok([]) is False
    assert no_enabled_filters_ok(None) is False


def test_no_enabled_filters_ok_true_when_all_enabled_off() -> None:
    assert (
        no_enabled_filters_ok(
            [
                {"id": "pd", "enabled": True, "ok": False},
                {"id": "oi", "enabled": True, "ok": False},
            ]
        )
        is True
    )


def test_no_enabled_filters_ok_false_when_any_enabled_ok() -> None:
    assert (
        no_enabled_filters_ok(
            [
                {"id": "pd", "enabled": True, "ok": True},
                {"id": "oi", "enabled": True, "ok": False},
            ]
        )
        is False
    )


def test_no_enabled_filters_ok_ignores_disabled_for_all_off_check() -> None:
    assert (
        no_enabled_filters_ok(
            [
                {"id": "pd", "enabled": False, "ok": True},
                {"id": "oi", "enabled": True, "ok": False},
            ]
        )
        is True
    )


def _klines_pd_pass(interval_sec: int = 120, *, margin_sec: int = 5) -> list[dict[str, float | int]]:
    """Свечи в окне PD относительно time.time() (как PumpDumpFilter).

    margin_sec — запас внутри окна, чтобы повторные вызовы evaluate в одном тесте
    не выкидывали первую свечу из окна.
    """
    now_ms = int(time.time() * 1000)
    margin_ms = margin_sec * 1000
    return [
        {"t": now_ms - interval_sec * 1000 + margin_ms, "o": 1.0, "c": 1.0, "q": 1.0},
        {"t": now_ms, "o": 1.0, "c": 1.05, "q": 1.0},
    ]


def test_dv_gate_fail_pd_ok_returns_none() -> None:
    """DV gate fail — пара не попадает в Scanner, даже если PD ok."""
    s = _settings(
        dv_min_usd=1e15,
        dv_max_usd=None,
        pd_interval_sec=120,
        pd_min_change_pct=1.0,
    )
    out = evaluate_test_mode_snapshot(
        "BTCUSDT",
        "BTC",
        MarketType.FUTURES,
        s,
        {"q": 1_000_000.0, "p": 2.5},
        _klines_pd_pass(),
        [],
        0.0,
        [],
        set(),
        set(),
        daily_signal_count=1,
    )
    assert out is None


def test_dv_pass_does_not_affect_score() -> None:
    """DV gate pass — объём не влияет на Score (только PD в расчёте)."""
    s = _settings(
        dv_min_usd=1e6,
        dv_max_usd=None,
        pd_interval_sec=120,
        pd_min_change_pct=1.0,
        dp_min_pct=None,
        dp_max_pct=None,
    )
    common = dict(
        symbol="BTCUSDT",
        ticker="BTC",
        market_type=MarketType.FUTURES,
        settings=s,
        klines=_klines_pd_pass(),
        open_interest=[],
        funding_rate=0.0,
        liquidations=[],
        blacklist=set(),
        whitelist=set(),
        daily_signal_count=1,
    )
    out_low = evaluate_test_mode_snapshot(**common, ticker_daily={"q": 2_000_000.0, "p": 2.5})
    out_high = evaluate_test_mode_snapshot(**common, ticker_daily={"q": 9_000_000_000.0, "p": 2.5})
    assert out_low is not None
    assert out_high is not None
    assert out_low["score"] == out_high["score"]


def test_dv_gate_row_last_when_enabled() -> None:
    """При включённом DV строка гейта — последняя в test_filters."""
    s = _settings(
        dv_min_usd=1e6,
        dv_max_usd=None,
        pd_interval_sec=120,
        pd_min_change_pct=1.0,
    )
    out = evaluate_test_mode_snapshot(
        "BTCUSDT",
        "BTC",
        MarketType.FUTURES,
        s,
        {"q": 5_000_000.0, "p": 2.5},
        _klines_pd_pass(),
        [],
        0.0,
        [],
        set(),
        set(),
        daily_signal_count=1,
    )
    assert out is not None
    ids = [r["id"] for r in out["test_filters"]]
    assert ids[-1] == "dv"
    assert out["test_filters"][-1].get("is_gate") is True
