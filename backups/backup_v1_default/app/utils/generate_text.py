__all__ = ["generate_text"]

from unicex.enums import Exchange, MarketType
from unicex.extra import (
    generate_cg_link,
    generate_ex_link,
    generate_tv_link,
    make_humanreadable,
    normalize_symbol,
)

from app.models import ScreeningResult, SettingsDTO
from app.schemas import TextTemplateType


def _fmt_pct(value: float) -> str:
    return f"{value:.2}%"


def _fmt_coins(value: float) -> str:
    return f"{make_humanreadable(value)}¢"


def _fmt_dollars(value: float) -> str:
    return f"{make_humanreadable(value)}$"


def _fmt_multiplier(value: float) -> str:
    return f"{value:.1f}x"


def _generate_tree_type_text(
    symbol: str,
    exchange: Exchange,
    market_type: MarketType,
    settings: SettingsDTO,
    result: ScreeningResult,
    daily_signal_count: int,
) -> str:
    """Возвращает текст уведмолени в формате дерева."""
    _HEADER = (
        "┌ {screener_name} #{symbol}\n├ 💱 <a href='{link_ex}'>{exchange} {market_type}</a>\n|"
    )
    _FOOTER = """
    ├ 📊 Vol 24h: {daily_volume}$
    ├ 🏷️ Prc 24h: {daily_price}
    ├ 🔔 Sig 24h: {daily_signal_count}
    └ 🔗 <a href='{link_cg}'>CoinGlass</a>; <a href='{link_tv}'>TradingView</a>
    """
    normalized_symbol = normalize_symbol(symbol)
    link_tv = generate_tv_link(exchange, market_type, normalized_symbol)
    link_cg = generate_cg_link(exchange, market_type, normalized_symbol)
    link_ex = generate_ex_link(exchange, market_type, normalized_symbol)

    if settings.oi_status:
        oi_block = f"\n├ OI: {_fmt_pct(result.oi_change_pct)} ({_fmt_dollars(result.oi_change_usdt)})\n| └ {_fmt_coins(result.oi_start_value)} ⭢ {_fmt_coins(result.oi_final_value)}\n|" #type: ignore
    else:
        oi_block = None

    if settings.pd_status:
        pd_block = f"\n├ PD: {_fmt_pct(result.pd_price_change_pct)}\n| └ {result.pd_start_price}$ ⭢ {result.pd_final_price}$\n|" #type: ignore
    else:
        pd_block = None

    if settings.vl_status:
        vl_block = f"\n├ VL: {_fmt_multiplier(result.vl_multiplier)}\n|" #type: ignore
    else:
        vl_block = None

    if settings.fr_status:
        fr_block = f"\n├ FR: {result.funding_rate:.4}%\n|"
    else:
        fr_block = None

    if settings.lq_status:
        lq_block = f"\n├ LQ: {_fmt_dollars(result.lq_amount_usdt)}\n|" #type: ignore
    else:
        lq_block = None

    header = _HEADER.format_map(
        dict(
            screener_name=settings.name,
            symbol=symbol,
            link_ex=link_ex,
            exchange=exchange.value.capitalize(),
            market_type=market_type.value.capitalize(),
        )
    )

    footer = _FOOTER.format_map(
        dict(
            daily_volume=make_humanreadable(result.daily_volume),
            daily_price=str(round(result.daily_price, 2)) + "%",
            link_cg=link_cg,
            link_tv=link_tv,
            daily_signal_count=daily_signal_count,
        )
    )

    text = ""
    for part in [header, pd_block, oi_block, vl_block, fr_block, lq_block, footer]:
        if part:
            text += part
    return text


def _generate_default_type_text(
    symbol: str,
    exchange: Exchange,
    market_type: MarketType,
    settings: SettingsDTO,
    result: ScreeningResult,
    daily_signal_count: int,
) -> str:
    """Возвращает текст уведмоления в стандартном формате."""
    _HEADER = "<code>{symbol}-</code>\nСкринер: {screener_name}"
    _FILTERS_HEADER = "♻️ Фильтры: "
    _METRICS_HEADER = "📊 Метрики:"
    _FOOTER = "🔗 {tv_link} | {cg_link} | {ex_link}"
    normalized_symbol = normalize_symbol(symbol)
    link_tv = generate_tv_link(exchange, market_type, normalized_symbol)
    link_cg = generate_cg_link(exchange, market_type, normalized_symbol)
    link_ex = generate_ex_link(exchange, market_type, normalized_symbol)

    header = _HEADER.format_map(
        dict(
            symbol=symbol,
            screener_name=settings.name,
        )
    )

    filter_lines: list[str] = []

    if settings.pd_status:
        filter_lines.append(
            f"Памп: {_fmt_pct(settings.pd_min_change_pct)}, {settings.pd_interval_sec} сек."
        )

    if settings.oi_status:
        if settings.oi_min_change_pct is not None:
            oi_change_pct = _fmt_pct(settings.oi_min_change_pct)
        else:
            oi_value = _fmt_dollars(settings.oi_min_change_usd)
        filter_lines.append(f"Открытый интерес: {oi_value}, {settings.oi_interval_sec} сек.")
    
    if settings.vl_status:
        filter_lines.append(
            f"Множитель объема: {_fmt_multiplier(settings.vl_min_multiplier)}"
            f", {settings.vl_interval_sec} сек."
        )
    
    if settings.lq_status:
        filter_lines.append(
            f"Ликвидации: {_fmt_dollars(settings.lq_min_amount_usd)}"
            f", {settings.lq_interval_sec} сек. "
        )
    
    metrics_lines = [
        f"Фандинги: {result.funding_rate:.4}%",
        f"Цена 24ч.: {result.daily_price:.2f}%",
        f"Объем 24ч.: {make_humanreadable(result.daily_volume)}$",
        f"Сигнал 24ч.: {daily_signal_count}",
    ]

    footer = _FOOTER.format_map(
        dict(
            tv_link=f"<a href='{link_tv}'>TV</a>",
            cg_link=f"<a href='{link_cg}'>CG</a>",
            ex_link=f"<a href='{link_ex}'>{exchange.value.capitalize()}</a>",
        )
    )

    parts: list[str] = [header]

    if filter_lines:
        # Блок фильтров добавляем только если есть активные фильтры
        parts.append("\n".join([_FILTERS_HEADER, *filter_lines]))
    
    parts.append("\n".join([_METRICS_HEADER, *metrics_lines]))
    parts.append(footer)

    return "\n\n".join(parts)

# todo вставить секунды
def generate_text(
symbol: str,
exchange: Exchange,
market_type: MarketType,
settings: SettingsDTO,
result: ScreeningResult,
daily_signal_count: int,
) -> str:
    """Собирает итоговый текст сигнала для Telegram."""
    if settings.text_template_type == TextTemplateType.TREE:
        return _generate_tree_type_text(
            symbol, exchange, market_type, settings, result, daily_signal_count
        )
    elif settings.text_template_type == TextTemplateType.DEFAULT:
        return _generate_default_type_text(
            symbol, exchange, market_type, settings, result, daily_signal_count
        )
    else:
        raise ValueError(f"Unknown text template type: {settings.text_template_type}")
