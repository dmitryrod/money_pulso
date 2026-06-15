"""Мониторинг открытых файловых дескрипторов и сигнал давления для recycle WebSocket."""

from __future__ import annotations

import os
import resource
from dataclasses import dataclass
from typing import Any

import psutil

_DEFAULT_PRESSURE_RATIO = 0.70
_DEFAULT_MIN_INTERVAL_SEC = 300


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return default
    try:
        return float(str(raw).strip().split()[0])
    except (ValueError, IndexError):
        return default


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return default
    try:
        return max(0, int(str(raw).strip().split()[0]))
    except (ValueError, IndexError):
        return default


def fd_pressure_recycle_ratio() -> float:
    """Доля soft ulimit, при превышении которой Operator делает recycle WS."""
    return min(0.95, max(0.1, _env_float("FD_PRESSURE_RECYCLE_RATIO", _DEFAULT_PRESSURE_RATIO)))


def fd_pressure_min_interval_sec() -> int:
    """Минимальный интервал между recycle по давлению FD (сек)."""
    return _env_int("FD_PRESSURE_MIN_INTERVAL_SEC", _DEFAULT_MIN_INTERVAL_SEC)


def soft_fd_limit() -> int:
    """Soft RLIMIT_NOFILE текущего процесса."""
    try:
        soft, _hard = resource.getrlimit(resource.RLIMIT_NOFILE)
        return int(soft)
    except (OSError, ValueError):
        return 1024


def open_fd_count() -> int | None:
    """Число открытых FD процесса или None при ошибке."""
    try:
        return int(psutil.Process().num_fds())
    except (AttributeError, OSError, psutil.Error):
        return None


@dataclass(frozen=True)
class FdPressureSnapshot:
    """Снимок давления на лимит FD."""

    open_fds: int | None
    soft_limit: int
    ratio: float | None
    recycle_threshold: float

    @property
    def is_pressure(self) -> bool:
        if self.open_fds is None or self.soft_limit <= 0:
            return False
        return (self.open_fds / self.soft_limit) >= self.recycle_threshold


def get_fd_pressure_snapshot() -> FdPressureSnapshot:
    """Текущий снимок для мониторинга и Operator."""
    limit = soft_fd_limit()
    count = open_fd_count()
    threshold = fd_pressure_recycle_ratio()
    ratio = (count / limit) if count is not None and limit > 0 else None
    return FdPressureSnapshot(
        open_fds=count,
        soft_limit=limit,
        ratio=ratio,
        recycle_threshold=threshold,
    )


def should_trigger_fd_recycle(
    snapshot: FdPressureSnapshot,
    last_recycle_ts: float,
    *,
    now: float,
) -> bool:
    """True, если пора принудительно перезапустить WS-парсеры из-за давления FD."""
    if not snapshot.is_pressure:
        return False
    interval = fd_pressure_min_interval_sec()
    if interval > 0 and (now - last_recycle_ts) < interval:
        return False
    return True


def fd_pressure_payload(snapshot: FdPressureSnapshot) -> dict[str, Any]:
    """Поля для `/admin_api/monitoring/metrics`."""
    return {
        "open_fds": snapshot.open_fds,
        "fd_soft_limit": snapshot.soft_limit,
        "fd_pressure_ratio": snapshot.ratio,
        "fd_recycle_threshold": snapshot.recycle_threshold,
        "fd_pressure": snapshot.is_pressure,
    }
