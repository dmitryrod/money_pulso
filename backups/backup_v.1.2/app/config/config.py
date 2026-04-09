from __future__ import annotations

from dataclasses import dataclass
import os
import uuid
from os import getenv

from app.schemas import EnvironmentType


@dataclass(frozen=True)
class _DatabaseConfig:
    """Настройки подключения к базе данных."""

    user: str = getenv("POSTGRES_USER", "postgres")
    password: str = getenv("POSTGRES_PASSWORD", "postgres")
    host: str = getenv("POSTGRES_HOST", "postgres")
    port: int = int(getenv("POSTGRES_PORT", "5432"))
    name: str = getenv("POSTGRES_DB", "screener_db")

    def build_connection_str(self) -> str:
        return (
            f"postgresql+asyncpg://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.name}"
        )


@dataclass(frozen=True)
class _AdminConfig:
    """Настройки админ-панели."""

    title: str = "Paid Screener"
    logo_url: str = (
        "https://images.icon-icons.com/3256/PNG/512/admin_lock_padlock_icon_205893.png"
    )
    login: str = getenv("ADMIN_LOGIN", "admin")
    password: str = getenv("ADMIN_PASSWORD", "admin")


@dataclass(frozen=True)
class Configuration:
    """Единая точка доступа к настройкам приложения."""

    db: _DatabaseConfig = _DatabaseConfig()
    admin: _AdminConfig = _AdminConfig()

    try:
        environment: EnvironmentType = EnvironmentType(
            os.getenv("ENVIRONMENT", "development")
        )
    except ValueError as err:
        raise ValueError(f"Invalid environment: {os.getenv('ENVIRONMENT')}") from err

    cypher_key: str = getenv(
        "CYPHER_KEY", uuid.UUID(int=uuid.getnode()).hex[-12:]
    )

    # Дефолты для Telegram, если не заданы в настройках скринера
    telegram_bot_token: str | None = getenv("TELEGRAM_BOT_TOKEN")
    _telegram_chat_id_raw: str | None = getenv("TELEGRAM_CHAT_ID")
    telegram_chat_id: int | None = (
        int(_telegram_chat_id_raw) if _telegram_chat_id_raw else None
    )


config: Configuration = Configuration()
