__all__ = ["Consumer"]

import asyncio
import functools
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any
from uuid import uuid4

from unicex import (
    Exchange,
    KlineDict,
    LiquidationDict,
    MarketType,
    OpenInterestItem,
    TickerDailyItem,
    get_uni_client,
)
from unicex.extra import TimeoutTracker, normalize_ticker

from app.config import get_logger, log_debug_event_async
from app.models import SettingsDTO, SignalDTO, ScreeningResult
from app.utils import (
    SignalCounter,
    TelegramBot,
    format_filter_failure,
    generate_text,
)

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
from .parsers import ParsersDTO


class Consumer:
    """Прослушивает данные с парсеров и с определенной переодичностью
    проверяет данные на совпадение условий, чтобы отправить сигнал в телеграм."""

    _CHECK_INTERVAL_SEC: int = 1
    """Интервал проверки условий в секундах."""

    _FUNDING_RATE_CACHE_TTL_SEC: int = 55
    """TTL кэша фандинга по символу (сек). Снижает число запросов к API биржи."""

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
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="filters")
        self._run_id = uuid4().hex
        self._cycle_id = 0
        self._last_signal_ts: float = 0.0
        self._last_agg_empty_warn_ts: float = 0.0
        # Кэш фандинга: symbol -> (rate, expires_at)
        self._funding_rate_cache: dict[str, tuple[float, float]] = {}

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

    def _schedule_debug_log(self, **kwargs: Any) -> None:
        """Пишет debug.log в фоне: не блокирует цикл и отправку в Telegram при сбое json/очереди."""

        async def _runner() -> None:
            try:
                await log_debug_event_async(**kwargs)
            except Exception as exc:
                self._logger.warning(
                    "debug.json log failed ({}): {}",
                    type(exc).__name__,
                    exc,
                )

        asyncio.create_task(_runner())

    async def start(self) -> None:
        """Запускает процесс прослушивания данных и проверки условий."""
        while self._is_running:
            try:
                self._cycle_id += 1
                start_time = time.time()
                alert_tasks, cycle_meta = await self._check_filters()
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

                if self.settings.debug:
                    self._schedule_debug_log(
                        level="info",
                        screener_name=self.settings.name,
                        screener_id=self.settings.id,
                        exchange=str(self.settings.exchange.value),
                        market_type=str(self.settings.market_type.value),
                        event="cycle_end",
                        symbol=None,
                        payload={
                            **(cycle_meta or {}),
                            "elapsed_sec": round(elapsed_time, 6),
                            "has_alerts": bool(alert_tasks),
                        },
                        run_id=self._run_id,
                        cycle_id=self._cycle_id,
                    )
            except Exception as e:
                self._logger.exception(e)
                if self.settings.debug:
                    self._schedule_debug_log(
                        level="error",
                        screener_name=self.settings.name,
                        screener_id=self.settings.id,
                        exchange=str(self.settings.exchange.value),
                        market_type=str(self.settings.market_type.value),
                        event="error",
                        symbol=None,
                        payload={"location": "consumer.start"},
                        run_id=self._run_id,
                        cycle_id=self._cycle_id,
                        exc=e,
                    )
            await asyncio.sleep(self._CHECK_INTERVAL_SEC)

    async def stop(self) -> None:
        """Останавливает процесс прослушивания данных и проверки условий."""
        self._is_running = False
        await self._telegram_bot.close()

    async def _check_filters(self) -> tuple[list[asyncio.Task], dict]:
        """Проверяет данные по всем фильтрам и отправляет сигнал при успехе."""
        if not self.settings.any_filters_status:
            return [], {"reason": "no_filters_selected"}

        klines = await self._parsers.agg_trades.fetch_collected_data()
        ticker_daily = await self._parsers.ticker_daily.fetch_collected_data()
        now = time.time()
        if not klines and now - self._last_agg_empty_warn_ts >= 60.0:
            self._last_agg_empty_warn_ts = now
            self._logger.warning(
                "AggTrades: klines пуст по всем символам — фильтры (OI/Liquidations/pump/volume) "
                "не пройдут проверку «есть свеча», пока websocket aggTrades не начнёт отдавать сделки."
            )
        total_symbols = len(ticker_daily)
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
        blocked_timeout = 0
        blocked_day_limit = 0
        missing_klines = 0
        for symbol in ticker_daily:
            if self._timeout_tracker.is_blocked(symbol):
                self._logger.trace(f"[x] {symbol} is not valid. Reason: timeout")
                blocked_timeout += 1
                continue
            if self.settings.max_day_alerts and not self._signal_counter.is_within_limit(
                symbol, self.settings.max_day_alerts
            ):
                self._logger.trace(f"[x] {symbol} is not valid. Reason: max day alerts limit")
                blocked_day_limit += 1
                continue
            ticker = normalize_ticker(symbol)
            # Значение фандинга: сначала пытаемся по "сырому" symbol,
            # если нет — пробуем по нормализованному тикеру.
            symbol_funding_rate = funding_rate.get(symbol)
            if symbol_funding_rate is None:
                symbol_funding_rate = funding_rate.get(ticker, 0.0)
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
                        symbol_funding_rate,
                        liquidations.get(ticker, []),
                        blacklist,
                        whitelist,
                    ),
                )
            )

        if self.settings.debug:
            self._schedule_debug_log(
                level="info",
                screener_name=self.settings.name,
                screener_id=self.settings.id,
                exchange=str(self.settings.exchange.value),
                market_type=str(self.settings.market_type.value),
                event="cycle_start",
                symbol=None,
                payload={
                    "total_symbols": total_symbols,
                    "tasks_created": len(tasks),
                    "blocked_timeout": blocked_timeout,
                    "blocked_day_limit": blocked_day_limit,
                    "missing_klines": missing_klines,
                    "pipeline_blocker": "agg_trades_no_symbols"
                    if len(klines) == 0
                    else None,
                    "data_sizes": {
                        "klines_symbols": len(klines),
                        "ticker_daily_symbols": len(ticker_daily),
                        "open_interest_symbols": len(open_interest) if isinstance(open_interest, dict) else None,
                        "funding_rate_symbols": len(funding_rate) if isinstance(funding_rate, dict) else None,
                        "liquidations_symbols": len(liquidations) if isinstance(liquidations, dict) else None,
                    },
                    "parsers_age_sec": {
                        "agg_trades": round(
                            now
                            - (
                                self._parsers.agg_trades.last_update_ts
                                or self._parsers.agg_trades.started_ts
                            ),
                            3,
                        ),
                        "ticker_daily": round(
                            now
                            - (
                                self._parsers.ticker_daily.last_update_ts
                                or self._parsers.ticker_daily.started_ts
                            ),
                            3,
                        ),
                        "open_interest": (
                            None
                            if not self._parsers.open_interest
                            else round(
                                now
                                - (
                                    self._parsers.open_interest.last_update_ts
                                    or self._parsers.open_interest.started_ts
                                ),
                                3,
                            )
                        ),
                        "funding_rate": (
                            None
                            if not self._parsers.funding_rate
                            else round(
                                now
                                - (
                                    self._parsers.funding_rate.last_update_ts
                                    or self._parsers.funding_rate.started_ts
                                ),
                                3,
                            )
                        ),
                        "liquidations": (
                            None
                            if not self._parsers.liquidations
                            else round(
                                now
                                - (
                                    self._parsers.liquidations.last_update_ts
                                    or self._parsers.liquidations.started_ts
                                ),
                                3,
                            )
                        ),
                    },
                    "seconds_since_last_signal": None if not self._last_signal_ts else round(now - self._last_signal_ts, 3),
                },
                run_id=self._run_id,
                cycle_id=self._cycle_id,
            )

        alert_tasks = []
        total_signals = 0
        error_count = 0
        collect_fail_details = bool(getattr(self.settings, "debug", False))
        fail_reason_counts: dict[str, int] = {} if collect_fail_details else {}
        fail_samples: list[str] = [] if collect_fail_details else []
        for task in asyncio.as_completed(tasks):
            try:
                result = await task
            except Exception as e:
                self._logger.error(f"Error processing filters: ({type(e)}) {e}")
                error_count += 1
                if self.settings.debug:
                    self._schedule_debug_log(
                        level="error",
                        screener_name=self.settings.name,
                        screener_id=self.settings.id,
                        exchange=str(self.settings.exchange.value),
                        market_type=str(self.settings.market_type.value),
                        event="error",
                        symbol=None,
                        payload={"location": "consumer._check_filters.as_completed"},
                        run_id=self._run_id,
                        cycle_id=self._cycle_id,
                        exc=e,
                    )
                continue
            if isinstance(result, tuple) and isinstance(result[0], SignalDTO):
                signal, calc_debug = result
            else:
                signal, calc_debug = result, None

            if isinstance(signal, SignalDTO):
                try:
                    total_signals += 1
                    self._last_signal_ts = time.time()
                    self._timeout_tracker.block(signal.symbol, self.settings.timeout_sec)
                    daily_signal_count = self._signal_counter.add(signal.symbol)

                    # Обновляем ставку фандинга "на лету" по символу, если нужно
                    await self._enrich_signal_with_funding_rate(signal)

                    # Логируем фактическое значение фандинга в сигнале
                    self._logger.info(
                        "Signal created: symbol={}, funding_rate={}",
                        signal.symbol,
                        signal.funding_rate,
                    )

                    # Заполняем ScreeningResult из SignalDTO (датакласс, без timestamp/datetime)
                    screening_result = ScreeningResult(
                        symbol=signal.symbol,
                        ticker=signal.ticker,
                        last_price=signal.last_price,
                        funding_rate=signal.funding_rate,
                        daily_volume=signal.daily_volume,
                        daily_price=signal.daily_price,
                        pd_start_price=signal.pd_start_price,
                        pd_final_price=signal.pd_final_price,
                        pd_price_change_pct=signal.pd_price_change_pct,
                        pd_price_change_usdt=signal.pd_price_change_usdt,
                        oi_start_value=signal.oi_start_value,
                        oi_final_value=signal.oi_final_value,
                        oi_change_pct=signal.oi_change_pct,
                        oi_change_coins=signal.oi_change_coins,
                        oi_change_usdt=signal.oi_change_usdt,
                        lq_amount_usdt=signal.lq_amount_usdt,
                        vl_multiplier=signal.vl_multiplier,
                    )

                    text = generate_text(
                        symbol=signal.symbol,
                        exchange=self.settings.exchange,
                        market_type=self.settings.market_type,
                        settings=self.settings,
                        result=screening_result,
                        daily_signal_count=daily_signal_count,
                    )

                    alert_task = asyncio.create_task(
                        self._send_signal(signal.symbol, text)
                    )
                    alert_tasks.append(alert_task)

                    if self.settings.debug:
                        self._schedule_debug_log(
                            level="info",
                            screener_name=self.settings.name,
                            screener_id=self.settings.id,
                            exchange=str(self.settings.exchange.value),
                            market_type=str(self.settings.market_type.value),
                            event="signal",
                            symbol=signal.symbol,
                            payload={
                                "signal": signal.model_dump(),
                                "screening_result": screening_result.__dict__,
                                "generate_text_input": {
                                    "symbol": signal.symbol,
                                    "exchange": str(self.settings.exchange.value),
                                    "market_type": str(self.settings.market_type.value),
                                    "text_template_type": str(self.settings.text_template_type.value),
                                    "daily_signal_count": daily_signal_count,
                                },
                                "message_text": text,
                                "calc": calc_debug,
                            },
                            run_id=self._run_id,
                            cycle_id=self._cycle_id,
                        )
                    self._logger.success(f"Processsed filters for {signal.symbol}")
                except Exception as e:
                    self._logger.error(f"Error sending filters: ({type(e)}) {e}")
                    error_count += 1
                    if self.settings.debug:
                        self._schedule_debug_log(
                            level="error",
                            screener_name=self.settings.name,
                            screener_id=self.settings.id,
                            exchange=str(self.settings.exchange.value),
                            market_type=str(self.settings.market_type.value),
                            event="error",
                            symbol=getattr(signal, "symbol", None),
                            payload={"location": "consumer._check_filters.signal_handling"},
                            run_id=self._run_id,
                            cycle_id=self._cycle_id,
                            exc=e,
                        )
            else:
                # signal тут строка с причиной отказа
                s = str(signal)
                if "no klines data" in s:
                    missing_klines += 1

                if collect_fail_details:
                    # Базовая агрегация "Reason: ..."
                    reason = "unknown"
                    try:
                        marker = "Reason:"
                        if marker in s:
                            reason = s.split(marker, 1)[1].strip()
                    except Exception:
                        reason = "unknown"

                    # Троттлим payload: Reason может содержать большие metadata.
                    reason_key = reason
                    if len(reason_key) > 180:
                        reason_key = reason_key[:180] + "…"

                    fail_reason_counts[reason_key] = fail_reason_counts.get(
                        reason_key, 0
                    ) + 1
                    if len(fail_samples) < 5:
                        fail_samples.append(s[:220])

                    # Старое поведение: не спамим whitelisted / not USDT pair в app.log
                    if "whitelisted" not in s and "not USDT pair" not in s:
                        self._logger.info(s)

        meta = {
            "total_symbols": total_symbols,
            "tasks_created": len(tasks),
            "signals": total_signals,
            "errors": error_count,
            "blocked_timeout": blocked_timeout,
            "blocked_day_limit": blocked_day_limit,
            "missing_klines": missing_klines,
            "fail_reasons_top": dict(
                sorted(fail_reason_counts.items(), key=lambda kv: kv[1], reverse=True)[
                    :10
                ]
            )
            if collect_fail_details
            else {},
            "fail_samples": fail_samples if collect_fail_details else [],
        }
        return alert_tasks, meta

    async def _send_signal(self, symbol: str, text: str) -> dict:
        """Отправляет сообщение и пишет debug-лог по результату (без env-секретов)."""
        try:
            resp = await self._telegram_bot.send_message(
                bot_token=self.settings.bot_token,
                chat_id=self.settings.chat_id,
                text=text,
            )
            if self.settings.debug:
                result = resp.get("result") if isinstance(resp, dict) else None
                safe_telegram = {
                    "ok": resp.get("ok") if isinstance(resp, dict) else None,
                    "description": resp.get("description") if isinstance(resp, dict) else None,
                }
                if isinstance(result, dict):
                    safe_telegram["message_id"] = result.get("message_id")
                    safe_telegram["date"] = result.get("date")
                self._schedule_debug_log(
                    level="info",
                    screener_name=self.settings.name,
                    screener_id=self.settings.id,
                    exchange=str(self.settings.exchange.value),
                    market_type=str(self.settings.market_type.value),
                    event="telegram_sent",
                    symbol=symbol,
                    payload={
                        "ok": True,
                        "message_len": len(text or ""),
                        "telegram": safe_telegram,
                    },
                    run_id=self._run_id,
                    cycle_id=self._cycle_id,
                )
            return resp
        except Exception as e:
            if self.settings.debug:
                self._schedule_debug_log(
                    level="error",
                    screener_name=self.settings.name,
                    screener_id=self.settings.id,
                    exchange=str(self.settings.exchange.value),
                    market_type=str(self.settings.market_type.value),
                    event="telegram_error",
                    symbol=symbol,
                    payload={
                        "ok": False,
                        "message_len": len(text or ""),
                    },
                    run_id=self._run_id,
                    cycle_id=self._cycle_id,
                    exc=e,
                )
            raise

    async def _enrich_signal_with_funding_rate(self, signal: SignalDTO) -> None:
        """Добирает актуальный фандинг по символу, если парсер не заполнил его.

        Использует TTL-кэш, чтобы не дергать API биржи при повторных сигналах по тому же тикеру.
        """
        if self.market_type != MarketType.FUTURES:
            return
        if signal.funding_rate not in (0.0, 0):
            return

        now = time.time()
        cached = self._funding_rate_cache.get(signal.symbol)
        if cached is not None and cached[1] > now:
            signal.funding_rate = cached[0]
            return

        try:
            client_factory = get_uni_client(self.exchange)
            client = await client_factory.create()
            async with client:
                value = await client.funding_rate(signal.symbol)  # type: ignore[arg-type]
            rate = float(value)
            signal.funding_rate = rate
            self._funding_rate_cache[signal.symbol] = (
                rate,
                now + self._FUNDING_RATE_CACHE_TTL_SEC,
            )
            self._logger.info(
                "Enriched funding rate for symbol {}: {}",
                signal.symbol,
                signal.funding_rate,
            )
        except Exception as e:
            self._logger.error(
                "Error fetching funding rate on-demand for {}: ({}) {}",
                signal.symbol,
                type(e),
                e,
            )

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
    ) -> str | tuple[SignalDTO, dict]:
        """Проверяет фильтры для конкретного тикера."""
        only_usdt_pair_result = OnlyUsdtPairsFilter.process(symbol)
        if not only_usdt_pair_result.ok:
            return f"[x] {symbol}. Reason: not USDT pair. Details: {only_usdt_pair_result}"

        # Если по тикеру ещё нет ни одной свечи, пропускаем его, чтобы не падать на индексах.
        if not klines:
            return f"[x] {symbol}. Reason: no klines data"

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
                    lq_min_amount_pct=settings.lq_min_amount_pct,
                    daily_volume_usd=ticker_daily["q"],
                )
                if not liquidations_result.ok:
                    return f"[x] {symbol}. Reason: liquidations sum filter. Details: {liquidations_result}"
            else:
                liquidations_result = None
        else:
            open_interest_result = None
            funding_rate_result = None
            liquidations_result = None
        
        signal = SignalDTO(
            timestamp=int(time.time()),
            datetime=time.ctime(),
            symbol=symbol,
            ticker=ticker,
            last_price=last_price,
            funding_rate=funding_rate,
            daily_volume=ticker_daily["q"],
            daily_price=ticker_daily["p"],
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

        calc_debug = {
            "inputs": {
                "ticker_daily": dict(ticker_daily),
                "last_price": last_price,
                "funding_rate_in": funding_rate,
                "klines_len": len(klines),
                "open_interest_len": len(open_interest) if open_interest is not None else 0,
                "liquidations_len": len(liquidations) if liquidations is not None else 0,
            },
            "settings": {
                "pd_status": settings.pd_status,
                "pd_interval_sec": settings.pd_interval_sec,
                "pd_min_change_pct": settings.pd_min_change_pct,
                "oi_status": settings.oi_status,
                "oi_interval_sec": settings.oi_interval_sec,
                "oi_min_change_pct": settings.oi_min_change_pct,
                "oi_min_change_usd": settings.oi_min_change_usd,
                "fr_status": settings.fr_status,
                "fr_min_value_pct": settings.fr_min_value_pct,
                "fr_max_value_pct": settings.fr_max_value_pct,
                "vl_status": settings.vl_status,
                "vl_interval_sec": settings.vl_interval_sec,
                "vl_min_multiplier": settings.vl_min_multiplier,
                "lq_status": settings.lq_status,
                "lq_interval_sec": settings.lq_interval_sec,
                "lq_min_amount_usd": settings.lq_min_amount_usd,
                "lq_min_amount_pct": settings.lq_min_amount_pct,
                "dv_status": settings.dv_status,
                "dv_min_usd": settings.dv_min_usd,
                "dv_max_usd": settings.dv_max_usd,
                "dp_status": settings.dp_status,
                "dp_min_pct": settings.dp_min_pct,
                "dp_max_pct": settings.dp_max_pct,
                "timeout_sec": settings.timeout_sec,
                "max_day_alerts": settings.max_day_alerts,
                "text_template_type": str(settings.text_template_type.value),
            },
            "filters": {
                "pump_dump": None if pump_dump_result is None else {
                    "start_price": pump_dump_result.start_price,
                    "final_price": pump_dump_result.final_price,
                    "price_change_pct": pump_dump_result.price_change_pct,
                    "price_change_usdt": pump_dump_result.price_change_usdt,
                },
                "volume_multiplier": None if volume_multiplier_result is None else {
                    "multiplier": volume_multiplier_result.multiplier,
                },
                "open_interest": None if open_interest_result is None else {
                    "start_value": open_interest_result.start_value,
                    "final_value": open_interest_result.final_value,
                    "change_pct": open_interest_result.change_pct,
                    "change_coins": open_interest_result.change_coins,
                    "change_usdt": open_interest_result.change_usdt,
                },
                "funding_rate": None if funding_rate_result is None else {
                    "funding_rate": funding_rate,
                },
                "liquidations": None if liquidations_result is None else {
                    "amount_usdt": liquidations_result.amount_usdt,
                },
            },
        }

        return signal, calc_debug