from .abstract import Filter, FilterResult


class DailyVolumeFilterResult(FilterResult):
    """Результат выполнения фильтра по дневному объему."""


class DailyVolumeFilter(Filter):
    """Фильтр для проверки дневного объема."""

    def process(self, *args, **kwargs) -> DailyVolumeFilterResult:
        """Обработка фильтра по дневному объему."""