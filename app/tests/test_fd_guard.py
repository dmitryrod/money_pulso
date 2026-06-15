"""Тесты мониторинга FD и порога recycle."""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from app.utils import fd_guard as fg


def test_fd_pressure_snapshot_ratio() -> None:
    snap = fg.FdPressureSnapshot(
        open_fds=800,
        soft_limit=1000,
        ratio=0.8,
        recycle_threshold=0.7,
    )
    assert snap.is_pressure is True


def test_should_trigger_fd_recycle_respects_interval() -> None:
    snap = fg.FdPressureSnapshot(
        open_fds=900,
        soft_limit=1000,
        ratio=0.9,
        recycle_threshold=0.7,
    )
    now = time.time()
    assert fg.should_trigger_fd_recycle(snap, 0.0, now=now) is True
    assert fg.should_trigger_fd_recycle(snap, now - 10, now=now) is False


def test_should_not_trigger_below_threshold() -> None:
    snap = fg.FdPressureSnapshot(
        open_fds=100,
        soft_limit=1000,
        ratio=0.1,
        recycle_threshold=0.7,
    )
    assert fg.should_trigger_fd_recycle(snap, 0.0, now=time.time()) is False


@patch("app.utils.fd_guard.open_fd_count", return_value=7200)
@patch("app.utils.fd_guard.soft_fd_limit", return_value=65536)
def test_fd_pressure_payload(_lim: object, _cnt: object) -> None:
    payload = fg.fd_pressure_payload(fg.get_fd_pressure_snapshot())
    assert payload["open_fds"] == 7200
    assert payload["fd_soft_limit"] == 65536
    assert payload["fd_pressure"] is False


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("0.75", 0.75),
        ("", 0.70),
        ("bad", 0.70),
    ],
)
def test_fd_pressure_recycle_ratio_env(
    monkeypatch: pytest.MonkeyPatch, raw: str, expected: float
) -> None:
    if raw:
        monkeypatch.setenv("FD_PRESSURE_RECYCLE_RATIO", raw)
    else:
        monkeypatch.delenv("FD_PRESSURE_RECYCLE_RATIO", raising=False)
    assert fg.fd_pressure_recycle_ratio() == expected
