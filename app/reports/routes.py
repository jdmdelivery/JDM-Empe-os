"""Reportes y exportaciones básicas."""

import csv
import io
from datetime import datetime

from flask import Response, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from openpyxl import Workbook

from app.models import (
    Customer,
    DirectPurchase,
    Expense,
    Item,
    PawnContract,
    PawnPayment,
    Sale,
)
from app.reports import reports_bp
from app.services.notification_service import queue_due_reminders
from app.services.pawn_service import update_expiration_statuses
from app.utils.decorators import permission_required
from app.utils.money import ZERO, money_add, money_sub, to_decimal


@reports_bp.route("/")
@login_required
@permission_required("reports.view", "reports.global")
def index():
    update_expiration_statuses()
    branch_id = None if current_user.has_role("superadmin", "auditor") else current_user.branch_id

    def scoped(query, model):
        if branch_id and hasattr(model, "branch_id"):
            return query.filter(model.branch_id == branch_id)
        return query

    contracts = scoped(PawnContract.query.filter_by(is_deleted=False), PawnContract).all()
    payments = scoped(PawnPayment.query.filter_by(is_deleted=False, is_voided=False), PawnPayment).all()
    sales = scoped(Sale.query.filter_by(is_deleted=False), Sale).all()
    purchases = scoped(DirectPurchase.query.filter_by(is_deleted=False), DirectPurchase).all()
    items = scoped(Item.query.filter_by(is_deleted=False), Item).all()
    expenses = scoped(Expense.query.filter_by(is_deleted=False, entry_type="gasto"), Expense).all()

    capital_loaned = sum((to_decimal(c.capital) for c in contracts), ZERO)
    interest_collected = sum((to_decimal(p.amount) for p in payments), ZERO)
    sales_total = sum((to_decimal(s.total) for s in sales), ZERO)
    purchases_total = sum((to_decimal(p.paid_price) for p in purchases), ZERO)
    expenses_total = sum((to_decimal(e.amount) for e in expenses), ZERO)
    active = [c for c in contracts if c.status in {"activo", "renovado", "proximo_vencer"}]
    expired = [c for c in contracts if c.status in {"vencido", "en_periodo_gracia", "pendiente_autorizacion"}]
    available = [i for i in items if i.status in {"disponible_venta", "autorizado_inventario"}]

    summary = {
        "capital_loaned": capital_loaned,
        "interest_collected": interest_collected,
        "sales_total": sales_total,
        "purchases_total": purchases_total,
        "expenses_total": expenses_total,
        "profit_estimate": money_sub(
            money_sub(money_add(interest_collected, sales_total), purchases_total),
            expenses_total,
        ),
        "active_contracts": len(active),
        "expired_contracts": len(expired),
        "available_items": len(available),
        "customers": Customer.query.filter_by(is_deleted=False).count(),
    }
    return render_template("reports/index.html", title="Reportes", summary=summary)


@reports_bp.route("/export.csv")
@login_required
@permission_required("reports.view", "reports.global")
def export_csv():
    kind = request.args.get("kind", "payments")
    output = io.StringIO()
    writer = csv.writer(output)
    if kind == "payments":
        writer.writerow(["recibo", "contrato", "monto", "metodo", "fecha"])
        for p in PawnPayment.query.filter_by(is_voided=False).limit(1000):
            writer.writerow(
                [
                    p.receipt_number,
                    p.contract.contract_number if p.contract else "",
                    str(p.amount),
                    p.method,
                    p.paid_at.isoformat() if p.paid_at else "",
                ]
            )
    elif kind == "sales":
        writer.writerow(["factura", "total", "metodo", "fecha"])
        for s in Sale.query.filter_by(is_deleted=False).limit(1000):
            writer.writerow([s.invoice_number, str(s.total), s.payment_method, s.sold_at.isoformat()])
    else:
        writer.writerow(["contrato", "cliente", "capital", "estado", "vencimiento"])
        for c in PawnContract.query.filter_by(is_deleted=False).limit(1000):
            writer.writerow(
                [
                    c.contract_number,
                    c.customer.full_name if c.customer else "",
                    str(c.capital),
                    c.status,
                    str(c.due_date),
                ]
            )
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=reporte_{kind}.csv"},
    )


@reports_bp.route("/notify-due", methods=["POST"])
@login_required
@permission_required("reports.view", "reports.global")
def notify_due():
    results = queue_due_reminders()
    if results and results[0].get("status") == "disabled":
        flash(results[0]["message"], "warning")
    else:
        flash(f"Recordatorios encolados: {len(results)}", "success")
    return redirect(url_for("reports.index"))


@reports_bp.route("/export.xlsx")
@login_required
@permission_required("reports.view", "reports.global")
def export_xlsx():
    wb = Workbook()
    ws = wb.active
    ws.title = "Pagos"
    ws.append(["Recibo", "Contrato", "Monto", "Método", "Fecha"])
    for p in PawnPayment.query.filter_by(is_voided=False).limit(1000):
        ws.append(
            [
                p.receipt_number,
                p.contract.contract_number if p.contract else "",
                float(p.amount),
                p.method,
                p.paid_at.isoformat() if p.paid_at else "",
            ]
        )
    bio = io.BytesIO()
    wb.save(bio)
    return Response(
        bio.getvalue(),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=reporte_pagos.xlsx"},
    )