# TODO

Задачи, отложенные из активных планов для реализации в будущем.

---

## Исторический бэктест

**Контекст:** часть плана Strategy Monitor (фазовое отслеживание пар).  
Текущий план реализует форвард-тестинг (сбор pnl% по live entry-сигналам).  
Исторический бэктест — следующий этап.

### Что нужно реализовать

**Модуль:** `app/backtest/`

- `data_fetcher.py` — загрузка исторических данных через `unicex` REST:
  - `futures_klines(symbol, "1m", ...)` → исторические свечи  
    Требует расширить unicex Binance-адаптер: добавить маппинг `takerBuyBaseAssetVolume` (индекс 9 в raw ответе) в `KlineDict` как поле `bv`, и вычислять `sv = v - bv`
  - `open_interest_hist(symbol, "1m", start, end)` → `GET /fapi/v1/openInterestHist` (только Binance, метод уже есть в `binance/client.py`, не вынесен в `IUniClient`)
  - Ликвидации: `GET /fapi/v1/allForceOrders` — ограничения: ~30 дней истории, только Binance, один символ за раз

- `runner.py` — прогон `Phase1Evaluator → Phase2Evaluator → Phase3Evaluator` по историческим данным как по временному ряду (sliding window)

- `report.py` — итоговый отчёт:
  - win rate, средний pnl%, MFE/MAE по всем сработавшим сигналам
  - score distribution (качество сигналов)
  - время от Phase 1 до entry-сигнала (среднее, медиана)
  - таблица всех сделок: timestamp, phase, price, oi, cvd, liq_usd, signal, entry, exit, pnl

- Доступен через CLI или страницу `/admin/backtest`

### Ключевые метрики для сбора (на каждый сигнал)

```python
# Цена
surge_start_price, surge_peak_price, surge_pct, time_to_peak_minutes

# OI
oi_at_surge_start, oi_peak, oi_at_signal
oi_drawdown_from_peak_pct, oi_zscore_at_peak

# CVD
cvd_at_surge_start, cvd_peak, cvd_at_signal
cvd_reversal_pct, cvd_divergence_detected

# Ликвидации
total_liq_long_usd, total_liq_short_usd
liq_cluster_count, largest_single_liq_usd
time_from_peak_to_first_liq_seconds

# Сигнал
signal_candle_close, signal_candle_volume
signal_candle_type  # 'engulfing', 'pinbar', 'break_structure'
entry_price, entry_delay_seconds

# Результат
exit_price, pnl_pct
max_favorable_excursion_pct, max_adverse_excursion_pct
hold_time_minutes, exit_reason  # 'tp' | 'sl' | 'timeout'
```

### Ограничения

- Исторические ликвидации: только Binance, только ~30 дней, только по одному символу за запрос
- `openInterestHist` не вынесен в `IUniClient` — работает только для Binance
- Другие биржи (Bybit, OKX) имеют свои API с аналогичными ограничениями; потребуется отдельный маппинг в `unicex`

### Зависимости

- Расширить `KlineDict` полями `bv`/`sv` (делается в рамках текущего плана Strategy Monitor — Шаг 1)
- Расширить Binance-адаптер unicex: пробросить `takerBuyBaseAssetVolume` из klines REST-ответа
- Вынести `open_interest_hist` в `IUniClient` или сделать Binance-specific обёртку в `data_fetcher.py`
