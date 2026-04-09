from __future__ import annotations

import time

from app.unicex.types import OpenInterestItem  # type: ignore[attr-defined]

from .abstract import Filter, FilterResult


class OpenInterestFilterResult(FilterResult):
    """Результат фильтра по открытому интересу."""

    start_value: float | None = None
    final_value: float | None = None
    change_pct: float | None = None
    change_coins: float | None = None
    change_usdt: float | None = None


class OpenInterestFilter(Filter):
    """Фильтр по изменению открытого интереса."""

    @staticmethod
    def process(
        open_interest: list[OpenInterestItem],
        oi_interval_sec: int | None,
        oi_min_change_pct: float | None,
        oi_min_change_usd: float | None,
        last_price: float,
    ) -> OpenInterestFilterResult:
        """Проверяет рост OI за интервал по % и/или USD."""
        if not oi_interval_sec:
            return OpenInterestFilterResult(ok=False, metadata={})

        now_ms = int(time.time() * 1000)
        threshold_ms = now_ms - oi_interval_sec * 1000

        # Берём все точки за последний oi_interval_sec
        window = [item for item in open_interest if item["t"] >= threshold_ms]
        if len(window) < 2:
            return OpenInterestFilterResult(
                ok=False, metadata={"reason": "not_enough_points"}
            )

        # Ищем минимум и максимум OI внутри окна, чтобы поймать рост в любой момент интервала,
        # а не только между самой старой и самой новой точкой.
        min_item = min(window, key=lambda x: x["v"])
        max_item = max(window, key=lambda x: x["v"])

        start = float(min_item["v"])
        end = float(max_item["v"])

        change_coins = end - start
        change_pct = (change_coins / start * 100.0) if start > 0 else 0.0
        change_usdt = change_coins * float(last_price)

        ok = True
        if oi_min_change_pct is not None and change_pct < oi_min_change_pct:
            ok = False
        if oi_min_change_usd is not None and change_usdt < oi_min_change_usd:
            ok = False

        result = OpenInterestFilterResult(
            ok=ok,
            metadata={
                "start_value": start,
                "final_value": end,
                "change_pct": change_pct,
                "change_coins": change_coins,
                "change_usdt": change_usdt,
                "oi_interval_sec": oi_interval_sec,
                "oi_min_change_pct": oi_min_change_pct,
                "oi_min_change_usd": oi_min_change_usd,
            },
        )
        result.start_value = start
        result.final_value = end
        result.change_pct = change_pct
        result.change_coins = change_coins
        result.change_usdt = change_usdt
        return result

