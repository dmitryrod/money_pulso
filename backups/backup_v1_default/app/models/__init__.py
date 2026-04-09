"""Пакет моделей приложения (DTO, dataclasses, attrs, …)."""

__all__ = ["SettingsDTO", "ScreeningResult"]

from .settings import SettingsDTO
from .screener import ScreeningResult