"""Timeline entries for ``tracking_sessions`` in admin analytics."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.database.models import TrackingSessionORM

ANALYTICS_RECENT_TAIL_LIMIT = 1000
ANALYTICS_DELETED_RETENTION = 50
_EPOCH_UTC = datetime.min.replace(tzinfo=timezone.utc)


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
    """Build timeline for analytics table: ``start``, optional ``triggered``, final status.

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

    trigger_iso = _iso(row.triggered_at)
    if trigger_iso and row.status != "triggered":
        items.append({"label": "triggered", "at": trigger_iso})

    final_iso = _iso(_final_timestamp(row))
    if final_iso and row.status:
        if not (row.status == "triggered" and trigger_iso):
            items.append({"label": row.status, "at": final_iso})

    return items


def analytics_category(status: str) -> str:
    """UI pill category for analytics table."""
    if status in ("triggered", "active", "posttracking"):
        return "active"
    if status in ("completed", "closed"):
        return "completed"
    return "other"


def analytics_session_activity_at(row: TrackingSessionORM) -> datetime:
    """Latest meaningful timestamp for analytics catalog sort order."""
    candidates = (
        row.completed_at,
        row.triggered_at,
        row.closed_at,
        row.updated_at,
        row.created_at,
    )
    present = [dt for dt in candidates if dt is not None]
    return max(present) if present else _EPOCH_UTC


def merge_analytics_session_catalog(
    triggered_rows: list[TrackingSessionORM],
    active_tail_rows: list[TrackingSessionORM],
    deleted_tail_rows: list[TrackingSessionORM] | None = None,
) -> list[TrackingSessionORM]:
    """Triggered sessions plus capped never-triggered tails, deduped and sorted.

    Args:
        triggered_rows: Rows with ``triggered_at`` set (always shown in catalog).
        active_tail_rows: Recent rows without trigger and without ``deleted`` status.
        deleted_tail_rows: Newest tombstone ``deleted`` rows (capped server-side).

    Returns:
        Merged list sorted by ``analytics_session_activity_at`` descending.
    """
    seen: set[str] = set()
    merged: list[TrackingSessionORM] = []
    for row in triggered_rows:
        tid = row.tracking_id
        if tid in seen:
            continue
        seen.add(tid)
        merged.append(row)
    for row in active_tail_rows:
        tid = row.tracking_id
        if tid in seen:
            continue
        seen.add(tid)
        merged.append(row)
    for row in deleted_tail_rows or ():
        tid = row.tracking_id
        if tid in seen:
            continue
        seen.add(tid)
        merged.append(row)
    merged.sort(
        key=lambda row: (
            0 if row.triggered_at is not None else 1,
            -analytics_session_activity_at(row).timestamp(),
        ),
    )
    return merged


def build_session_events(
    jsonl_rows: list[dict[str, Any]],
    row: TrackingSessionORM | None = None,
) -> list[dict[str, str]]:
    """Chronological status events for Stat page (JSONL + DB backfill for legacy rows).

    Args:
        jsonl_rows: Lines from statistics JSONL.
        row: Optional ORM row for missing single-shot timestamps on old sessions.

    Returns:
        Sorted list of ``{"ts": iso8601, "event": str}``.
    """
    events: list[dict[str, str]] = []

    for r in jsonl_rows:
        if not isinstance(r, dict):
            continue
        kind = r.get("kind")
        if kind == "event":
            ev = str(r.get("event") or "").strip()
            if not ev:
                continue
            if ev == "start" and any(e["event"] == "start" for e in events):
                continue
            events.append({"ts": str(r.get("ts") or ""), "event": ev})
        elif kind == "session_meta":
            if any(e["event"] == "start" for e in events):
                continue
            ts = str(r.get("entered_scanner_at") or r.get("ts") or "")
            events.append({"ts": ts, "event": "start"})

    if row is not None:
        seen_labels = {e["event"] for e in events}

        def _add_if_missing(label: str, dt: datetime | None) -> None:
            if dt is None or label in seen_labels:
                return
            events.append({"ts": dt.isoformat(), "event": label})
            seen_labels.add(label)

        _add_if_missing("start", row.entered_scanner_at or row.created_at)
        if row.status == "deleted":
            _add_if_missing("deleted", row.closed_at)
        else:
            _add_if_missing("triggered", row.triggered_at)
            if row.status == "completed":
                _add_if_missing("completed", row.completed_at)
            elif row.status == "closed":
                _add_if_missing("closed", row.closed_at)

    events.sort(key=lambda e: e.get("ts") or "")
    return events
