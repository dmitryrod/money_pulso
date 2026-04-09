"""Настройка админ-панели и регистрация представлений."""

__all__ = [
    "register_admin_routes",
]

import asyncio
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import func, select, update
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from starlette_admin import I18nConfig
from starlette_admin.contrib.sqla import Admin

from app.config import config
from app.database import Database, SettingsORM, SignalORM
from app.test_signal_broadcast import (
    register_test_stream_subscriber,
    unregister_test_stream_subscriber,
)
from app.utils.coinmarketcap_rank import get_cmc_rank_for_symbol

from .auth import AdminAuthProvider
from .view import LogsViewerView, MetrCustomView, SettingsModelView, SignalsView

_SIGNALS_LOG_PATH = Path(__file__).resolve().parents[1] / "logs" / "signals_log.txt"


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

    # ──────────────────────────────────────────────────────────────────────────
    # Signals API
    # ──────────────────────────────────────────────────────────────────────────

    def _signal_orm_to_dict(row: SignalORM) -> dict:
        live_rank = get_cmc_rank_for_symbol(row.symbol)
        return {
            "id": row.id,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "screener_name": row.screener_name,
            "screener_id": row.screener_id,
            "exchange": row.exchange,
            "market_type": row.market_type,
            "symbol": row.symbol,
            "telegram_text": row.telegram_text,
            "telegram_ok": row.telegram_ok,
            "error": row.error,
            "cmc_rank": live_rank,
        }

    def _parse_log_line(line: str) -> dict | None:
        """Парсит строку из signals_log.txt. Возвращает dict или None если не сигнал."""
        line = line.strip()
        if not line:
            return None
        try:
            tab_idx = line.index("\t")
            ts = line[:tab_idx]
            payload = json.loads(line[tab_idx + 1:])
        except (ValueError, json.JSONDecodeError):
            return None
        if payload.get("kind") != "signal":
            return None
        symbol = payload.get("symbol", "")
        live_rank = get_cmc_rank_for_symbol(symbol)
        return {
            "id": ts,
            "created_at": payload.get("ts_moscow") or ts,
            "screener_name": payload.get("screener_name", ""),
            "screener_id": payload.get("screener_id", 0),
            "exchange": payload.get("exchange", ""),
            "market_type": payload.get("market_type", ""),
            "symbol": symbol,
            "telegram_text": payload.get("telegram_text", "").replace("\\n", "\n"),
            "telegram_ok": bool(payload.get("telegram_ok", False)),
            "error": payload.get("error"),
            "cmc_rank": live_rank,
        }

    def _read_file_signals() -> list[dict]:
        """Читает все сигналы из signals_log.txt. Новые — в начале."""
        if not _SIGNALS_LOG_PATH.exists():
            return []
        items: list[dict] = []
        try:
            with _SIGNALS_LOG_PATH.open("r", encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    parsed = _parse_log_line(line)
                    if parsed:
                        items.append(parsed)
        except OSError:
            return []
        items.reverse()
        return items

    @app.get("/admin_api/signals")
    async def _get_signals(
        request: Request,
        source: str = "db",
        page: int = 1,
        per_page: int = 100,
    ) -> JSONResponse:
        page = max(1, page)
        per_page = per_page if per_page in (100, 500, 1000) else 100
        offset = (page - 1) * per_page

        if source == "file":
            all_items = await asyncio.to_thread(_read_file_signals)
            total = len(all_items)
            items = all_items[offset: offset + per_page]
            return JSONResponse({
                "items": items,
                "total": total,
                "page": page,
                "per_page": per_page,
                "pages": max(1, math.ceil(total / per_page)),
                "source": "file",
            })

        if source == "test":
            return JSONResponse({
                "items": [],
                "total": 0,
                "page": 1,
                "per_page": per_page,
                "pages": 1,
                "source": "test",
            })

        # source == "db"
        async with Database.session_context() as db:
            total_scalar = await db.session.scalar(
                select(func.count()).select_from(SignalORM)
            )
            total = int(total_scalar or 0)
            rows = (
                await db.session.execute(
                    select(SignalORM)
                    .order_by(SignalORM.id.desc())
                    .limit(per_page)
                    .offset(offset)
                )
            ).scalars().all()
        return JSONResponse({
            "items": [_signal_orm_to_dict(r) for r in rows],
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": max(1, math.ceil(total / per_page)),
            "source": "db",
        })

    @app.get("/admin_api/signals/stream")
    async def _stream_signals(
        request: Request,
        source: str = "db",
    ) -> StreamingResponse:
        """SSE-стрим новых сигналов. source=db|file|test."""

        async def _test_generator() -> AsyncGenerator[str, None]:
            q: asyncio.Queue[dict] = asyncio.Queue(maxsize=500)
            register_test_stream_subscriber(q)
            ping_counter = 0
            try:
                while True:
                    if await request.is_disconnected():
                        break
                    try:
                        item = await asyncio.wait_for(q.get(), timeout=0.3)
                        yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n"
                        continue
                    except asyncio.TimeoutError:
                        pass
                    ping_counter += 1
                    if ping_counter >= 50:
                        yield "event: ping\ndata: {}\n\n"
                        ping_counter = 0
            finally:
                unregister_test_stream_subscriber(q)

        async def _db_generator() -> AsyncGenerator[str, None]:
            last_id: int = 0
            # Получаем текущий максимальный id как стартовую точку
            async with Database.session_context() as db:
                max_id = await db.session.scalar(
                    select(func.max(SignalORM.id))
                )
                last_id = int(max_id or 0)

            ping_counter = 0
            while True:
                if await request.is_disconnected():
                    break
                try:
                    async with Database.session_context() as db:
                        rows = (
                            await db.session.execute(
                                select(SignalORM)
                                .where(SignalORM.id > last_id)
                                .order_by(SignalORM.id.asc())
                                .limit(50)
                            )
                        ).scalars().all()
                    for row in rows:
                        last_id = row.id
                        yield f"data: {json.dumps(_signal_orm_to_dict(row), ensure_ascii=False)}\n\n"
                except Exception:
                    pass
                ping_counter += 1
                if ping_counter >= 50:  # каждые ~15 сек
                    yield "event: ping\ndata: {}\n\n"
                    ping_counter = 0
                await asyncio.sleep(0.3)

        async def _file_generator() -> AsyncGenerator[str, None]:
            file_pos: int = 0
            if _SIGNALS_LOG_PATH.exists():
                file_pos = _SIGNALS_LOG_PATH.stat().st_size

            ping_counter = 0
            while True:
                if await request.is_disconnected():
                    break
                try:
                    if _SIGNALS_LOG_PATH.exists():
                        current_size = _SIGNALS_LOG_PATH.stat().st_size
                        if current_size > file_pos:
                            with _SIGNALS_LOG_PATH.open("rb") as fh:
                                fh.seek(file_pos)
                                new_bytes = fh.read(current_size - file_pos)
                            file_pos = current_size
                            for raw_line in new_bytes.decode("utf-8", errors="replace").splitlines():
                                parsed = _parse_log_line(raw_line)
                                if parsed:
                                    yield f"data: {json.dumps(parsed, ensure_ascii=False)}\n\n"
                        elif current_size < file_pos:
                            # Файл был ротирован
                            file_pos = current_size
                except Exception:
                    pass
                ping_counter += 1
                if ping_counter >= 50:
                    yield "event: ping\ndata: {}\n\n"
                    ping_counter = 0
                await asyncio.sleep(0.3)

        if source == "test":
            generator = _test_generator()
        else:
            generator = _db_generator() if source != "file" else _file_generator()
        return StreamingResponse(
            generator,
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    admin.add_view(SettingsModelView(model=SettingsORM, label="Скринеры", icon="fa fa-cogs"))
    admin.add_view(SignalsView(label="Сигналы", path="/signals", icon="fa fa-bell"))
    admin.add_view(MetrCustomView(label="Система", path="/monitoring", icon="fa fa-heartbeat"))
    admin.add_view(LogsViewerView(label="Логи", path="/logs", icon="fa fa-book"))

    admin.mount_to(app)