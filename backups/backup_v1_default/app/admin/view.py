"""Пользовательские представления для админ-панели."""

__all__ = [
    "SettingsModelView",
    "MetrCustomView",
    "LogsViewerView",
]

import os
from datetime import datetime
from typing import Any

import aiofiles
import psutil
from starlette.requests import Request
from starlette.responses import Response
from starlette.templating import Jinja2Templates
from starlette_admin import (
    BooleanField,
    CustomView,
    EnumField,
    FloatField,
    IntegerField,
    StringField,
)
from starlette_admin.contrib.sqla import ModelView
from starlette_admin.exceptions import FormValidationError
from unicex import Exchange, MarketType

from app.schemas import TextTemplateType
from app.config import logger


class SettingsModelView(ModelView):
    """Настройки основного скринера и бизнес-логики сигналов."""

    name = "Скринер"

    create_template = "create_screener.html"
    edit_template = "edit_screener.html"
    exclude_fields_from_edit = ["market_type"]

    fields = [
        # Общие настройки
        BooleanField(
            "enabled",
            label="Включить скринер",
            # help_text="Снимите галочку, если нужно полностью остановить проверки и отправку сигналов."
        ),
        EnumField(
            "exchange",
            label="Биржа для анализа",
            choices=[
                (Exchange.BINANCE.value, Exchange.BINANCE.capitalize()),
                (Exchange.BYBIT.value, Exchange.BYBIT.capitalize()),
                (Exchange.BITGET.value, Exchange.BITGET.capitalize()),
                (Exchange.ASTER.value, Exchange.ASTER.capitalize()),
                (Exchange.MEXC.value, Exchange.MEXC.capitalize()),
                (Exchange.OKX.value, Exchange.OKX.capitalize()),
                (Exchange.GATE.value, Exchange.GATE.capitalize()),
            ],
            required=True,
            # help_text="Выберите торговую площадку, с которой бот будет собирать и формировать сигналы."
        ),
        EnumField(
            "market_type",
            label="Тип рынка внутри выбранной биржи",
            choices=[
                (MarketType.SPOT.value, MarketType.SPOT.capitalize()),
                (MarketType.FUTURES.value, MarketType.FUTURES.capitalize()),
            ],
            required=True,
            help_text="Укажите, для какого сегмента биржи (Spot или Futures) нужно запускать проверки. ! Тип рынка нельзя изменить после создания скринера",
        ),
        StringField(
            "blacklist",
            label="Черный список тикеров",
            help_text="Перечислите тикеры через запятую без постфикса USDT: BTC,ETH,XRP. Эти монеты будут игнорироваться.",
        ),
        StringField(
            "whitelist",
            label="Белый список тикеров",
            help_text=(
                "Если заполнено - сканируем только эти тикеры.",
                "Перечислите тикеры через запятую без постфикса USDT: BTC,ETH,XRP..."
                "Оставьте поле пустым, чтобы анализировать весь рынок.",
            ),
        ),
        # Фильтр пампов и дампов
        IntegerField(
            "pd_interval_sec",
            label="Интервал для измерения роста монеты, сек",
            help_text="Временной интервал для измерения роста монеты в секундах.",
        ),
        FloatField(
            "pd_min_change_pct",
            label="Минимальный рост цены монеты, %",
            help_text="Процент роста, при котором сработает фильтр пампа/дампа.",
        ),
        # Фильтр открытого интереса
        IntegerField(
            "oi_interval_sec",
            label="Интервал для измерения роста открытого интереса, сек",
            help_text="Интервал для измерения роста открытого интереса в секундах.",
        ),
        FloatField(
            "oi_min_change_pct",
            label="Минимальный рост открытого интереса, %",
            help_text="Минимальный процентный рост открытого интереса монеты в процентах, при котором сработает фильтр.",
        ),
        FloatField(
            "oi_min_change_usd",
            label="Минимальный рост открытого интереса монеты, $",
            help_text="Минимальный процентный рост открытого интереса монеты в долларах, при котором сработает фильтр.",
        ),
        # Фильтр ставки финансирования
        FloatField(
            "fr_min_value_pct",
            label="Минимальная ставка финансирования, %",
            help_text="Нижний порог допустимой ставки финансирования.",
        ),
        FloatField(
            "fr_max_value_pct",
            label="Максимальная ставка финансирования, %",
            help_text="Верхний порог допустимой ставки финансирования.",
        ),
        # Фильтр множителя объема
        IntegerField(
            "vl_interval_sec",
            label="Интервал расчета множителя объема, сек",
            help_text="Сколько секунд учитывается при сравнении объема.",
        ),
        FloatField(
            "vl_min_multiplier",
            label="Минимальный множитель объема, Х",
            help_text="Во сколько раз объем должен вырасти относительно среднего объема за сутки. Например, 50 = рост в 50 раз.",
        ),
        # Фильтр ликвидаций
        IntegerField(
            "lq_interval_sec",
            label="Интервал расчета ликвидаций, сек",
            help_text="Промежуток времени, за который суммируем ликвидации.",
        ),
        FloatField(
            "lq_min_amount_usd",
            label="Минимальная сумма ликвидаций, $",
            help_text="Минимальная сумма ликвидаций в долларах, при которой фильтр будет пройден.",
        ),
        # Фильтр объема монеты за сутки
        FloatField(
            "dv_min_usd",
            label="Минимальный суточный объем, $",
            help_text="Минимальный объем монеты в долларах, при котором фильтр будет пройден.",
        ),
        FloatField(
            "dv_max_usd",
            label="Максимальный суточный объем, $",
            help_text="Монета не пройдет фильтр, если объем монеты за сутки в долларах превышает это значение.",
        ),
        # Фильтр изменения цены монеты за сутки
        FloatField(
            "dp_min_pct",
            label="Минимальное изменение цены за сутки, %",
            help_text="Минимальное допустимое значение изменения цены за сутки в процентах.",
        ),
        FloatField(
            "dp_max_pct",
            label="Максимальное изменение цены за сутки, %",
            help_text="Ограничьте слишком волатильные монеты, указав верхнюю границу изменения цены в процентах.",
        ),
        # Настройка уведомлений
        IntegerField(
            "max_day_alerts",
            label="Максимум сигналов на тикер в сутки",
            required=True,
            help_text="Позволяет ограничить спам по одной монете. 0 означает без ограничений.",
        ),
        IntegerField(
            "timeout_sec",
            label="Таймаут между сигналами по тикеру, сек",
            required=False,
            help_text="Минимальное время между повторными уведомлениями по одной монете. Помогает избегать дублей.",
        ),
        IntegerField(
            "chat_id",
            label="ID Telegram чата для уведомлений",
            required=True,
            help_text="ID Telegram чата, в который будут отправляться уведомления.",
        ),
        StringField(
            "bot_token",
            label="Токен Telegram-бота, который будет отправлять уведомления",
            required=True,
            help_text="API-токен Telegram бота, который отправляет сигналы. Получите его у @BotFather и вставьте сюда.",
        ),
        BooleanField(
            "debug",
            label="Отладка",
            help_text="Если включено, в текст сообщения будет добавлен отладочный блок.",
            required=False,
        ),
    ]

    async def validate(self, request: Request, data: dict[str, Any]) -> None:
        errors = {}

        # Работа с логичаскими ошибками
        def ensure_min_before_max(min_key: str, max_key: str, message: str) -> None:
            min_value = data.get(min_key)
            max_value = data.get(max_key)
            if min_value is None or max_value is None:
                return
            if min_value > max_value:
                errors[min_key] = message
        
        ensure_min_before_max(
            "dv_min_usd",
            "dv_max_usd",
            "Минимальный суточный объем не может превышать максимальный.",
        )
        ensure_min_before_max(
            "dp_min_pct",
            "dp_max_pct",
            "Минимальное изменение цены за сутки не может быть больше максимального."
        )
        ensure_min_before_max(
            "fr_min_value_pct",
            "fr_max_value_pct",
            "Минимальная ставка финансирования должна быть ниже максимальной.",
        )

        timeout = data.get("timeout_sec")
        if timeout is not None and timeout < 0:
            errors["timeout_sec"] = "Таймаут между сигналами не может быть отрицательным."

        if data.get("max_day_alerts") is not None and data["max_day_alerts"] < 0:
            errors["max_day_alerts"] = "Количество сигналов в сутки не должно быть отрицательным"

        def ensure_positive(field: str, message: str) -> None:
            value = data.get(field)
            if value is None:
                return
            if value <= 0:
                errors[field] = message

        ensure_positive("pd_interval_sec", "Интервал для роста цены должен быть больше нуля.")
        ensure_positive(
            "oi_interval_sec", "Интервал анализа открытого интереса должен быть больше нуля."
        )
        ensure_positive(
            "vl_interval_sec","Интервал расчета множителя объема должен превышать ноль."
        )
        ensure_positive("vl_min_multiplier", "Множитель объема должен быть положительным.")
        ensure_positive("lq_interval_sec", "Интервал расчета ликвидаций должен быть больше нуля.")

        # Работа с дефолтными значениями
        if data.get("timeout_sec") is None:
            data["timeout_sec"] = 60

        def has_any_filters_selected() -> bool:
            """Проверяет, активирован ли хотя бы один фильтр."""
            # Пампы и дампы
            pumps_enabled = (
                data.get("pd_interval_sec") is not None
                and data.get("pd_min_change_pct") is not None
            )
        
            # Открытый интерес
            open_interest_enabled = data.get("oi_interval_sec") is not None and (
                data.get("oi_min_change_pct") is not None
                or data.get("oi_min_change_usd") is not None
            )

            # Ставка финансирования
            funding_rate_enabled = (
                data.get("fr_min_value_pct") is not None or data.get("fr_max_value_pct") is not None
            )

            # Множитель объема
            volume_multiplier_enabled = (
                data.get("vl_interval_sec") is not None
                and data.get("vl_min_multiplier") is not None
            )

            # Ликвидации
            liquidations_enabled = (
                data.get("lq_interval_sec") is not None
                and data.get("lq_min_amount_usd") is not None
            )

            # Суточный объем и изменение цены
            daily_volume_enabled = (
                data.get("dv_min_usd") is not None or data.get("dv_max_usd") is not None
            )
            daily_price_change_enabled = (
                data.get("dp_min_pct") is not None or data.get("dp_max_pct") is not None
            )

            return any(
                [
                    pumps_enabled,
                    open_interest_enabled,
                    funding_rate_enabled,
                    volume_multiplier_enabled,
                    liquidations_enabled,
                    daily_volume_enabled,
                    daily_price_change_enabled,
                ]
            )

        if not has_any_filters_selected():
            errors["enabled"] = (
                "Нужно настроить хотя бы один фильтр, иначе скринер ничего не проверяет."
            )

        if errors:
            raise FormValidationError(errors)


class SystemStatusView(CustomView):
    """Показывает ключевые метрики сервера в админ-панели."""

    async def render(self, request: Request, templates: Jinja2Templates) -> Response: # noqa
        """Возвращает шаблон с загрузкой CPU, RAM, диска и времени аптайма."""
        try:
            # Получение данных о системе
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            cpu_percent = psutil.cpu_percent(interval=1)
            boot_time = datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M:%S")

            # Подготовка контекста
            context: dict[str, Any] = {
                "request": request,
                "memory_total": f"{memory.total / (1024**3):.2f} GB",
                "memory_used": f"{memory.used / (1024**3):.2f} GB",
                "memory_percent": f"{memory.percent}%",
                "disk_total": f"{disk.total / (1024**3):.2f} GB",
                "disk_used": f"{disk.used / (1024**3):.2f} GB",
                "disk_percent": f"{disk.percent}%",
                "cpu_percent": f"{cpu_percent}%",
                "boot_time": boot_time,
            }