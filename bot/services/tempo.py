"""Utilitários de tempo no fuso do projeto (`America/Belem`)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

_FORMATO_TS = "%Y%m%d_%H%M%S"


def fuso_belem():
    """Fuso `America/Belem`; usa offset fixo -03:00 se o tzdata não estiver disponível."""
    try:
        from zoneinfo import ZoneInfo

        return ZoneInfo("America/Belem")
    except Exception:  # pragma: no cover - fallback defensivo
        return timezone(timedelta(hours=-3))


def _momento(agora: datetime | None = None) -> datetime:
    fuso = fuso_belem()
    return agora.astimezone(fuso) if agora is not None else datetime.now(fuso)


def timestamp_belem(agora: datetime | None = None) -> str:
    """Timestamp `YYYYMMDD_HHMMSS` no fuso `America/Belem`."""
    return _momento(agora).strftime(_FORMATO_TS)


def agora_iso(agora: datetime | None = None) -> str:
    """Instante atual em ISO 8601 no fuso `America/Belem`."""
    return _momento(agora).isoformat()
