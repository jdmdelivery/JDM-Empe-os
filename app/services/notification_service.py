"""Notificaciones (no envía hasta configurar proveedor)."""

from __future__ import annotations

from app.extensions import db
from app.models.settings import Setting


# Tabla ligera en settings/logs; modelo dedicado opcional via settings flag.


def provider_configured(channel: str) -> bool:
    mapping = {
        "whatsapp": "WHATSAPP_API_TOKEN",
        "sms": "SMS_API_TOKEN",
        "email": "SMTP_HOST",
    }
    import os

    key = mapping.get(channel)
    return bool(key and os.getenv(key))


def queue_notification(
    *,
    channel: str,
    recipient: str,
    template_code: str,
    payload: dict | None = None,
) -> dict:
    if not provider_configured(channel):
        return {
            "status": "pending_config",
            "message": (
                f"Notificación '{template_code}' no enviada: "
                f"configure el proveedor de {channel} en variables de entorno."
            ),
            "recipient": recipient,
            "payload": payload or {},
        }
    # Integración real se activa cuando existan credenciales.
    return {
        "status": "queued",
        "channel": channel,
        "recipient": recipient,
        "template_code": template_code,
        "payload": payload or {},
    }


def ensure_notification_settings() -> None:
    defaults = [
        ("notifications_enabled", "0", "Notificaciones habilitadas"),
        ("notify_before_due_days", "3", "Días de anticipación de vencimiento"),
    ]
    for key, value, label in defaults:
        if Setting.query.filter_by(key=key).first() is None:
            db.session.add(
                Setting(key=key, value=value, category="notifications", label=label)
            )
    db.session.commit()


def queue_due_reminders() -> list[dict]:
    """Encola recordatorios de contratos próximos a vencer (sin enviar si no hay proveedor)."""
    from datetime import timedelta

    from app.models import PawnContract
    from app.utils.datetime_utils import local_now

    ensure_notification_settings()
    enabled = Setting.query.filter_by(key="notifications_enabled").first()
    if not enabled or enabled.value not in {"1", "true", "True"}:
        return [{"status": "disabled", "message": "Notificaciones deshabilitadas en configuración."}]

    days_setting = Setting.query.filter_by(key="notify_before_due_days").first()
    days = int(days_setting.value) if days_setting and days_setting.value else 3
    today = local_now().date()
    limit = today + timedelta(days=days)
    queued: list[dict] = []
    contracts = PawnContract.query.filter(
        PawnContract.is_deleted.is_(False),
        PawnContract.status.in_(["activo", "renovado", "proximo_vencer"]),
        PawnContract.due_date <= limit,
        PawnContract.due_date >= today,
    ).all()
    for contract in contracts:
        phone = None
        if contract.customer and contract.customer.phone_primary:
            phone = contract.customer.phone_primary
        if not phone:
            continue
        queued.append(
            queue_notification(
                channel="whatsapp",
                recipient=phone,
                template_code="pawn_due_reminder",
                payload={
                    "contract_number": contract.contract_number,
                    "due_date": str(contract.due_date),
                    "pending_total": str(contract.pending_total),
                },
            )
        )
    return queued