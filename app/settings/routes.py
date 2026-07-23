"""Rutas de configuración."""

from decimal import Decimal

from flask import flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.forms.settings_forms import BusinessSettingsForm
from app.models import BackupRecord, Setting
from app.services.audit_service import log_action
from app.services.backup_service import create_sqlite_backup, restore_sqlite_backup
from app.services.notification_service import ensure_notification_settings, queue_notification
from app.services.seed_service import seed_default_settings
from app.settings import settings_bp
from app.utils.decorators import permission_required


def _get_setting(key: str, default: str = "") -> str:
    setting = Setting.query.filter_by(key=key).first()
    return setting.value if setting and setting.value is not None else default


def _set_setting(key: str, value: str) -> None:
    setting = Setting.query.filter_by(key=key).first()
    if setting is None:
        setting = Setting(key=key, value=value, category="general")
        db.session.add(setting)
    else:
        setting.value = value


@settings_bp.route("/", methods=["GET", "POST"])
@login_required
@permission_required("settings.view", "settings.manage")
def index():
    seed_default_settings()
    form = BusinessSettingsForm()
    can_manage = True
    from flask_login import current_user

    can_manage = current_user.has_permission("settings.manage")

    if not form.is_submitted():
        form.business_name.data = _get_setting("business_name", "JDM Empeños")
        form.business_rnc.data = _get_setting("business_rnc")
        form.business_phone.data = _get_setting("business_phone")
        form.business_whatsapp.data = _get_setting("business_whatsapp")
        form.business_email.data = _get_setting("business_email")
        form.business_address.data = _get_setting("business_address")
        form.currency_symbol.data = _get_setting("currency_symbol", "RD$")
        form.timezone.data = _get_setting("timezone", "America/Santo_Domingo")
        form.default_interest_percent.data = Decimal(_get_setting("default_interest_percent", "10"))
        form.default_grace_days.data = int(_get_setting("default_grace_days", "3"))
        form.default_duration_days.data = int(_get_setting("default_duration_days", "30"))

    if form.validate_on_submit():
        if not can_manage:
            flash("No tiene permisos para modificar la configuración.", "danger")
            return redirect(url_for("settings.index"))

        old = {
            "business_name": _get_setting("business_name"),
            "currency_symbol": _get_setting("currency_symbol"),
            "default_interest_percent": _get_setting("default_interest_percent"),
        }
        _set_setting("business_name", form.business_name.data or "JDM Empeños")
        _set_setting("business_rnc", form.business_rnc.data or "")
        _set_setting("business_phone", form.business_phone.data or "")
        _set_setting("business_whatsapp", form.business_whatsapp.data or "")
        _set_setting("business_email", form.business_email.data or "")
        _set_setting("business_address", form.business_address.data or "")
        _set_setting("currency_symbol", form.currency_symbol.data or "RD$")
        _set_setting("timezone", form.timezone.data or "America/Santo_Domingo")
        _set_setting(
            "default_interest_percent",
            str(form.default_interest_percent.data or Decimal("10")),
        )
        _set_setting("default_grace_days", str(form.default_grace_days.data or 3))
        _set_setting("default_duration_days", str(form.default_duration_days.data or 30))
        log_action(
            action="update",
            module="settings",
            record_type="settings",
            old_value=old,
            new_value={
                "business_name": form.business_name.data,
                "currency_symbol": form.currency_symbol.data,
                "default_interest_percent": str(form.default_interest_percent.data),
            },
        )
        db.session.commit()
        flash("Configuración guardada correctamente.", "success")
        return redirect(url_for("settings.index"))

    backups = (
        BackupRecord.query.order_by(BackupRecord.created_at.desc()).limit(20).all()
        if can_manage
        else []
    )
    return render_template(
        "settings/index.html",
        title="Configuración",
        form=form,
        can_manage=can_manage,
        backups=backups,
    )


@settings_bp.route("/backup", methods=["POST"])
@login_required
@permission_required("settings.manage")
def backup_now():
    ensure_notification_settings()
    try:
        record = create_sqlite_backup(user_id=current_user.id)
        notice = queue_notification(
            channel="email",
            recipient=current_user.email or "admin@example.com",
            template_code="backup_created",
            payload={"filename": record.filename, "status": record.status},
        )
        if notice.get("status") == "pending_config":
            flash(f"Respaldo creado: {record.filename}. (Aviso email pendiente de configurar SMTP)", "success")
        else:
            flash(f"Respaldo creado: {record.filename}", "success")
    except Exception as exc:  # noqa: BLE001
        flash(f"No se pudo crear el respaldo: {exc}", "danger")
    return redirect(url_for("settings.index"))


@settings_bp.route("/backup/<int:backup_id>/restore", methods=["POST"])
@login_required
@permission_required("settings.manage")
def backup_restore(backup_id: int):
    try:
        record = restore_sqlite_backup(backup_id)
        flash(
            f"Respaldo restaurado: {record.filename}. Reinicie la aplicación para continuar.",
            "warning",
        )
    except Exception as exc:  # noqa: BLE001
        flash(f"No se pudo restaurar: {exc}", "danger")
    return redirect(url_for("settings.index"))