"""Timeline entries for ``tracking_sessions`` in admin analytics."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.database.models import TrackingSessionORM


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.isoformat()


def _final_timestamp(row: TrackingSessionORM) -> datetime | None:
    """Timestamp for the second timeline row (current/final status)."""
    status = row.status
    if status == "deleted":
        return row.closed_at
    if status == "triggered":
        return row.triggered_at
    if status == "completed":
        return row.completed_at
    if status == "closed":
        return row.closed_at
    return row.updated_at or row.triggered_at or row.created_at


def build_tracking_timeline(row: TrackingSessionORM) -> list[dict[str, str]]:
    """Build timeline: ``start`` plus current/final status (max 2 rows).

    Args:
        row: ORM row from ``tracking_sessions``.

    Returns:
        List of ``{"label": str, "at": iso8601}`` entries.
    """
    items: list[dict[str, str]] = []
    start_at = row.entered_scanner_at or row.created_at
    start_iso = _iso(start_at)
    if start_iso:
        items.append({"label": "start", "at": start_iso})

    if row.status == "deleted":
        deleted_iso = _iso(row.closed_at)
        if deleted_iso:
            items.append({"label": "deleted", "at": deleted_iso})
        return items

    final_iso = _iso(_final_timestamp(row))
    if final_iso and row.status:
        items.append({"label": row.status, "at": final_iso})

    return items


def analytics_category(status: str) -> str:
    """UI pill category for analytics table."""
    if status in ("triggered", "active", "posttracking"):
        return "active"
    if status in ("completed", "closed"):
        return "completed"
    return "other"
