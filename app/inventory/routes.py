"""Inventario y transferencias."""

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from flask_wtf import FlaskForm
from wtforms import SelectField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Optional

from app.extensions import db
from app.models import Branch, Item, ItemMovement, Transfer
from app.inventory import inventory_bp
from app.services.audit_service import log_action
from app.utils.decorators import permission_required
from app.utils.datetime_utils import utc_now
from app.utils.money import to_decimal, ZERO


class TransferForm(FlaskForm):
    item_id = SelectField("Artículo", coerce=int, validators=[DataRequired()])
    to_branch_id = SelectField("Sucursal destino", coerce=int, validators=[DataRequired()])
    notes = TextAreaField("Observaciones", validators=[Optional()])
    submit = SubmitField("Transferir")


@inventory_bp.route("/")
@login_required
@permission_required("inventory.view", "inventory.manage")
def index():
    status = (request.args.get("status") or "").strip()
    query = Item.query.filter_by(is_deleted=False)
    if not current_user.has_role("superadmin", "auditor"):
        query = query.filter_by(branch_id=current_user.branch_id)
    if status:
        query = query.filter_by(status=status)
    items = query.order_by(Item.created_at.desc()).limit(300).all()
    invested = sum((to_decimal(i.purchase_price or i.loan_amount or 0) for i in items), ZERO)
    potential = sum((to_decimal(i.sale_price or i.estimated_value or 0) for i in items), ZERO)
    return render_template(
        "inventory/index.html",
        title="Inventario",
        items=items,
        status=status,
        invested=invested,
        potential=potential,
    )


@inventory_bp.route("/transfers", methods=["GET", "POST"])
@login_required
@permission_required("inventory.manage")
def transfers():
    form = TransferForm()
    form.item_id.choices = [(0, "—")] + [
        (i.id, f"{i.code} · {i.branch.name if i.branch else ''}")
        for i in Item.query.filter_by(is_deleted=False).limit(300)
    ]
    form.to_branch_id.choices = [(0, "—")] + [
        (b.id, b.name) for b in Branch.query.filter_by(is_deleted=False, is_active=True).all()
    ]
    if form.validate_on_submit() and form.item_id.data and form.to_branch_id.data:
        item = db.session.get(Item, form.item_id.data)
        if item is None:
            flash("Artículo no válido.", "danger")
        else:
            transfer = Transfer(
                item_id=item.id,
                from_branch_id=item.branch_id,
                to_branch_id=form.to_branch_id.data,
                notes=form.notes.data,
                sent_by_id=current_user.id,
                status="recibido",
                received_by_id=current_user.id,
                received_at=utc_now(),
            )
            old = item.status
            item.branch_id = form.to_branch_id.data
            item.status = "transferido"
            db.session.add(transfer)
            db.session.add(
                ItemMovement(
                    item_id=item.id,
                    movement_type="transferencia",
                    from_status=old,
                    to_status="transferido",
                    notes=form.notes.data,
                    user_id=current_user.id,
                    branch_id=form.to_branch_id.data,
                )
            )
            log_action(
                action="transfer",
                module="inventory",
                record_type="transfer",
                record_id=item.id,
                new_value={"to_branch_id": form.to_branch_id.data},
            )
            db.session.commit()
            flash("Transferencia registrada.", "success")
            return redirect(url_for("inventory.transfers"))
    rows = Transfer.query.order_by(Transfer.sent_at.desc()).limit(100).all()
    return render_template("inventory/transfers.html", title="Transferencias", form=form, transfers=rows)