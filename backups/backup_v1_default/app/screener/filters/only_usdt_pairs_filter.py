__all__ = ["OnlyUsdtPairsFilter"]

from .abstract import Filter, FilterResult


class OnlyUsdtPairsFilter(Filter):
    """Фильтр для проверки что пара к USDT."""

    def process(self, symbol: str) -> FilterResult:
        return FilterResult(ok=symbol.endswith("USDT", "-USDT-SWAP"))