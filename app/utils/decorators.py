"""Decoradores de autorización."""

from __future__ import annotations

from functools import wraps
from typing import Any, Callable

from flask import abort, flash, redirect, request, url_for
from flask_login import current_user


def permission_required(*permissions: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Exige al menos uno de los permisos indicados (validación backend)."""

    def decorator(view: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(view)
        def wrapped(*args: Any, **kwargs: Any):
            if not current_user.is_authenticated:
                return redirect(url_for("auth.login", next=request.path))
            if not current_user.has_any_permission(*permissions):
                flash("No tiene permisos para realizar esta acción.", "danger")
                abort(403)
            return view(*args, **kwargs)

        return wrapped

    return decorator


def role_required(*role_codes: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(view: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(view)
        def wrapped(*args: Any, **kwargs: Any):
            if not current_user.is_authenticated:
                return redirect(url_for("auth.login", next=request.path))
            if current_user.role is None or current_user.role.code not in role_codes:
                flash("No tiene el rol necesario para esta acción.", "danger")
                abort(403)
            return view(*args, **kwargs)

        return wrapped

    return decorator


def active_user_required(view: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(view)
    def wrapped(*args: Any, **kwargs: Any):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login", next=request.path))
        if not current_user.is_active_user:
            flash("Su cuenta está inactiva o bloqueada.", "danger")
            return redirect(url_for("auth.logout"))
        return view(*args, **kwargs)

    return wrapped