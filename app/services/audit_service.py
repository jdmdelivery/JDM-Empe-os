"""Servicio de auditoría."""

from __future__ import annotations

import json
from typing import Any

from flask import has_request_context, request
from flask_login import current_user

from app.extensions import db
from app.models import AuditLog


def _serialize(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False, default=str)
    except TypeError:
        return str(value)


def log_action(
    *,
    action: str,
    module: str,
    record_type: str | None = None,
    record_id: str | int | None = None,
    old_value: Any = None,
    new_value: Any = None,
    reason: str | None = None,
    user_id: int | None = None,
    role_code: str | None = None,
) -> AuditLog:
    ip_address = None
    user_agent = None
    if has_request_context():
        ip_address = request.headers.get("X-Forwarded-For", request.remote_addr)
        user_agent = request.headers.get("User-Agent", "")[:255]
        if user_id is None and current_user.is_authenticated:
            user_id = current_user.id
            role_code = role_code or (
                current_user.role.code if current_user.role else None
            )

    entry = AuditLog(
        user_id=user_id,
        role_code=role_code,
        action=action,
        module=module,
        record_type=record_type,
        record_id=str(record_id) if record_id is not None else None,
        old_value=_serialize(old_value),
        new_value=_serialize(new_value),
        reason=reason,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.session.add(entry)
    return entry