__all__ = ["Operator"]

import asyncio
from collections.abc import Awaitable

from unicex import Exchange, MarketType

from app.config import get_logger
from app.database import Database
from app.schemas import SettingsDTO

from .consumer import Consumer
from .parsers import (
    AggTradesParser,
    FundingRateParser,
    LiquidationsParser,
    OpenInterestParser,
    ParsersDTO,
    TickerDailyParser,
)


class Operator:
    """Управляет созданием и запуском парсеров и консьюмеров."""

    _UPDATE_INTERVAL_SEC: int = 3
    """Интервал обновления настроек в секундах."""

    def __init__(self) -> None:
        """Инициализирует оператора."""
        self._logger = get_logger("operator")
        self._is_running = False

        self._parsers: dict[tuple[Exchange, MarketType], ParsersDTO] = {}
        """Настроенные для каждой пары биржа+рынок парсеры."""

        self._parser_tasks: dict[tuple[Exchange, MarketType], list[asyncio.Task]] = {}
        """Запущенные задачи парсеров для каждой пары биржа+рынок."""

        self._consumers: dict[tuple[int, Exchange, MarketType], Consumer] = []
        """Активные консьюмеры по ключу (settings.id, exchange, market_type)."""

        self._consumer_tasks: dict[tuple[int, Exchange, MarketType], asyncio.Task] = {}
        """Задачи для фонового запуска консьюмеров."""

    async def start(self) -> None:
        """Запускает цикл обновления настроек и управление процессами."""
        if self._is_running:
            raise RuntimeError("Operator is already running")

        self._is_running = True
        self._logger.info ("Operator started")

        while self._is_running:
            try:
                settings_list = await self._fetch_settings()
            except Exception as exc:
                self._logger.exception(f"Error fetching settings: {exc}")
                await asyncio.sleep(self._UPDATE_INTERVAL_SEC)
                continue

            try:
                await self._update_parsers(settings_list)
            except Exception as exc:
                self._logger.exception(f"Error updating parsers: {exc}")

            try:
                await self._update_consumers(settings_list)
            except Exception as exc:
                self._logger.exception(f"Error updating consumers: {exc}")

            await asyncio.sleep(self._UPDATE_INTERVAL_SEC)

    async def stop(self) -> None:
        """Останавливает оператора и все запущенные процессы."""
        self._is_running = False

        #Останавливаем консьюмеров раньше парсеров, чтобы они не читали пустые данные
        await self._stop_consumers(list(self._consumers.keys()))
        await self._stop_parsers(list(self._parsers.keys()))

        self._logger.info ("Operator stopped")

    async def _fetch_settings(self) -> list[SettingsDTO]:
        """Получает актуальные настройки скринера из базы данных.
        
        Returns:
            list[SettingsDTO]: Список включенных настроек.
        """
        async with Database.session_context() as db:
            settings_list = await db.settings_repo.get_all()

        # Оставляем только включенные настройки и переводим их в DTO
        return [
            SettingsDTO.model_validate(settings) for settings in settings_list if settings.enabled
        ]

    async def _update_parsers(self, settings_list: list[SettingsDTO]) -> None:
        """Создает и останавливает парсеры под актуальные настройки."""
        required_pairs = {(settings.exchange, settings.market_type) for settings in settings_list}

        # Запускаем парсеры для новых пар биржа+рынок
        for exchange, market_type in required_pairs:
            key = (exchange, market_type)
            if key in self._parsers:
                continue

            agg_trades = AggTradesParser(exchange=exchange, market_type=market_type)
            ticker_daily = TickerDailyParser(exchange=exchange, market_type=market_type)
            if market_type == MarketType.FUTURES:
                funding_rate = FundingRateParser(exchange=exchange, market_type=market_type)
                liquidations = LiquidationsParser(exchange=exchange, market_type=market_type)
                open_interest = OpenInterestParser(exchange=exchange, market_type=market_type)
            else:
                funding_rate = None
                liquidations = None
                open_interest = None
            parsers = ParsersDTO(
                agg_trades=agg_trades,
                ticker_daily=ticker_daily,
                funding_rate=funding_rate,
                liquidations=liquidations,
                open_interest=open_interest,
            )
            self._parsers[key] = parsers
            self._parser_tasks[key] = [
                asyncio.create_task(parsers.agg_trades.start()),
                asyncio.create_task(parsers.ticker_daily.start()),
            ]
            if parsers.funding_rate:
                self._parser_tasks[key].append(asyncio.create_task(parsers.funding_rate.start()))
            if parsers.liquidations:
                self._parser_tasks[key].append(asyncio.create_task(parsers.liquidations.start()))
            if parsers.open_interest:
                self._parser_tasks[key].append(asyncio.create_task(parsers.open_interest.start()))
            self._logger.info (f"Parsers started for {exchange}:{market_type}")

        # Останавливаем парсеры, которые больше не нужны
        pairs_to_stop = set(self._parsers.keys()) - required_pairs
        if pairs_to_stop:
            await self._stop_parsers(list(pairs_to_stop))

    async def _update_consumers(self, settings_list: list[SettingsDTO]) -> None:
        """Создает, обновляет и останавливает консьюмеров под актуальные настройки."""
        # Создаем или обновляем консьюмеров
        for settings in settings_list:
            key = (settings.id, settings.exchange, settings.market_type)
            existing_consumer = self._consumers.get(key)

            if existing_consumer:
                existing_consumer.update_settings(settings)
                continue

            parsers = self._parsers.get((settings.exchange, settings.market_type))
            if not parsers:
                self._logger.warning(
                    f"Parsers is not ready {settings.exchange}:{settings.market_type}"
                )
                continue

            consumer = Consumer(parsers=parsers, settings=settings)
            self._consumers[key] = consumer
            self._consumer_tasks[key] = asyncio.create_task(consumer.start())

            self._logger.info (
                f"consumer started for settings_id={settings.id} "
                f"{settings.exchange}: {settings.market_type})"
            )

        # Останавливаем консьюмеров, которые больше не нужны
        desired_keys = {
            (settings.id, settings.exchange, settings.market_type) for settings in settings_list
        }
        keys_to_stop = set(self._consumers.keys()) - desired_keys
        if keys_to_stop:
            await self._stop_consumers(list(keys_to_stop))

    async def _stop_parsers(self, keys: list[tuple[Exchange, MarketType]]) -> None:
        """Останавливает парсеры и связанные с ними задачи."""
        stop_tasks: list[Awaitable[None]] = []
        tasks_to_cancel: list[asyncio.Task] = []

        for key in keys:
            parsers = self._parsers.pop(key, None)
            if parsers:
                stop_tasks.extend(
                    [
                        parsers.agg_trades.stop(),
                        parsers.funding_rate.stop() if parsers.funding_rate else asyncio.sleep(0),
                        parsers.liquidations.stop() if parsers.liquidations else asyncio.sleep(0),
                        parsers.open_interest.stop() if parsers.open_interest else asyncio.sleep(0),
                        parsers.ticker_daily.stop(),
                    ]
                )

            for task in self._parser_tasks.pop(key, []):
                if not task.done():
                    task.cancel()
                    tasks_to_cancel.append(task)

            self._logger.info (f"Parser stopped for {key[0]}:{key[1]}")

        if stop_tasks:
            await asyncio.gather(*stop_tasks, return_exceptions=True)

        if tasks_to_cancel:
            await asyncio.gather(*tasks_to_cancel, return_exceptions=True)

    async def _stop_consumers(self, keys: list[tuple[int, Exchange, MarketType]]) -> None:
        """Останавливает консьюмеров и связанные с ними задачи."""
        stop_tasks: list[Awaitable[None]] = []
        tasks_to_cancel: list[asyncio.Task] = []

        for key in keys:
            consumer = self._consumers.pop(key, None)
            if consumer:
                stop_tasks.append(consumer.stop())

            task = self._consumer_tasks.pop(key, None)
            if task and not task.done():
                task.cancel()
                tasks_to_cancel.append(task)

            self._logger.info (f"Consumer stopped for settings_id={key[0]}")

        if stop_tasks:
            await asyncio.gather(*stop_tasks, return_exceptions=True)

        if tasks_to_cancel:
            await asyncio.gather(+tasks_to_cancel, return_exceptions=True)