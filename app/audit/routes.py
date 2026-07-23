"""Rutas de auditoría."""

from flask import render_template, request
from flask_login import login_required

from app.audit import audit_bp
from app.models import AuditLog, LoginLog
from app.utils.decorators import permission_required


@audit_bp.route("/")
@login_required
@permission_required("audit.view")
def index():
    page = request.args.get("page", 1, type=int)
    module = (request.args.get("module") or "").strip()
    query = AuditLog.query
    if module:
        query = query.filter(AuditLog.module == module)
    pagination = query.order_by(AuditLog.created_at.desc()).paginate(
        page=page, per_page=25, error_out=False
    )
    return render_template(
        "audit/index.html",
        title="Auditoría",
        pagination=pagination,
        module=module,
    )


@audit_bp.route("/logins")
@login_required
@permission_required("audit.view")
def logins():
    page = request.args.get("page", 1, type=int)
    pagination = LoginLog.query.order_by(LoginLog.created_at.desc()).paginate(
        page=page, per_page=25, error_out=False
    )
    return render_template(
        "audit/logins.html",
        title="Historial de acceso",
        pagination=pagination,
    )