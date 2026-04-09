import os
import threading
import time
from typing import Dict, Optional

import logging

import requests

logger = logging.getLogger(__name__)

_CMC_RANKS: Dict[str, int] = {}
_CMC_LOCK = threading.RLock()
_CMC_THREAD_STARTED = False
_CMC_INITIAL_FETCH_DONE = False


def _get_env_api_key() -> Optional[str]:
    return os.getenv("X-CMC_PRO_API_KEY") or os.getenv("CMC_PRO_API_KEY")


def _get_update_interval_seconds() -> int:
    raw = os.getenv("X-CMC_UPDATE_TIME") or os.getenv("CMC_UPDATE_TIME") or "60"
    try:
        minutes = int(str(raw).strip().split()[0])
    except (TypeError, ValueError):
        minutes = 60
    # минимальный интервал на всякий случай
    if minutes <= 0:
        minutes = 60
    return minutes * 60


def _fetch_and_update_cmc_ranks() -> None:
    api_key = _get_env_api_key()
    if not api_key:
        logger.warning("CoinMarketCap API key is not set; skipping CMC rank update")
        return

    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest"
    params = {
        "start": 1,
        "limit": 5000,
        "convert": "USD",
    }
    headers = {
        "X-CMC_PRO_API_KEY": api_key,
        "Accept": "application/json",
    }

    try:
        resp = requests.get(url, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
        payload = resp.json()
    except Exception as exc:
        logger.error("Failed to fetch CoinMarketCap listings: %s", exc)
        return

    data = payload.get("data") or []
    if not isinstance(data, list):
        logger.error("Unexpected CoinMarketCap payload format: %r", type(data))
        return

    new_ranks: Dict[str, int] = {}
    for item in data:
        try:
            symbol = str(item.get("symbol") or "").upper()
            rank = item.get("cmc_rank")
            if not symbol or not isinstance(rank, int):
                continue
            new_ranks[symbol] = rank
        except Exception:
            continue

    if not new_ranks:
        logger.warning("CoinMarketCap returned empty ranks list")
        return

    with _CMC_LOCK:
        _CMC_RANKS.clear()
        _CMC_RANKS.update(new_ranks)

    global _CMC_INITIAL_FETCH_DONE
    _CMC_INITIAL_FETCH_DONE = True

    logger.info("CoinMarketCap ranks updated, %d entries", len(new_ranks))


def _updater_loop() -> None:
    interval = _get_update_interval_seconds()
    while True:
        try:
            _fetch_and_update_cmc_ranks()
        except Exception as exc:  # защита от падения потока
            logger.exception("Unhandled error in CMC updater loop: %s", exc)
        time.sleep(interval)


def _ensure_thread_started() -> None:
    global _CMC_THREAD_STARTED
    if _CMC_THREAD_STARTED:
        return
    _CMC_THREAD_STARTED = True
    t = threading.Thread(target=_updater_loop, name="cmc-rank-updater", daemon=True)
    t.start()


def init_cmc_rank_cache() -> None:
    """
    Инициализировать кеш: блокирующий первый запрос + запуск фонового обновления.
    Вызывать как можно раньше при старте приложения.
    """
    # первый запрос делаем синхронно, чтобы как можно раньше получить рейтинг
    _fetch_and_update_cmc_ranks()
    _ensure_thread_started()


def _extract_base_symbol(symbol: str) -> str:
    """
    Грубый, но практичный разбор тикера в базовый символ для CMC.
    BTCUSDT, BTC/USDT, BTC-USDT, BTCUSDT.P, BTCUSDT_PERP → BTC
    """
    s = symbol.upper().strip()
    # удаляем разделители
    for sep in ("/", "-", "_"):
        s = s.replace(sep, "")
    # убираем распространённые фьючерсные суффиксы
    for suf in ("PERP", "F0", "FUT", "P"):
        if s.endswith(suf) and len(s) > len(suf) + 1:
            s = s[: -len(suf)]
    # частые котируемые валюты
    suffixes = (
        "USDT",
        "USD",
        "USDC",
        "FDUSD",
        "BUSD",
        "EUR",
        "BTC",
        "ETH",
    )
    for suf in suffixes:
        if s.endswith(suf) and len(s) > len(suf):
            return s[: -len(suf)]
    return s


def get_cmc_rank_for_symbol(symbol: str) -> Optional[int]:
    """
    Быстрый доступ к кешу рангов.
    Возвращает None, если данных нет (ошибка запроса, ещё не успели обновиться и т.п.).
    """
    base = _extract_base_symbol(symbol)
    with _CMC_LOCK:
        rank = _CMC_RANKS.get(base)
    return rank


# Попробуем инициализироваться как можно раньше при импортировании модуля.
try:
    init_cmc_rank_cache()
except Exception as exc:  # не даём упасть при импорте
    logger.error("Failed to initialize CoinMarketCap rank cache: %s", exc)

