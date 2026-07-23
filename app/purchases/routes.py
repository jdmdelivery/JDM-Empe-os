"""Compras directas."""

from flask import flash, redirect, render_template, url_for
from flask_login import current_user, login_required
from flask_wtf import FlaskForm
from wtforms import BooleanField, DecimalField, SelectField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, NumberRange, Optional

from app.extensions import db
from app.models import Customer, Deliverer, DirectPurchase, Item, ItemMovement
from app.purchases import purchases_bp
from app.services.audit_service import log_action
from app.services.cash_service import add_movement, get_open_session
from app.services.numbering import next_code
from app.utils.decorators import permission_required
from app.utils.money import to_decimal


class PurchaseForm(FlaskForm):
    customer_id = SelectField("Cliente / vendedor", coerce=int, validators=[DataRequired()])
    deliverer_id = SelectField("Persona que entrega", coerce=int, validators=[DataRequired()])
    item_id = SelectField("Artículo", coerce=int, validators=[DataRequired()])
    estimated_value = DecimalField("Valor estimado", places=2, validators=[Optional()])
    negotiated_price = DecimalField("Precio negociado", places=2, validators=[DataRequired(), NumberRange(min=0)])
    paid_price = DecimalField("Precio pagado", places=2, validators=[DataRequired(), NumberRange(min=0)])
    payment_method = SelectField(
        "Método",
        choices=[("efectivo", "Efectivo"), ("transferencia", "Transferencia"), ("cheque", "Cheque")],
        default="efectivo",
    )
    status = SelectField(
        "Estado post-compra",
        choices=[
            ("disponible_venta", "Disponible para venta"),
            ("pendiente_documentacion", "Pendiente de revisión"),
            ("en_reparacion", "Pendiente de reparación"),
            ("bloqueado", "Bloqueado"),
        ],
        default="disponible_venta",
    )
    declaration_accepted = BooleanField("Declaración de procedencia aceptada")
    observations = TextAreaField("Observaciones", validators=[Optional()])
    submit = SubmitField("Registrar compra")


@purchases_bp.route("/")
@login_required
@permission_required("purchases.view", "purchases.manage")
def index():
    query = DirectPurchase.query.filter_by(is_deleted=False)
    if not current_user.has_role("superadmin", "auditor"):
        query = query.filter_by(branch_id=current_user.branch_id)
    purchases = query.order_by(DirectPurchase.purchased_at.desc()).limit(200).all()
    return render_template("purchases/index.html", title="Compras directas", purchases=purchases)


@purchases_bp.route("/create", methods=["GET", "POST"])
@login_required
@permission_required("purchases.manage")
def create():
    form = PurchaseForm()
    form.customer_id.choices = [(0, "—")] + [
        (c.id, f"{c.code} · {c.full_name}")
        for c in Customer.query.filter_by(is_deleted=False).order_by(Customer.first_name).limit(300)
    ]
    form.deliverer_id.choices = [(0, "—")] + [
        (d.id, f"{d.code} · {d.full_name}")
        for d in Deliverer.query.filter_by(is_deleted=False).order_by(Deliverer.id.desc()).limit(300)
    ]
    form.item_id.choices = [(0, "—")] + [
        (i.id, f"{i.code} · {i.brand or ''} {i.model or ''}")
        for i in Item.query.filter(
            Item.is_deleted.is_(False),
            Item.status.in_(["en_evaluacion", "pendiente_documentacion"]),
        ).limit(300)
    ]
    if form.validate_on_submit():
        if 0 in {form.customer_id.data, form.deliverer_id.data, form.item_id.data}:
            flash("Complete cliente, quien entrega y artículo.", "danger")
        elif not form.declaration_accepted.data:
            flash("Debe aceptar la declaración de procedencia.", "danger")
        else:
            last = DirectPurchase.query.order_by(DirectPurchase.id.desc()).first()
            number = next_code("COM", last.purchase_number if last else None)
            branch_id = current_user.branch_id
            purchase = DirectPurchase(
                purchase_number=number,
                estimated_value=to_decimal(form.estimated_value.data) if form.estimated_value.data is not None else None,
                negotiated_price=to_decimal(form.negotiated_price.data),
                paid_price=to_decimal(form.paid_price.data),
                payment_method=form.payment_method.data,
                status=form.status.data,
                observations=form.observations.data,
                declaration_accepted=True,
                customer_id=form.customer_id.data,
                deliverer_id=form.deliverer_id.data,
                item_id=form.item_id.data,
                branch_id=branch_id,
                buyer_user_id=current_user.id,
            )
            item = db.session.get(Item, form.item_id.data)
            old = item.status if item else None
            if item:
                item.status = form.status.data
                item.purchase_price = purchase.paid_price
                item.customer_id = form.customer_id.data
                item.deliverer_id = form.deliverer_id.data
                db.session.add(
                    ItemMovement(
                        item_id=item.id,
                        movement_type="compra_directa",
                        from_status=old,
                        to_status=item.status,
                        reference=number,
                        user_id=current_user.id,
                        branch_id=branch_id,
                    )
                )
            db.session.add(purchase)
            log_action(
                action="create",
                module="purchases",
                record_type="direct_purchase",
                new_value={"number": number, "paid": str(purchase.paid_price)},
            )
            db.session.commit()
            session = get_open_session(branch_id) if branch_id else None
            if session:
                add_movement(
                    session=session,
                    movement_type="compra",
                    concept=f"Compra {number}",
                    amount=purchase.paid_price,
                    method=purchase.payment_method,
                    related_type="direct_purchase",
                    related_id=purchase.id,
                    reference=number,
                    user_id=current_user.id,
                )
            flash(f"Compra {number} registrada.", "success")
            return redirect(url_for("purchases.index"))
    return render_template("purchases/form.html", title="Nueva compra directa", form=form)