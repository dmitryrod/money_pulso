__all__ = ["TelegramBot"]

import aiohttp


class TelegramBot:
    """Утилита для отправки сообщений в телеграм."""

    def __init__(self):
        """Инициализирует экземпляр класса TelegramBot."""
        self._session = aiohttp.ClientSession()

    async def send_message(self, bot_token: str, chat_id: int, text: str) -> dict:
        """Отправляет сообщение в телеграм"""
        url = f" https://api.telegram.org/bot{bot_token}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        async with self._session.post(url, json=data) as response:
            response.raise_for_status()
            return await response.json()

    async def close(self) -> None:
        """Закрывает сессию."""
        await self._session.close()