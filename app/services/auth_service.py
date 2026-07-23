"""Servicio de autenticación."""

from __future__ import annotations

import secrets
from datetime import timedelta

from flask import current_app, has_request_context, request
from flask_login import login_user, logout_user

from app.extensions import db
from app.models import LoginLog, User
from app.services.audit_service import log_action
from app.utils.datetime_utils import utc_now


def _client_meta() -> tuple[str | None, str | None]:
    if not has_request_context():
        return None, None
    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    ua = (request.headers.get("User-Agent") or "")[:255]
    return ip, ua


def record_login_attempt(
    *,
    username: str,
    success: bool,
    user: User | None = None,
    message: str | None = None,
) -> LoginLog:
    ip, ua = _client_meta()
    entry = LoginLog(
        user_id=user.id if user else None,
        username_attempted=username,
        success=success,
        ip_address=ip,
        user_agent=ua,
        message=message,
    )
    db.session.add(entry)
    return entry


def authenticate(username: str, password: str, remember: bool = False) -> tuple[bool, str, User | None]:
    username = (username or "").strip()
    user = User.query.filter(
        (User.username == username) | (User.email == username),
        User.is_deleted.is_(False),
    ).first()

    max_attempts = current_app.config["LOGIN_MAX_ATTEMPTS"]
    lockout_minutes = current_app.config["LOGIN_LOCKOUT_MINUTES"]

    if user is None:
        record_login_attempt(username=username, success=False, message="Usuario no encontrado")
        db.session.commit()
        return False, "Usuario o contraseña incorrectos.", None

    if not user.account_active:
        record_login_attempt(
            username=username, success=False, user=user, message="Cuenta inactiva"
        )
        db.session.commit()
        return False, "La cuenta está inactiva. Contacte al administrador.", user

    if user.is_locked:
        record_login_attempt(
            username=username, success=False, user=user, message="Cuenta bloqueada"
        )
        db.session.commit()
        return (
            False,
            "La cuenta está temporalmente bloqueada por intentos fallidos.",
            user,
        )

    if not user.check_password(password):
        user.register_failed_login(max_attempts, lockout_minutes)
        record_login_attempt(
            username=username, success=False, user=user, message="Contraseña incorrecta"
        )
        log_action(
            action="login_failed",
            module="auth",
            record_type="user",
            record_id=user.id,
            user_id=user.id,
            role_code=user.role.code if user.role else None,
            reason="Contraseña incorrecta",
        )
        db.session.commit()
        if user.is_locked:
            return False, "Cuenta bloqueada por demasiados intentos fallidos.", user
        return False, "Usuario o contraseña incorrectos.", user

    user.clear_failed_logins()
    ip, _ = _client_meta()
    user.last_login_at = utc_now()
    user.last_login_ip = ip
    login_user(user, remember=remember)
    record_login_attempt(username=username, success=True, user=user, message="OK")
    log_action(
        action="login",
        module="auth",
        record_type="user",
        record_id=user.id,
        user_id=user.id,
        role_code=user.role.code if user.role else None,
    )
    db.session.commit()
    return True, "Sesión iniciada correctamente.", user


def logout_current_user() -> None:
    if has_request_context():
        from flask_login import current_user

        if current_user.is_authenticated:
            log_action(
                action="logout",
                module="auth",
                record_type="user",
                record_id=current_user.id,
            )
            db.session.commit()
    logout_user()


def create_password_reset_token(user: User, hours_valid: int = 2) -> str:
    token = secrets.token_urlsafe(32)
    user.password_reset_token = token
    user.password_reset_expires = utc_now() + timedelta(hours=hours_valid)
    db.session.commit()
    log_action(
        action="password_reset_requested",
        module="auth",
        record_type="user",
        record_id=user.id,
        user_id=user.id,
    )
    db.session.commit()
    return token


def reset_password_with_token(token: str, new_password: str) -> tuple[bool, str]:
    user = User.query.filter_by(password_reset_token=token, is_deleted=False).first()
    if user is None or user.password_reset_expires is None:
        return False, "El enlace de recuperación no es válido."
    if user.password_reset_expires < utc_now():
        return False, "El enlace de recuperación ha expirado."
    user.set_password(new_password)
    user.password_reset_token = None
    user.password_reset_expires = None
    user.must_change_password = False
    user.clear_failed_logins()
    log_action(
        action="password_reset",
        module="auth",
        record_type="user",
        record_id=user.id,
        user_id=user.id,
    )
    db.session.commit()
    return True, "Contraseña actualizada correctamente."