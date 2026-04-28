"""Заголовки кэширования для статики админки в production (Lighthouse / CDN-friendly)."""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.config import config
from app.schemas import EnvironmentType


# Версия в пути (tabler.min-1.1.0) — при смене файла URL меняется; immutable безопасен.
_CACHE_STATIC = "public, max-age=31536000, immutable"
# UI-скрипт без хэша в имени — короткий SLA, чтобы обновления раздавались без смены URL.
_CACHE_TIMEZONE_UI = "public, max-age=86400"


def apply_production_asset_cache_headers(
    *, environment: EnvironmentType, path: str, response: Response
) -> None:
    """Выставляет Cache-Control для путей статики в ``EnvironmentType.PRODUCTION``.

    Args:
        environment: Режим приложения.
        path: ``request.url.path`` без query string.
        response: Исходящий ответ (заголовки мутируются in-place).
    """
    if environment is not EnvironmentType.PRODUCTION:
        return
    if path.startswith("/admin/statics/"):
        response.headers.setdefault("Cache-Control", _CACHE_STATIC)
    elif path == "/admin_api/ui/timezone.js":
        response.headers.setdefault("Cache-Control", _CACHE_TIMEZONE_UI)


class ProductionAssetCacheMiddleware(BaseHTTPMiddleware):
    """Добавляет долгий кэш для ``/admin/statics/*`` и сутки для ``timezone.js`` в проде."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        apply_production_asset_cache_headers(
            environment=config.environment,
            path=request.url.path,
            response=response,
        )
        return response
