"""Контракт API сигналов для UI (режим БД + card_snapshot)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import patch

from app.admin import signal_orm_row_to_dict
from app.database.models.signal import SignalORM


def test_signal_orm_row_to_dict_render_as_scanner_with_snapshot() -> None:
    snap = {
        "mode": "test",
        "symbol": "BTCUSDT",
        "telegram_text": "body",
        "test_filters": [{"id": "pd", "ok": True}],
        "scanner_duration_at_trigger_ms": 125000,
        "scanner_snapshot_frozen": True,
    }
    row = SignalORM(
        screener_name="S",
        screener_id=1,
        exchange="bybit",
        market_type="futures",
        symbol="BTCUSDT",
        telegram_text="body",
        telegram_ok=True,
        error=None,
        tracking_id="tid-abc",
        card_snapshot_json=json.dumps(snap, ensure_ascii=False),
    )
    row.id = 100
    row.created_at = datetime(2026, 4, 1, 12, 0, 0, tzinfo=timezone.utc)

    with patch("app.admin.get_cmc_rank_for_symbol", return_value=10):
        d = signal_orm_row_to_dict(row)

    assert d["render_as_scanner"] is True
    assert d["tracking_id"] == "tid-abc"
    assert d["stat_href"] == "/admin/analytics/stat-btcusdt-tid-abc"
    assert d["card_snapshot"]["scanner_duration_at_trigger_ms"] == 125000
    assert d["card_snapshot"]["scanner_snapshot_frozen"] is True
    assert d["cmc_rank"] == 10


def test_signal_orm_row_to_dict_no_snapshot_not_scanner_layout() -> None:
    row = SignalORM(
        screener_name="S",
        screener_id=1,
        exchange="bybit",
        market_type="futures",
        symbol="ETHUSDT",
        telegram_text="x",
        telegram_ok=True,
        error=None,
        tracking_id=None,
        card_snapshot_json=None,
    )
    row.id = 1
    row.created_at = datetime(2026, 4, 1, tzinfo=timezone.utc)

    with patch("app.admin.get_cmc_rank_for_symbol", return_value=None):
        d = signal_orm_row_to_dict(row)

    assert d["render_as_scanner"] is False
    assert d["card_snapshot"] is None
