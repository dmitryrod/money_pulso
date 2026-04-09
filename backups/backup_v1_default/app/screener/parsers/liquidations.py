__all__ = ["LiquidationsParser"]

import asyncio
import time
from collections import defaultdict

from unicex import (
    BybitWebsocketManager,
    Exchange,
    IUniClient,
    LiquidationDict,
    MarketType,
    Websocket,
)

#from app.config import get_logger
from config import get_logger

from .abstract import Parser


class LiquidationsParser(Parser):
    """Парсер ликвидаций."""

    _WS_CHUNK_SIZE: int = 20
    """Количество подключений в одном вебсокет соединении."""

    def __init__(self, **_) -> None:
        """Инициализирует парсер ликвидаций.

        Args:
            _ (dict): Дополнительные аргументы, для отказоустойчивости.
        """
        super().__init__(Exchange.BYBIT, MarketType.FUTURES)

        self._logger = get_logger("lq")
        self._liquidation_websockets: list[Websocket] = []
        self._liquidations_lock = asyncio.Lock()
        self._liquidations: dict[str, list[LiquidationDict]] = defaultdict(list)    

    async def start(self) -> None:
        """Запускает парсер данных."""
        self._logger. info("Parser started")
        try:
            async with self._client_context() as client:
                futures_tickers_batched = await self._fetch_batched_futures_tickers_list(client)
                self._websockets = self._create_websockets(futures_tickers_batched)
                tasks = await self._start_websockets()
                gather_results = await asyncio.gather(*tasks)
        except Exception as e:
            self._logger.exception(f"Error fetching data: {e}")

    async def _fetch_batched_futures_tickers_list(self, client:IUniClient) -> list[list[str]]:
        """Fetches a batched list of futures tickers."""
        return await client.futures_tickers_batched(batch_size=self._WS_CHUNK_SIZE)

    async def _create_websockets(self, futures_tickers_batched: list[list[str]]) -> list[Websocket]:
        """Генерирует вебсокеты исходя из списка тикеров разбитых на чанки."""
        return [
            BybitWebsocketManager(
                logger=self._logger,
            ).liquidations(
                callback=self._liquidation_message_callback,
                symbols=batch,
            )
            for batch in futures_tickers_batched
        ]

    async def _start_websockets(self) -> list[asyncio.Task]:
        """Запускает вебсокеты."""
        tasks = []
        for websocket in self._websockets:
            if not websocket.running:
                tasks.append(websocket.start())
                self._logger.debug(f"{websocket} started")
                await asyncio.sleep(0.5)
        return tasks

    async def _liquidations_message_callback(self, liquidation: LiquidationDict) -> None:
        """Обрабатывает сообщение о ликвидации."""
        async with self._liquidations_lock:
            ticker = liquidation["s"].removesuffix("USDT")
            self._liquidations[ticker].append(liquidation)
            threshold: float = (time.time() - self._MAX_HISTORY_LEN) * 1000
            self._liquidations[ticker] = [
                item for item in self._liquidations[ticker] if item["t"] > threshold
            ]

    async def stop(self) -> None:
        """Останавливает парсер данных."""
        self._logger.info ("Parser stopped")
        gather_results = await asyncio.gather(
            *[ws.stop() for ws in self._liquidation_websockets], return_exceptions=True
        )
        for result in gather_results:
            if isinstance(result, Exception):
                self._logger.error(f"Error while stopping websocket: {result}")
        self._is_running = False

    async def fetch_collected_data(self) -> dict[str, list[LiquidationDict]]:
        """Возвращает накопленные данные. Возвращает ссылку на объект в котором хранятся данные."""
        async with self._liquidations_lock:
            return self._liquidations