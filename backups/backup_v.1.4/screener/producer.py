import asyncio
from collections import defaultdict
from itertools import batched
from typing import TYPE_CHECKING

import aiohttp
from pycryptoapi.abstract import AbstractWebsocket
from pycryptoapi.enums import Exchange, MarketType
from pycryptoapi.fixes import (
    init_fixes,
    kcex_perpetual_aggtrade_fix,
    mexc_perpetual_aggtrade_fix,
    okx_perpetual_aggtrade_fix,
    xt_perpetual_aggtrade_fix,
)
from pycryptoapi.mappers import ADAPTERS_MAPPER, CLIENTS_MAPPER, SOCKETS_MAPPER
from pycryptoapi.types import AggTradeDict, KlineDict, TickerDailyDict

from app.core import get_logger

if TYPE_CHECKING:
    from loguru import Logger


class Producer:
    """Класс для сбора свечей / сделок с биржи."""

    MAX_HISTORY_LEN = 60 * 15
    """Максимальная длина истории в секундах"""

    TICKER_DAILY_UPDATE_INTERVAL = 5
    """Интервал обновления суточной статистики тикеров в секундах"""

    WS_CHUNK_SIZE = {
        Exchange.BINGX: 30,
        Exchange.BITUNIX: 60,
    }
    """Количество тикеров в одном вебсокет соединении.
    Если биржи нет - используется DEFAULT_WS_CHUNK_SIZE"""

    DEFAULT_WS_CHUNK_SIZE = 20
    """Стандартное количество тикеров в одном вебсокет соединении"""

    TIMEFRAME = 1
    """Таймфрейм для аггрегации свечей из сделок в секундах"""

    def __init__(self, exchange: Exchange, market_type: MarketType) -> None:
    """Инициализация класса Producer.

    Args:
        exchange (Exchange): Биржа, с которой будет производиться сбор данных.
        market_type (MarketType): Тип рынка (SPOT, FUTURES).
    
    """
    self._exchange = exchange