"""Тесты режима «Тест» (оценка фильтров для админки)."""

from __future__ import annotations

import pytest
from unicex import Exchange, MarketType

from app.schemas.dtos import SettingsDTO
from app.schemas.enums import TextTemplateType
from app.screener.test_mode_eval import evaluate_test_mode_snapshot


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
