"""Перечисления, используемые в приложении."""

__all__ = ["EnvironmentType"]

from .enums import StrEnum


class EnvironmentType(StrEnum):
    """Перечисление типов окружения."""

    DEVELOPMENT = "development"
    PRODUCTION = "production"


class TextTemplateType(StrEnum):
    """Перечисление шаблонов текста."""

    DEFAULT = "default"
    TREE = "tree"