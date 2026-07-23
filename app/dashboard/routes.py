"""Rutas del dashboard."""

from flask import render_template, request
from flask_login import current_user, login_required

from app.dashboard import dashboard_bp
from app.models import (
    AuditLog,
    Branch,
    Customer,
    DirectPurchase,
    Item,
    PawnContract,
    PawnPayment,
    Sale,
    User,
)
from app.services.cash_service import get_open_session, session_balance
from app.services.pawn_service import update_expiration_statuses
from app.utils.decorators import permission_required
from app.utils.datetime_utils import ensure_aware, local_now
from app.utils.money import ZERO, format_money, to_decimal


def _is_local_today(dt) -> bool:
    """Compara fechas en zona America/Santo_Domingo (no UTC crudo)."""
    local_dt = ensure_aware(dt)
    return bool(local_dt and local_dt.date() == local_now().date())


@dashboard_bp.route("/")
@login_required
@permission_required("dashboard.view")
def index():
    update_expiration_statuses()
    today = local_now().date()
    branch_id = None if current_user.has_role("superadmin", "auditor") else current_user.branch_id

    def scope(query, model):
        if branch_id is not None and hasattr(model, "branch_id"):
            return query.filter(model.branch_id == branch_id)
        return query

    contracts_today = scope(PawnContract.query.filter_by(is_deleted=False), PawnContract).all()
    capital_today = sum(
        (to_decimal(c.capital) for c in contracts_today if c.start_date == today),
        ZERO,
    )
    payments_q = PawnPayment.query.filter_by(is_voided=False)
    if hasattr(PawnPayment, "is_deleted"):
        payments_q = payments_q.filter_by(is_deleted=False)
    payments_today = [
        p for p in scope(payments_q, PawnPayment).all() if _is_local_today(p.paid_at)
    ]
    interest_today = sum((to_decimal(p.amount) for p in payments_today), ZERO)
    sales_today = sum(
        (
            to_decimal(s.total)
            for s in scope(Sale.query.filter_by(is_deleted=False), Sale).all()
            if _is_local_today(s.sold_at)
        ),
        ZERO,
    )
    purchases_today = sum(
        (
            to_decimal(p.paid_price)
            for p in scope(DirectPurchase.query.filter_by(is_deleted=False), DirectPurchase).all()
            if _is_local_today(p.purchased_at)
        ),
        ZERO,
    )
    active_contracts = scope(
        PawnContract.query.filter(
            PawnContract.is_deleted.is_(False),
            PawnContract.status.in_(["activo", "renovado", "proximo_vencer"]),
        ),
        PawnContract,
    ).count()
    expired_count = scope(
        PawnContract.query.filter(
            PawnContract.is_deleted.is_(False),
            PawnContract.status.in_(["vencido", "en_periodo_gracia", "pendiente_autorizacion"]),
        ),
        PawnContract,
    ).count()
    available_items = scope(
        Item.query.filter(
            Item.is_deleted.is_(False),
            Item.status.in_(["disponible_venta", "autorizado_inventario"]),
        ),
        Item,
    ).count()
    cash_value = ZERO
    if current_user.branch_id:
        session = get_open_session(current_user.branch_id)
        if session:
            cash_value = session_balance(session)

    cards = [
        {"title": "Capital prestado hoy", "value": format_money(capital_today), "hint": "Empeños del día", "tone": "primary"},
        {"title": "Cobrado hoy", "value": format_money(interest_today), "hint": "Pagos recibidos", "tone": "success"},
        {"title": "Ventas de hoy", "value": format_money(sales_today), "hint": "Facturación", "tone": "info"},
        {"title": "Compras de hoy", "value": format_money(purchases_today), "hint": "Compras directas", "tone": "warning"},
        {"title": "Caja disponible", "value": format_money(cash_value), "hint": "Sesión abierta", "tone": "gold"},
        {"title": "Contratos activos", "value": str(active_contracts), "hint": "En vigor", "tone": "primary"},
        {"title": "Vencidos / gracia", "value": str(expired_count), "hint": "Requieren atención", "tone": "warning"},
        {"title": "Disponibles venta", "value": str(available_items), "hint": "Inventario", "tone": "secondary"},
        {"title": "Clientes", "value": str(Customer.query.filter_by(is_deleted=False).count()), "hint": "Base", "tone": "secondary"},
        {"title": "Sucursales", "value": str(Branch.query.filter_by(is_deleted=False, is_active=True).count()), "hint": "Red", "tone": "secondary"},
        {"title": "Usuarios", "value": str(User.query.filter_by(is_deleted=False, account_active=True).count()), "hint": "Equipo", "tone": "secondary"},
        {"title": "Ganancia hoy (est.)", "value": format_money(interest_today + sales_today - purchases_today), "hint": "Estimación operativa", "tone": "success"},
    ]

    alerts = []
    if expired_count:
        alerts.append({"level": "danger", "text": f"Hay {expired_count} contratos vencidos o en gracia."})
    if current_user.branch_id and not get_open_session(current_user.branch_id):
        alerts.append({"level": "warning", "text": "No hay caja abierta en su sucursal."})
    if not alerts:
        alerts.append({"level": "success", "text": "Sistema operativo. Moneda RD$ · zona America/Santo_Domingo."})

    return render_template(
        "dashboard/index.html",
        title="Panel principal",
        cards=cards,
        alerts=alerts,
    )


@dashboard_bp.route("/actividad")
@login_required
@permission_required("dashboard.view")
def activity():
    page = request.args.get("page", 1, type=int)
    pagination = AuditLog.query.order_by(AuditLog.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    return render_template(
        "dashboard/activity.html",
        title="Actividad reciente",
        recent_audits=pagination.items,
        pagination=pagination,
    )