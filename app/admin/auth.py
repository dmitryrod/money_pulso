from __future__ import annotations

from starlette.requests import Request
from starlette.responses import Response
from starlette_admin.auth import AdminConfig, AdminUser, AuthProvider

from app.config import config


class AdminAuthProvider(AuthProvider):
    """Провайдер аутентификации, который пускает всех без логина и пароля.

    Требование для MVP: админка должна открываться без ввода пароля.
    """

    async def login(  # type: ignore[override]
        self,
        username: str | None,
        password: str | None,
        remember_me: bool,
        request: Request,
        response: Response,
    ) -> Response:
        # Просто считаем, что пользователь успешно залогинен.
        request.session.update({"username": username or config.admin.login})
        return response

    async def is_authenticated(self, request: Request) -> bool:  # type: ignore[override]
        # Всегда считаем пользователя аутентифицированным.
        if "username" not in request.session:
            request.session["username"] = config.admin.login
        request.state.user = request.session["username"]
        return True

    def get_admin_config(self, request: Request) -> AdminConfig:  # type: ignore[override]
        return AdminConfig(app_title=config.admin.title, logo_url=config.admin.logo_url)

    def get_admin_user(self, request: Request) -> AdminUser:  # type: ignore[override]
        username = getattr(request.state, "user", config.admin.login)
        return AdminUser(username=username)

