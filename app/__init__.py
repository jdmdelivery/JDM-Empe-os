"""Factory de la aplicación JDM Empeños."""

from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, abort, redirect, render_template, request, send_from_directory, session, url_for
from flask_login import current_user, login_required

from app.config import get_config
from app.extensions import csrf, db, limiter, login_manager, migrate
from app.utils.datetime_utils import format_date, format_datetime, local_now, utc_now
from app.utils.money import format_money
from app.utils.security_headers import register_security_headers


def create_app(config_name: str | None = None) -> Flask:
    app = Flask(
        __name__,
        instance_relative_config=True,
        template_folder="templates",
        static_folder="static",
    )

    config_cls = get_config(config_name)
    app.config.from_object(config_cls)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)

    _register_extensions(app)
    _register_blueprints(app)
    _register_context(app)
    _register_hooks(app)
    _register_error_handlers(app)
    register_security_headers(app)

    # En producción, asegurar esquema y admin aunque falle el Start Command
    if (config_name or os.getenv("FLASK_ENV") or "").lower() == "production":
        try:
            from app.services.bootstrap_service import bootstrap_database

            bootstrap_database(app)
        except Exception:
            app.logger.exception("Bootstrap de base de datos falló al iniciar")

    @app.route("/")
    def home():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard.index"))
        return redirect(url_for("auth.login"))

    @app.route("/healthz")
    def healthz():
        return {"status": "ok", "service": "JDM Empeños"}, 200

    @app.route("/readyz")
    def readyz():
        from sqlalchemy import text

        try:
            db.session.execute(text("SELECT 1"))
            return {"status": "ready", "database": "ok"}, 200
        except Exception as exc:
            return {"status": "not_ready", "database": str(exc.__class__.__name__)}, 503

    @app.route("/uploads/<path:filename>")
    @login_required
    def uploaded_file(filename: str):
        uploads = Path(app.config["UPLOAD_FOLDER"]).resolve()
        target = (uploads / filename).resolve()
        if not str(target).startswith(str(uploads)) or not target.exists():
            abort(404)
        return send_from_directory(uploads, filename)

    @app.route("/search")
    @login_required
    def global_search():
        from app.services.search_service import global_search as do_search

        q = (request.args.get("q") or "").strip()
        results = do_search(q) if q else {"customers": [], "deliverers": [], "articles": []}
        return render_template(
            "search/results.html",
            title="Búsqueda global",
            q=q,
            results=results,
        )

    return app


def _register_extensions(app: Flask) -> None:
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    # Importar modelos para metadata de Alembic
    from app import models  # noqa: F401


def _register_blueprints(app: Flask) -> None:
    from app.audit import audit_bp
    from app.auth import auth_bp
    from app.branches import branches_bp
    from app.cash import cash_bp
    from app.customers import customers_bp
    from app.dashboard import dashboard_bp
    from app.deliverers import deliverers_bp
    from app.expenses import expenses_bp
    from app.inventory import inventory_bp
    from app.items import items_bp
    from app.pawn import pawn_bp
    from app.payments import payments_bp
    from app.purchases import purchases_bp
    from app.renewals import renewals_bp
    from app.reports import reports_bp
    from app.sales import sales_bp
    from app.settings import settings_bp
    from app.users import users_bp

    for bp in (
        auth_bp,
        dashboard_bp,
        branches_bp,
        users_bp,
        settings_bp,
        audit_bp,
        customers_bp,
        deliverers_bp,
        items_bp,
        pawn_bp,
        payments_bp,
        renewals_bp,
        purchases_bp,
        sales_bp,
        inventory_bp,
        cash_bp,
        expenses_bp,
        reports_bp,
    ):
        app.register_blueprint(bp)

    @app.route("/expired")
    @login_required
    def expired_alias():
        return redirect(url_for("pawn.expired"))


def _register_context(app: Flask) -> None:
    @app.context_processor
    def inject_globals():
        from app.models import Setting

        symbol = app.config.get("BUSINESS_CURRENCY_SYMBOL", "RD$")
        business_name = app.config.get("APP_NAME", "JDM Empeños")
        try:
            setting_symbol = Setting.query.filter_by(key="currency_symbol").first()
            setting_name = Setting.query.filter_by(key="business_name").first()
            if setting_symbol and setting_symbol.value:
                symbol = setting_symbol.value
            if setting_name and setting_name.value:
                business_name = setting_name.value
        except Exception:
            # BD aún no inicializada
            pass

        return {
            "app_name": business_name,
            "currency_symbol": symbol,
            "format_money": format_money,
            "format_datetime": format_datetime,
            "format_date": format_date,
            "now": local_now,
        }


def _register_hooks(app: Flask) -> None:
    @app.before_request
    def enforce_session_timeout():
        if not current_user.is_authenticated:
            return None
        # Evitar timeout en assets y health
        if request.endpoint in {"static", "healthz"}:
            return None

        now = utc_now().timestamp()
        last = session.get("last_activity_at")
        timeout = app.config.get("SESSION_INACTIVITY_MINUTES", 30) * 60
        if last and (now - last) > timeout:
            from app.services.auth_service import logout_current_user

            logout_current_user()
            session.clear()
            from flask import flash

            flash("Su sesión expiró por inactividad.", "warning")
            return redirect(url_for("auth.login"))
        session["last_activity_at"] = now
        return None

    @app.before_request
    def force_password_change():
        if not current_user.is_authenticated:
            return None
        if request.endpoint in {
            "static",
            "healthz",
            "auth.logout",
            "users.change_password",
        }:
            return None
        if getattr(current_user, "must_change_password", False):
            from flask import flash

            flash("Debe cambiar su contraseña antes de continuar.", "warning")
            return redirect(url_for("users.change_password"))
        return None


def _register_error_handlers(app: Flask) -> None:
    @app.errorhandler(403)
    def forbidden(error):  # type: ignore[no-untyped-def]
        return render_template("errors/403.html", title="Acceso denegado"), 403

    @app.errorhandler(404)
    def not_found(error):  # type: ignore[no-untyped-def]
        return render_template("errors/404.html", title="No encontrado"), 404

    @app.errorhandler(500)
    def server_error(error):  # type: ignore[no-untyped-def]
        app.logger.exception("Error 500: %s", error)
        try:
            return render_template("errors/500.html", title="Error del servidor"), 500
        except Exception:
            return "Error del servidor", 500