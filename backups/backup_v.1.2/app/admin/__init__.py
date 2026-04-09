"""Настройка админ-панели и регистрация представлений."""

__all__ = [
    "register_admin_routes",
]

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import func, select, update
from starlette.responses import Response
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from starlette_admin import I18nConfig
from starlette_admin.contrib.sqla import Admin

from app.config import config
from app.database import Database, SettingsORM

from .auth import AdminAuthProvider
from .view import LogsViewerView, MetrCustomView, SettingsModelView


def register_admin_routes(app: FastAPI) -> None:
    """Регистрирует представления админ-панели в FastAPI-приложении."""

    @app.get("/admin_api/screeners/global-debug")
    async def _get_global_debug() -> JSONResponse:
        async with Database.session_context() as db:
            total = await db.session.scalar(select(func.count()).select_from(SettingsORM))
            enabled_count = await db.session.scalar(
                select(func.count())
                .select_from(SettingsORM)
                .where(SettingsORM.debug.is_(True))
            )
        total_i = int(total or 0)
        enabled_i = int(enabled_count or 0)
        return JSONResponse(
            {
                "total": total_i,
                "enabled_count": enabled_i,
                "all_enabled": total_i > 0 and enabled_i == total_i,
                "any_enabled": enabled_i > 0,
            }
        )

    @app.post("/admin_api/screeners/global-debug")
    async def _set_global_debug(enabled: bool) -> JSONResponse:
        async with Database.session_context() as db:
            await db.session.execute(update(SettingsORM).values(debug=enabled))
            await db.commit()
            total = await db.session.scalar(select(func.count()).select_from(SettingsORM))
        return JSONResponse({"ok": True, "enabled": enabled, "total": int(total or 0)})

    @app.get("/admin_api/screeners/global-debug.js")
    async def _global_debug_js() -> Response:
        js = r"""
(() => {
  const STATE_URL = '/admin_api/screeners/global-debug';

  function el(tag, attrs = {}, children = []) {
    const node = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
      if (k === 'class') node.className = v;
      else if (k === 'text') node.textContent = v;
      else if (k.startsWith('on') && typeof v === 'function') node.addEventListener(k.slice(2), v);
      else if (v !== undefined && v !== null) node.setAttribute(k, String(v));
    }
    for (const child of children) node.append(child);
    return node;
  }

  function findMountPoint() {
    // Идеальный вариант: вставиться рядом с кнопкой "Добавить Скринер"
    const addBtn = document.querySelector('a.btn.btn-primary, a.btn.btn-primary[href*="/admin/screeners/create"]');
    if (addBtn && addBtn.parentElement) return { type: 'after-button', button: addBtn, container: addBtn.parentElement };

    // Фолбэк: правая часть заголовка карточки списка
    const cardHeader = document.querySelector('.card .card-header, .content .card-header');
    if (cardHeader) return { type: 'append', container: cardHeader };

    const pageHeader = document.querySelector('.page-header');
    if (pageHeader) return { type: 'append', container: pageHeader };

    return { type: 'append', container: document.body };
  }

  async function fetchState() {
    const res = await fetch(STATE_URL, { credentials: 'same-origin' });
    if (!res.ok) throw new Error('state fetch failed');
    return await res.json();
  }

  async function setState(enabled) {
    const url = `${STATE_URL}?enabled=${enabled ? 'true' : 'false'}`;
    const res = await fetch(url, { method: 'POST', credentials: 'same-origin' });
    if (!res.ok) throw new Error('state set failed');
    return await res.json();
  }

  function renderToggle(mount) {
    const wrapper = el('div', { class: 'd-flex align-items-center gap-2 ms-3', style: 'white-space:nowrap; flex: 0 0 auto;' });

    const switchWrap = el('label', { class: 'form-check form-switch m-0' });
    const input = el('input', { class: 'form-check-input', type: 'checkbox', id: 'global-debug-toggle' });
    const label = el('span', { class: 'form-check-label', text: 'Глобальный режим отладки' });
    switchWrap.append(input, label);

    const status = el('div', { class: 'text-secondary small', id: 'global-debug-status', text: '' });

    wrapper.append(switchWrap, status);

    if (mount?.type === 'after-button' && mount.button?.parentElement) {
      mount.button.insertAdjacentElement('afterend', wrapper);
    } else {
      mount.container.append(wrapper);
    }

    const setUI = (state) => {
      const { total, enabled_count, all_enabled, any_enabled } = state || {};
      input.indeterminate = Boolean(any_enabled && !all_enabled);
      input.checked = Boolean(all_enabled);
      const tail = total ? `${enabled_count}/${total}` : '0/0';
      status.textContent = input.indeterminate
        ? `Смешанный режим: включено ${tail}`
        : (input.checked ? `Включено ${tail}` : `Выключено ${tail}`);
    };

    const setLoading = (loading) => {
      input.disabled = loading;
      status.setAttribute('data-loading', loading ? 'true' : 'false');
    };

    let lastState = null;
    setLoading(true);
    fetchState()
      .then((s) => { lastState = s; setUI(s); })
      .catch(() => { status.textContent = 'Не удалось получить состояние.'; })
      .finally(() => setLoading(false));

    input.addEventListener('change', async () => {
      const enabled = input.checked;
      setLoading(true);
      try {
        await setState(enabled);
        const s = await fetchState();
        lastState = s;
        setUI(s);
        window.location.reload();
      } catch (e) {
        if (lastState) setUI(lastState);
        status.textContent = 'Ошибка применения. Попробуйте ещё раз.';
      } finally {
        setLoading(false);
      }
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    if (!/\/admin\/screeners\/list\/?$/.test(window.location.pathname)) return;
    const mount = findMountPoint();
    renderToggle(mount);
  });
})();
"""
        return Response(content=js, media_type="application/javascript; charset=utf-8")

    admin = Admin(
        engine=Database.engine,
        base_url="/admin",
        templates_dir="app/admin/templates",
        auth_provider=AdminAuthProvider(),
        login_logo_url=config.admin.logo_url,
        i18n_config=I18nConfig(default_locale="ru"),
        middlewares=[Middleware(SessionMiddleware, secret_key=config.cypher_key)],
    )

    admin.add_view(SettingsModelView(model=SettingsORM, label="Скринеры", icon="fa fa-cogs"))
    admin.add_view(LogsViewerView(label="Логи", path="/logs", icon="fa fa-book"))
    admin.add_view(MetrCustomView(label="Система", path="/monitoring", icon="fa fa-heartbeat"))

    admin.mount_to(app)