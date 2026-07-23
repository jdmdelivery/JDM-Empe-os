"""Rutas de autenticación."""

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.auth import auth_bp
from app.extensions import db, limiter
from app.forms.auth_forms import ForgotPasswordForm, LoginForm, ResetPasswordForm
from app.models import User
from app.services.auth_service import (
    authenticate,
    create_password_reset_token,
    logout_current_user,
    reset_password_with_token,
)


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    form = LoginForm()
    if form.validate_on_submit():
        ok, message, _user = authenticate(
            form.username.data or "",
            form.password.data or "",
            remember=bool(form.remember.data),
        )
        if ok:
            flash(message, "success")
            next_url = request.args.get("next")
            if next_url and next_url.startswith("/"):
                return redirect(next_url)
            return redirect(url_for("dashboard.index"))
        flash(message, "danger")
    return render_template("auth/login.html", form=form, title="Iniciar sesión")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_current_user()
    flash("Sesión cerrada correctamente.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def forgot_password():
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data, is_deleted=False).first()
        # Mensaje genérico para no revelar existencia de cuentas.
        if user and user.account_active:
            token = create_password_reset_token(user)
            reset_url = url_for("auth.reset_password", token=token, _external=True)
            flash(
                "Si el correo existe, se generó un enlace de recuperación. "
                f"En desarrollo: {reset_url}",
                "info",
            )
        else:
            flash(
                "Si el correo existe en el sistema, recibirá instrucciones de recuperación.",
                "info",
            )
        return redirect(url_for("auth.login"))
    return render_template("auth/forgot_password.html", form=form, title="Recuperar contraseña")


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def reset_password(token: str):
    form = ResetPasswordForm()
    if form.validate_on_submit():
        ok, message = reset_password_with_token(token, form.password.data or "")
        flash(message, "success" if ok else "danger")
        if ok:
            return redirect(url_for("auth.login"))
    return render_template(
        "auth/reset_password.html", form=form, title="Restablecer contraseña", token=token
    )