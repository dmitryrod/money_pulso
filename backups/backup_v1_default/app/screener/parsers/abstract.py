__all__ = ["Parser"]

import asyncio
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from unicex import Exchange, IUniClient, MarketType, get_uni_client


class Parser(ABC):
    """Базовый класс для парсеров данных."""

    _MAX_HISTORY_LEN = 60 * 15
    """Максимальная длина истории в секундах для всех парсеров."""

    def __init__(self, exchange: Exchange, market_type: MarketType) -> None:
        """Инициализирует парсера данных.

        Args:
            exchange (Exchange): На какой бирже парсить данные.
            market_type (MarketType): Тип рынка с которого парсить данные.
        """
        self._exchange = exchange
        self._market_type = market_type
        self._is_running = True

    @abstractmethod
    async def start(self) -> None:
        """Запускает парсер данных."""
        pass

    @abstractmethod









    async def _safe_sleep(self, seconds: int) -> None:
        """Безопасное ожидание, которое может прерваться в процессе."""
        for _ in range(seconds):
            if not self._is_running:
                return
            await asyncio.sleep(1)

    @asynccontextmanager
    async def _client_context(self, **kwargs: Any) -> AsyncIterator[IUniClient]:
        """Создаёт клиента unicex и гарантированно закрывает соединение по завершении контекста.
        Args:
        **kwargs (Any): Любые параметры, которые нужно передать в UniClient.create (например, logger).
        Yields:
        AsyncIterator[Any]: Инициализированный и готовый к работе клиент.
        """
        client = await get_uni_client(self._exchange).create(**kwargs)
        async with client:
            yield client