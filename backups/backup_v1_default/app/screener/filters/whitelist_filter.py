__all__ = ["WhitelistFilter"]

from .abstract import Filter, FilterResult


class WhitelistFilter(Filter):
    """Фильтр для проверки наличия тикера в белом списке."""
    
    def process(self, ticker: str, whitelist: set[str]) -> FilterResult:
        if whitelist:
            FilterResult(ok=ticker in whitelist)
        return FilterResult(ok=True)
