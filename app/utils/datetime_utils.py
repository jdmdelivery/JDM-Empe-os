"""Utilidades de fecha y hora con zona horaria."""

from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

DEFAULT_TZ = "America/Santo_Domingo"


def get_tz(name: str | None = None) -> ZoneInfo:
    return ZoneInfo(name or DEFAULT_TZ)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def local_now(tz_name: str | None = None) -> datetime:
    return utc_now().astimezone(get_tz(tz_name))


def ensure_aware(dt: datetime | None, tz_name: str | None = None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc).astimezone(get_tz(tz_name))
    return dt.astimezone(get_tz(tz_name))


def format_datetime(dt: datetime | None, tz_name: str | None = None) -> str:
    local_dt = ensure_aware(dt, tz_name)
    if local_dt is None:
        return "—"
    return local_dt.strftime("%d/%m/%Y %H:%M")


def format_date(dt: datetime | None, tz_name: str | None = None) -> str:
    local_dt = ensure_aware(dt, tz_name)
    if local_dt is None:
        return "—"
    return local_dt.strftime("%d/%m/%Y")