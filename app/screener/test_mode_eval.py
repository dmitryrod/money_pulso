"""Независимая оценка фильтров для режима «Тест» в админке (гейты + хотя бы один ok)."""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any

from unicex import MarketType
from unicex.types import KlineDict, LiquidationDict, OpenInterestItem, TickerDailyItem

from app.models import ScreeningResult, SettingsDTO
from app.utils.coinmarketcap_rank import get_cmc_rank_for_symbol
from app.utils.generate_text import generate_text

from .filters import (
    BlacklistFilter,
    DailyPriceFilter,
    DailyVolumeFilter,
    FundingRateFilter,
    LiquidationsSumFilter,
    OnlyUsdtPairsFilter,
    OpenInterestFilter,
    PumpDumpFilter,
    VolumeMultiplierFilter,
    WhitelistFilter,
)


_EPS = 1e-9


def _f(x: Any) -> float | None:
    if x is None:
        return None
    try:
        v = float(x)
        if math.isnan(v) or math.isinf(v):
            return None
        return v
    except (TypeError, ValueError):
        return None


def _tie_margin_for_row(row: dict[str, Any]) -> float | None:
    """Безразмерный «запас» для одной строки test_filters при ok; иначе None."""
    if not row.get("ok"):
        return None
    cur = row.get("current") or {}
    thr = row.get("thresholds") or {}
    fid = row.get("id")

    if fid == "dv":
        vol = _f(cur.get("daily_volume_usd"))
        mn = _f(thr.get("dv_min_usd"))
        mx = _f(thr.get("dv_max_usd"))
        if vol is None:
            return None
        if mn is not None and mx is not None:
            slack = min(vol - mn, mx - vol)
        elif mn is not None:
            slack = vol - mn
        elif mx is not None:
            slack = mx - vol
        else:
            return 0.0
        return max(0.0, slack) / max(vol, _EPS)

    if fid == "dp":
        p = _f(cur.get("daily_price_change_pct"))
        mn = _f(thr.get("dp_min_pct"))
        mx = _f(thr.get("dp_max_pct"))
        if p is None:
            return None
        if mn is not None and mx is not None:
            slack = min(p - mn, mx - p)
        elif mn is not None:
            slack = p - mn
        elif mx is not None:
            slack = mx - p
        else:
            return 0.0
        return max(0.0, slack) / max(abs(p), 1.0)

    if fid == "pd":
        pct = _f(cur.get("price_change_pct"))
        mn = _f(thr.get("pd_min_change_pct"))
        if pct is None or mn is None:
            return None
        if mn >= 0:
            excess = pct - mn
        else:
            excess = mn - pct
        return max(0.0, excess) / max(abs(mn), _EPS)

    if fid == "vl":
        mult = _f(cur.get("multiplier"))
        vmin = _f(thr.get("vl_min_multiplier"))
        if mult is None or vmin is None or vmin <= 0:
            return None
        return max(0.0, mult / vmin - 1.0)

    if fid == "oi":
        pct = _f(cur.get("change_pct"))
        usd = _f(cur.get("change_usdt"))
        mnp = _f(thr.get("oi_min_change_pct"))
        mnu = _f(thr.get("oi_min_change_usd"))
        margins: list[float] = []
        if mnp is not None and pct is not None:
            if mnp >= 0:
                margins.append(max(0.0, pct - mnp) / max(abs(mnp), _EPS))
            else:
                margins.append(max(0.0, mnp - pct) / max(abs(mnp), _EPS))
        if mnu is not None and usd is not None:
            if mnu >= 0:
                margins.append(max(0.0, usd - mnu) / max(abs(mnu), _EPS))
            else:
                margins.append(max(0.0, mnu - usd) / max(abs(mnu), _EPS))
        if not margins:
            return None
        return sum(margins) / len(margins)

    if fid == "fr":
        v = _f(cur.get("funding_rate_pct"))
        mn = _f(thr.get("fr_min_value_pct"))
        mx = _f(thr.get("fr_max_value_pct"))
        if v is None:
            return None
        if mn is not None and mx is not None:
            span = mx - mn
            if span <= _EPS:
                return 0.0
            dist = min(v - mn, mx - v)
            return max(0.0, dist) / max(span, _EPS)
        if mn is not None:
            return max(0.0, v - mn) / max(abs(mn), _EPS)
        if mx is not None:
            return max(0.0, mx - v) / max(abs(mx), _EPS)
        return None

    if fid == "lq":
        amt = _f(cur.get("amount_usdt"))
        lpct = _f(cur.get("lq_pct_of_daily_volume"))
        m_usd = _f(thr.get("lq_min_amount_usd"))
        m_pct = _f(thr.get("lq_min_amount_pct"))
        margins = []
        if m_usd is not None and amt is not None:
            margins.append(max(0.0, amt - m_usd) / max(m_usd, _EPS))
        if m_pct is not None and lpct is not None:
            margins.append(max(0.0, lpct - m_pct) / max(abs(m_pct), _EPS))
        if not margins:
            return None
        return sum(margins) / len(margins)

    return None


def _finite_contribution(x: float) -> float:
    """Ограничение для JSON: без inf/nan."""
    if math.isnan(x):
        return 0.0
    if math.isinf(x):
        return 1e6 if x > 0 else -1e6
    return x


def _filter_score_contribution_for_row(row: dict[str, Any]) -> float:
    """Signed-вклад по фильтру: 0 у границы «ровно порог», >0 лучше порога, <0 хуже; без усечения 0–100."""
    cur = row.get("current") or {}
    thr = row.get("thresholds") or {}
    fid = row.get("id")
    ok = bool(row.get("ok"))

    if fid == "dv":
        vol = _f(cur.get("daily_volume_usd"))
        mn = _f(thr.get("dv_min_usd"))
        mx = _f(thr.get("dv_max_usd"))
        if vol is None:
            return 0.0
        if mn is not None and mx is not None and mx > mn + _EPS:
            if vol < mn and mn > _EPS:
                return _finite_contribution(vol / mn - 1.0)
            if vol > mx and vol > _EPS:
                return _finite_contribution(mx / vol - 1.0)
            if mn <= vol <= mx:
                r_lo = vol / mn - 1.0 if mn > _EPS else 0.0
                r_hi = mx / vol - 1.0 if vol > _EPS else 0.0
                return _finite_contribution(min(r_lo, r_hi))
            return 0.0
        if mn is not None:
            if mn <= _EPS:
                return 0.0
            return _finite_contribution(vol / mn - 1.0)
        if mx is not None:
            if vol <= _EPS:
                return -1.0 if ok else 0.0
            return _finite_contribution(mx / vol - 1.0)
        return 0.0 if ok else -1.0

    if fid == "dp":
        p = _f(cur.get("daily_price_change_pct"))
        mn = _f(thr.get("dp_min_pct"))
        mx = _f(thr.get("dp_max_pct"))
        if p is None:
            return 0.0
        if mn is not None and mx is not None and mx > mn + _EPS:
            if p < mn and mn != 0:
                return _finite_contribution(p / mn - 1.0)
            if p > mx and p != 0:
                return _finite_contribution(mx / p - 1.0)
            if mn <= p <= mx:
                r_lo = p / mn - 1.0 if mn != 0 and abs(mn) > _EPS else 0.0
                r_hi = mx / p - 1.0 if p != 0 else 0.0
                return _finite_contribution(min(r_lo, r_hi))
            return 0.0
        if mn is not None:
            if mn == 0:
                return 0.0
            return _finite_contribution(p / mn - 1.0)
        if mx is not None:
            if abs(p) <= _EPS:
                return 0.0
            return _finite_contribution(mx / p - 1.0)
        return 0.0 if ok else -1.0

    if fid == "pd":
        pct = _f(cur.get("price_change_pct"))
        mn = _f(thr.get("pd_min_change_pct"))
        if pct is None or mn is None:
            return 0.0
        if mn >= 0:
            if mn <= _EPS:
                return 0.0
            return _finite_contribution(pct / mn - 1.0)
        if mn < -_EPS:
            return _finite_contribution(pct / mn - 1.0)
        return 0.0

    if fid == "vl":
        mult = _f(cur.get("multiplier"))
        vmin = _f(thr.get("vl_min_multiplier"))
        if mult is None or vmin is None or vmin <= 0:
            return 0.0
        return _finite_contribution(mult / vmin - 1.0)

    if fid == "oi":
        pct = _f(cur.get("change_pct"))
        usd = _f(cur.get("change_usdt"))
        mnp = _f(thr.get("oi_min_change_pct"))
        mnu = _f(thr.get("oi_min_change_usd"))
        parts: list[float] = []
        if mnp is not None and pct is not None:
            if abs(mnp) <= _EPS:
                pass
            else:
                parts.append(_finite_contribution(pct / mnp - 1.0))
        if mnu is not None and usd is not None:
            if abs(mnu) <= _EPS:
                pass
            else:
                parts.append(_finite_contribution(usd / mnu - 1.0))
        if not parts:
            return 0.0
        return sum(parts) / len(parts)

    if fid == "fr":
        v = _f(cur.get("funding_rate_pct"))
        mn = _f(thr.get("fr_min_value_pct"))
        mx = _f(thr.get("fr_max_value_pct"))
        if v is None:
            return 0.0
        if mn is not None and mx is not None:
            span = mx - mn
            if span <= _EPS:
                return 0.0 if mn <= v <= mx else -1.0
            if v < mn and mn != 0:
                return _finite_contribution(v / mn - 1.0)
            if v > mx and v != 0:
                return _finite_contribution(mx / v - 1.0)
            if mn <= v <= mx:
                r_lo = v / mn - 1.0 if mn != 0 and abs(mn) > _EPS else 0.0
                r_hi = mx / v - 1.0 if v != 0 else 0.0
                return _finite_contribution(min(r_lo, r_hi))
            return 0.0
        if mn is not None:
            if mn == 0:
                return 0.0
            return _finite_contribution(v / mn - 1.0)
        if mx is not None:
            if abs(v) <= _EPS:
                return 0.0
            return _finite_contribution(mx / v - 1.0)
        return 0.0

    if fid == "lq":
        amt = _f(cur.get("amount_usdt"))
        lpct = _f(cur.get("lq_pct_of_daily_volume"))
        m_usd = _f(thr.get("lq_min_amount_usd"))
        m_pct = _f(thr.get("lq_min_amount_pct"))
        parts: list[float] = []
        if m_usd is not None and amt is not None and m_usd > _EPS:
            parts.append(_finite_contribution(amt / m_usd - 1.0))
        if m_pct is not None and lpct is not None and abs(m_pct) > _EPS:
            parts.append(_finite_contribution(lpct / m_pct - 1.0))
        if not parts:
            return 0.0
        return min(parts)

    return 0.0 if ok else -1.0


def enrich_fulfillment_and_score(test_rows: list[dict[str, Any]]) -> float:
    """Добавляет в каждую строку filter_score (signed-вклад); возвращает среднее (Score)."""
    if not test_rows:
        return 0.0
    acc: list[float] = []
    for row in test_rows:
        fs = round(_filter_score_contribution_for_row(row), 4)
        row["filter_score"] = fs
        acc.append(fs)
    return round(sum(acc) / len(acc), 3)


def compute_ok_count_and_tie_score(test_rows: list[dict[str, Any]]) -> tuple[int, float]:
    """Число сработавших фильтров и средний нормализованный запас (для сортировки)."""
    ok_count = sum(1 for r in test_rows if r.get("ok"))
    margins: list[float] = []
    for row in test_rows:
        m = _tie_margin_for_row(row)
        if m is not None:
            margins.append(m)
    if not margins:
        return ok_count, 0.0
    return ok_count, sum(margins) / len(margins)


def _json_safe(x: Any) -> Any:
    if x is None:
        return None
    if isinstance(x, float) and (math.isnan(x) or math.isinf(x)):
        return None
    if isinstance(x, (str, int, bool)):
        return x
    if isinstance(x, float):
        return x
    if isinstance(x, dict):
        return {str(k): _json_safe(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_json_safe(i) for i in x]
    return str(x)


def evaluate_test_mode_snapshot(
    symbol: str,
    ticker: str,
    market_type: MarketType,
    settings: SettingsDTO,
    ticker_daily: TickerDailyItem,
    klines: list[KlineDict],
    open_interest: list[OpenInterestItem],
    funding_rate: float,
    liquidations: list[LiquidationDict],
    blacklist: set[str],
    whitelist: set[str],
    *,
    daily_signal_count: int,
) -> dict[str, Any] | None:
    """Гейты как у продакшена, затем независимые фильтры. Возвращает payload для SSE или None."""
    only_usdt = OnlyUsdtPairsFilter.process(symbol)
    if not only_usdt.ok:
        return None
    if not klines:
        return None
    if not BlacklistFilter.process(ticker, blacklist).ok:
        return None
    if not WhitelistFilter.process(ticker, whitelist).ok:
        return None

    last_price = float(klines[-1]["c"])
    test_rows: list[dict[str, Any]] = []
    any_content_ok = False

    pump_dump_result = None
    volume_multiplier_result = None
    open_interest_result = None
    funding_rate_result = None
    liquidations_result = None

    if settings.dv_status:
        r = DailyVolumeFilter.process(
            ticker_daily=ticker_daily,
            dv_min_usd=settings.dv_min_usd,
            dv_max_usd=settings.dv_max_usd,
        )
        if r.ok:
            any_content_ok = True
        test_rows.append(
            {
                "id": "dv",
                "title": "Суточный объём (DV)",
                "enabled": True,
                "ok": r.ok,
                "current": _json_safe(r.metadata),
                "thresholds": {
                    "dv_min_usd": settings.dv_min_usd,
                    "dv_max_usd": settings.dv_max_usd,
                },
            }
        )

    if settings.dp_status:
        r = DailyPriceFilter.process(
            ticker_daily=ticker_daily,
            dp_min_pct=settings.dp_min_pct,
            dp_max_pct=settings.dp_max_pct,
        )
        if r.ok:
            any_content_ok = True
        test_rows.append(
            {
                "id": "dp",
                "title": "Изменение цены 24ч (DP)",
                "enabled": True,
                "ok": r.ok,
                "current": _json_safe(r.metadata),
                "thresholds": {
                    "dp_min_pct": settings.dp_min_pct,
                    "dp_max_pct": settings.dp_max_pct,
                },
            }
        )

    if settings.pd_status:
        r = PumpDumpFilter.process(
            klines=klines,
            pd_interval_sec=settings.pd_interval_sec,
            pd_min_change_pct=settings.pd_min_change_pct,
        )
        pump_dump_result = r
        if r.ok:
            any_content_ok = True
        test_rows.append(
            {
                "id": "pd",
                "title": "Памп/дамп (PD)",
                "enabled": True,
                "ok": r.ok,
                "current": _json_safe(
                    {
                        "price_change_pct": getattr(r, "price_change_pct", None),
                        "start_price": getattr(r, "start_price", None),
                        "final_price": getattr(r, "final_price", None),
                        **r.metadata,
                    }
                ),
                "thresholds": {
                    "pd_interval_sec": settings.pd_interval_sec,
                    "pd_min_change_pct": settings.pd_min_change_pct,
                },
            }
        )

    if settings.vl_status:
        r = VolumeMultiplierFilter.process(
            klines=klines,
            ticker_daily=ticker_daily,
            vl_interval_sec=settings.vl_interval_sec,
            vl_min_multiplier=settings.vl_min_multiplier,
        )
        volume_multiplier_result = r
        if r.ok:
            any_content_ok = True
        test_rows.append(
            {
                "id": "vl",
                "title": "Множитель объёма (VL)",
                "enabled": True,
                "ok": r.ok,
                "current": _json_safe({**r.metadata, "multiplier": getattr(r, "multiplier", None)}),
                "thresholds": {
                    "vl_interval_sec": settings.vl_interval_sec,
                    "vl_min_multiplier": settings.vl_min_multiplier,
                },
            }
        )

    if market_type == MarketType.FUTURES:
        if settings.oi_status:
            r = OpenInterestFilter.process(
                open_interest=open_interest,
                oi_interval_sec=settings.oi_interval_sec,
                oi_min_change_pct=settings.oi_min_change_pct,
                oi_min_change_usd=settings.oi_min_change_usd,
                last_price=last_price,
            )
            open_interest_result = r
            if r.ok:
                any_content_ok = True
            test_rows.append(
                {
                    "id": "oi",
                    "title": "Открытый интерес (OI)",
                    "enabled": True,
                    "ok": r.ok,
                    "current": _json_safe(
                        {
                            "change_pct": getattr(r, "change_pct", None),
                            "change_usdt": getattr(r, "change_usdt", None),
                            **r.metadata,
                        }
                    ),
                    "thresholds": {
                        "oi_interval_sec": settings.oi_interval_sec,
                        "oi_min_change_pct": settings.oi_min_change_pct,
                        "oi_min_change_usd": settings.oi_min_change_usd,
                    },
                }
            )

        if settings.fr_status:
            r = FundingRateFilter.process(
                funding_rate=funding_rate,
                fr_min_value_pct=settings.fr_min_value_pct,
                fr_max_value_pct=settings.fr_max_value_pct,
            )
            funding_rate_result = r
            if r.ok:
                any_content_ok = True
            test_rows.append(
                {
                    "id": "fr",
                    "title": "Фандинг (FR)",
                    "enabled": True,
                    "ok": r.ok,
                    "current": _json_safe(r.metadata),
                    "thresholds": {
                        "fr_min_value_pct": settings.fr_min_value_pct,
                        "fr_max_value_pct": settings.fr_max_value_pct,
                    },
                }
            )

        if settings.lq_status:
            r = LiquidationsSumFilter.process(
                liquidations=liquidations,
                lq_interval_sec=settings.lq_interval_sec,
                lq_min_amount_usd=settings.lq_min_amount_usd,
                lq_min_amount_pct=settings.lq_min_amount_pct,
                daily_volume_usd=float(ticker_daily["q"]),
            )
            liquidations_result = r
            if r.ok:
                any_content_ok = True
            test_rows.append(
                {
                    "id": "lq",
                    "title": "Ликвидации (LQ)",
                    "enabled": True,
                    "ok": r.ok,
                    "current": _json_safe(
                        {**r.metadata, "amount_usdt": getattr(r, "amount_usdt", None)}
                    ),
                    "thresholds": {
                        "lq_interval_sec": settings.lq_interval_sec,
                        "lq_min_amount_usd": settings.lq_min_amount_usd,
                        "lq_min_amount_pct": settings.lq_min_amount_pct,
                    },
                }
            )

    if not any_content_ok:
        return None

    screening = ScreeningResult(
        symbol=symbol,
        ticker=ticker,
        last_price=last_price,
        funding_rate=funding_rate,
        daily_volume=float(ticker_daily["q"]),
        daily_price=float(ticker_daily["p"]),
        pd_start_price=pump_dump_result.start_price if pump_dump_result else None,
        pd_final_price=pump_dump_result.final_price if pump_dump_result else None,
        pd_price_change_pct=pump_dump_result.price_change_pct if pump_dump_result else None,
        pd_price_change_usdt=pump_dump_result.price_change_usdt if pump_dump_result else None,
        oi_start_value=open_interest_result.start_value if open_interest_result else None,
        oi_final_value=open_interest_result.final_value if open_interest_result else None,
        oi_change_pct=open_interest_result.change_pct if open_interest_result else None,
        oi_change_coins=open_interest_result.change_coins if open_interest_result else None,
        oi_change_usdt=open_interest_result.change_usdt if open_interest_result else None,
        lq_amount_usdt=liquidations_result.amount_usdt if liquidations_result else None,
        vl_multiplier=volume_multiplier_result.multiplier if volume_multiplier_result else None,
    )

    telegram_text = generate_text(
        symbol=symbol,
        exchange=settings.exchange,
        market_type=market_type,
        settings=settings,
        result=screening,
        daily_signal_count=daily_signal_count,
    )

    cmc = get_cmc_rank_for_symbol(symbol)
    score = enrich_fulfillment_and_score(test_rows)
    ok_count, tie_break_score = compute_ok_count_and_tie_score(test_rows)
    return {
        "id": f"test-{settings.id}-{symbol}",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "screener_name": settings.name,
        "screener_id": settings.id,
        "exchange": str(settings.exchange.value),
        "market_type": str(settings.market_type.value),
        "symbol": symbol,
        "telegram_text": telegram_text,
        "telegram_ok": True,
        "error": None,
        "cmc_rank": cmc,
        "mode": "test",
        "test_filters": test_rows,
        "ok_count": ok_count,
        "tie_break_score": tie_break_score,
        "score": score,
    }
