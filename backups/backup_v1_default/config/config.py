from dataclasses import dataclass
import os
import uuid
from os import getenv

# подправь импорты под свой проект
from .database import _DatabaseConfig      # или откуда у тебя берётся конфиг БД
from .enums import EnvironmentType         # или реальный модуль с Enum'ом


@dataclass(frozen=True)
class _AdminConfig:
    """Настройки админ-панели."""

    title: str = "Admin Panel"
    """Название приложения."""

    logo_url: str = (
        "https://images.icon-icons.com/3256/PNG/512/admin_lock_padlock_icon_205893.png"
    )
    """Ссылка на логотип."""

    login: str = getenv("ADMIN_LOGIN", "admin")
    """Логин администратора."""

    password: str = getenv("ADMIN_PASSWORD", "admin")
    """Пароль администратора."""


@dataclass(frozen=True)
class Configuration:
    """Единая точка доступа к настройкам приложения."""

    db: _DatabaseConfig = _DatabaseConfig()
    """Конфигурация базы данных."""

    admin: _AdminConfig = _AdminConfig()
    """Конфигурация админ-панели."""

    try:
        environment: EnvironmentType = EnvironmentType(
            os.getenv("ENVIRONMENT", "productions")
        )
        """Текущее окружение проекта."""
    except KeyError as err:
        raise ValueError(f"Invalid environment: {os.getenv('ENVIRONMENT')}") from err

    cypher_key: str = getenv(
        "CYPHER_KEY", uuid.UUID(int=uuid.getnode()).hex[-12:]
    )
    """Ключ для шифрования."""


config: Configuration = Configuration()
"""Конфигурация приложения."""