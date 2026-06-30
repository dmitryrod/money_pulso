"""ACL и confirm-токен для POST /admin_api/analytics/purge."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from starlette.testclient import TestClient

from app.__main__ import app
from app.admin.roles import ROLE_ADMIN, SESSION_ROLE_KEY


@pytest.fixture
def admin_client() -> TestClient:
    client = TestClient(app)
    with client.session_transaction() as sess:
        sess[SESSION_ROLE_KEY] = ROLE_ADMIN
        sess["username"] = "root"
    return client


def test_analytics_purge_requires_admin_session() -> None:
    client = TestClient(app)
    r = client.post("/admin_api/analytics/purge?confirm=purge-all-statistics")
    assert r.status_code == 401


def test_analytics_purge_requires_confirm_token(admin_client: TestClient) -> None:
    r = admin_client.post("/admin_api/analytics/purge?confirm=wrong")
    assert r.status_code == 400


@patch("app.admin.__init__.purge_statistics_data_files", return_value=0)
@patch("app.admin.__init__.scanner_runtime")
def test_analytics_purge_ok_with_admin_and_confirm(
    _runtime: object,
    _purge_files: object,
    admin_client: TestClient,
) -> None:
    mock_db = AsyncMock()
    mock_db.session.scalar = AsyncMock(return_value=3)
    mock_db.session.execute = AsyncMock()
    mock_db.commit = AsyncMock()

    with patch("app.admin.__init__.Database.session_context") as ctx:
        ctx.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        ctx.return_value.__aexit__ = AsyncMock(return_value=None)
        r = admin_client.post(
            "/admin_api/analytics/purge?confirm=purge-all-statistics"
        )

    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["tracking_sessions_deleted"] == 3
