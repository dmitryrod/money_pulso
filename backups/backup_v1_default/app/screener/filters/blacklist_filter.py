__all__ = ["BlacklistFilter"]

from .abstract import Filter, FilterResult


class BlacklistFilter(Filter):
    """Фильтр для проверки наличия тикера в черном списке."""

    def process(self, ticker: str, blacklist: set[str]) -> FilterResult:
        return FilterResult(ok=ticker not in blacklist)