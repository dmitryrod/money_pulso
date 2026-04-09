__all__ = ["Consumer"]

import asyncio
import functools
import time

from unicex import (
    Exchange,
    KlineDict,
    LiquidationDict,
    MarketType,
    OpenInterestItem,
    TickerDailyItem,
)
from unicex.extra import TimeoutTracker, normalize_ticker

from app.config import get_logger
from app.models import SettingsDTO, SignalDTO
from app.utils import (
    SignalCounter,
    TelegramBot,
    format_filter_failure,
    generate_text,
)

from .filters import(
    daily_price_filter,
    daily_volume_filter,
    funding_rate_filter,
    liquidations_sum_filter,
    open_interest_filter,
    volume_multiplier_filter,
)
from .parsers import ParsersDTO

USE_CILTERS = True #  Use filters on C-lang

if USE_CILTERS:
    from .cilters import pump_dump_filter # type: ignore
else:
    from .filters import pump_dump_filter


class Consumer:
    """Прослушивает данные с парсеров и с определенной переодичностью
    проверяет данные на совпадение условий, чтобы отправить сигнал в телеграм."""

    _CHECK_INTERVAL_SEC: int = 1
    """Интервал проверки условий в секундах."""

    def __init__(self, parsers: ParsersDTO, settings: SettingsDTO) -> None:
        """Инициализирует экземпляр класса.

        Params:
            parsers: ParsersDTO - Объект с работающими парсерами.
            settings: SettingsDTO - Объект с настройками скринера.
        """
        self._parsers = parsers
        self._settings = settings

        self._logger = get_logger("settings_" + str(settings.id))
        self._timeout_tracker = TimeoutTracker[str]()
        self._signal_counter = SignalCounter[str]()
        self._telegram_bot = TelegramBot() # must be called from async ctx
        self._is_running = True

    def update_settings(self, settings: SettingsDTO) -> None:
        """Обновляет настройки."""
        if settings.id != self._settings.id:
            raise ValueError("Settings ID mismatch")
        self._settings = settings

    @property
    def exchange(self) -> Exchange:
        """Возвращает биржу для поиска сигналов"""
        return self._settings.exchange

    @property
    def market_type(self) -> MarketType:
        """Возвращает тип рынка для поиска сигналов."""
        return self._settings.market_type
    
    @property
    def settings(self) -> SettingsDTO:
        """Возвращает настройки."""
        return self._settings
    
    @property
    def is_running(self) -> bool:
        """Возвращает статус запущенного процесса."""
        return self._is_running

    async def start(self) -> None:
        """Запускает процесс прослушивания данных и проверки условий."""
        while self._is_running:
            try:
                start_time = time.time()
                alert_tasks = await self._check_filters()
                elapsed_time = time.time() - start_time
                self._logger.debug(f"Checked filters in {elapsed_time:.4f} seconds")
                if elapsed_time > self._CHECK_INTERVAL_SEC / 2:
                    self._logger.critical(
                        f"Process took longer than expected: {elapsed_time:.4f} seconds"
                    )

                if alert_tasks:
                    start_time = time.time()
                    results = await asyncio.gather(*alert_tasks, return_exceptions=True)
                    for result in results:
                        if isinstance(result, Exception):
                            self._logger.error(f"Error sending message: ({type(result)}) {result}")
                    elapsed_time = time.time() - start_time
                    self._logger.info(f"Sent {len(results)} messages in {elapsed_time:.4f} seconds")
            except Exception as e:
                self._logger.exception(e)
            await asyncio.sleep(self._CHECK_INTERVAL_SEC)

    async def stop(self) -> None:
        """Останавливает процесс прослушивания данных и проверки условий."""
        self._is_running = False
        await self._telegram_bot.close()

    async def _check_filters(self) -> list[asyncio.Task]:
        """Проверяет данные по всем фильтрам и отправляет сигнал при успехе."""
        if not self.settings.any_filters_status:
            return []

        klines = await self._parsers.agg_trades.fetch_collected_data()
        ticker_daily = await self._parsers.ticker_daily.fetch_collected_data()
        blacklist = self.settings.parse_blacklist()
        whitelist = self.settings.parse_whitelist()
        if self.market_type == MarketType.FUTURES:
            open_interest = await self._parsers.open_interest.fetch_collected_data() # type: ignore
            funding_rate = await self._parsers.funding_rate.fetch_collected_data() # type: ignore
            liquidations = await self._parsers.liquidations.fetch_collected_data() # type: ignore
        else:
            open_interest = {}
            funding_rate = {}
            liquidations = {}

        tasks = []
        loop = asyncio.get_running_loop()
        for symbol in ticker_daily:
            if self._timeout_tracker.is_blocked(symbol):
                self._logger.trace(f"[x] {symbol} is not valid. Reason: timeout")
                continue
            if self.settings.max_day_alerts and not self._signal_counter.is_within_limit(
                symbol, self.settings.max_day_alerts
            ):
                self._logger.trace(f"[x] {symbol} is not valid. Reason: max day alerts limit")
                continue
            ticker = normalize_ticker(symbol)
            tasks.append(
                loop.run_in_executor(
                    self._executor,
                    functools.partial(
                        self._check_filters_for_symbol,
                        symbol,
                        ticker,
                        self.market_type,
                        self.settings,
                        ticker_daily[symbol],
                        klines.get(symbol, []),
                        open_interest.get(symbol, []),
                        funding_rate.get(symbol, 0.0),
                        liquidations.get(ticker, []),
                        blacklist,
                        whitelist,
                    ),
                )
            )

        alert_tasks = []
        for task in asyncio.as_completed(tasks):
            try:
                signal = await task
            except Exception as e:
                self._logger.error(f"Error processing filters: ({type(e)}) {e}")
                continue
            if isinstance(signal, SignalDTO):
                try:
                    self._timeout_tracker.block(signal.symbol, self.settings.timeout_sec)
                    daily_signal_count = self._signal_counter.add(signal.symbol)
                    alert_task = asyncio.create_task(
                        self._telegram_bot.send_message(
                            bot_token=self.settings.bot_token,
                            chat_id=self.settings.chat_id,
                            text=generate_text(
                                settings=self.settings,
                                signal=signal,
                                daily_signal_count=daily_signal_count,
                            ),
                        )
                    )
                    alert_tasks.append(alert_task)
                    self._logger.success(f"Processsed filters for {signal.symbol}")
                except Exception as e:
                    self._logger.error(f"Error sending filters: ({type(e)}) {e}")
            else:
                if "whitelisted" not in signal and "not USDT pair" not in signal:
                    self._logger.info(signal)
                pass
        return alert_tasks

    @staticmethod
    def _check_filters_for_symbol(
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
    ) -> str | SignalDTO:
        """Проверяет фильтры для конкретного тикера."""
        only_usdt_pair_result = OnlyUsdtPairsFilter.process(symbol)
        if not only_usdt_pair_result.ok:
            return f"[x] {symbol}. Reason: not USDT pair. Details: {only_usdt_pair_result}"

        blacklist_result = BlacklistFilter.process(ticker, blacklist)
        if not blacklist_result.ok:
            return f"[x] {symbol}. Reason: blacklisted. Details: {blacklist_result}"

        whitelist_result = WhitelistFilter.process(ticker, whitelist)
        if not whitelist_result.ok:
            return f"[x] {symbol}. Reason: not whitelisted. Details: {whitelist_result}"
        
        if settings.dv_status:
            daily_volume_result = DailyVolumeFilter.process(
                ticker_daily=ticker_daily,
                dv_min_usd=settings.dv_min_usd,
                dv_max_usd=settings.dv_max_usd,
            )
            if not daily_volume_result.ok:
                return f"[x] {symbol}. Reason: daily volume filter. Details: {daily_volume_result}"

        if settings.dp_status:
            daily_price_result = DailyPriceFilter.process(
                ticker_daily=ticker_daily,
                dp_min_pct=settings.dp_min_pct,
                dp_max_pct=settings.dp_max_pct,
            )
            if not daily_price_result.ok:
                return f"[x] {symbol}. Reason: daily price filter. Details: {daily_price_result}"

        if settings.pd_status:
            pump_dump_result = PumpDumpFilter.process(
                klines = klines,
                pd_interval_sec = settings.pd_interval_sec,
                pd_min_change_pct = settings.pd_min_change_pct,
            )
            if not pump_dump_result.ok:
                return f"[x] {symbol}. Reason: daily pump dump filter. Details: {pump_dump_result}"
        else:
            pump_dump_result = None
        
        if settings.vl_status:
            volume_multiplier_result = VolumeMultiplierFilter.process(
                klines=klines,
                ticker_daily=ticker_daily,
                vl_interval_sec=settings.vl_interval_sec, # type: ignore
                vl_min_multiplier=settings.vl_min_multiplier, # type: ignore
            )
            if not volume_multiplier_result.ok:
                return f"[x] {symbol}. Reason: volume multiplier filter. Details: {volume_multiplier_result}"
        else:
            volume_multiplier_result = None

        last_price = klines[-1]["c"]

        if market_type == MarketType.FUTURES:
            if settings.oi_status:
                open_interest_result = OpenInterestFilter.process(
                    open_interest=open_interest,
                    oi_interval_sec=settings.oi_interval_sec,
                    oi_min_change_pct=settings.oi_min_change_pct,
                    oi_min_change_usd=settings.oi_min_change_usd,
                    last_price=last_price,
                )
                if not open_interest_result.ok:
                    return f"[x] {symbol}. Reason: open interest filter. Details: {open_interest_result}"
            else:
                open_interest_result = None

            if settings.fr_status:
                funding_rate_result = FundingRateFilter.process(
                    funding_rate=funding_rate,
                    fr_min_value_pct=settings.fr_min_value_pct,
                    fr_max_value_pct=settings.fr_max_value_pct,
                )
                if not funding_rate_result.ok:
                    return (
                        f"[x] {symbol}. Reason: funding rate filter. Details: {funding_rate_result}"
                    )
            else: 
                funding_rate_result = None

            if settings.lq_status:
                liquidations_result = LiquidationsSumFilter.process(
                    liquidations=liquidations,
                    lq_interval_sec=settings.lq_interval_sec,
                    lq_min_amount_usd=settings.lq_min_amount_usd,
                )
                if not liquidations_result.ok:
                    return f"[x] {symbol}. Reason: liquidations sum filter. Details: {liquidations_result}"
            else:
                liquidations_result = None
        else:
            open_interest_result = None
            funding_rate_result = None
            liquidations_result = None
        
        return SignalDTO(
            timestamp=int(time.time()),
            datetime=time.ctime,
            symbol=symbol,
            ticker=ticker,
            last_price=last_price,
            funding_rate=funding_rate,
            daily_volume=ticker_daily["q"],
            daile_price=ticker_daily["p"],
            pd_start_price=pump_dump_result.start_price if pump_dump_result else None,
            pd_final_price=pump_dump_result.final_price if pump_dump_result else None,
            pd_price_change_pct=pump_dump_result.price_change_pct if pump_dump_result else None,
            pd_price_change_usdt=pump_dump_result.price_change_usdt  if pump_dump_result else None,
            oi_start_value=open_interest_result.start_value if open_interest_result else None,
            oi_final_value=open_interest_result.final_value if open_interest_result else None,
            oi_change_pct=open_interest_result.change_pct if open_interest_result else None,
            oi_change_coins=open_interest_result.change_coins if open_interest_result else None,
            oi_change_usdt=open_interest_result.change_usdt if open_interest_result else None,
            lq_amount_usdt=liquidations_result.amount_usdt if liquidations_result else None,
            vl_multiplier=volume_multiplier_result.multiplier if volume_multiplier_result else None,
        )