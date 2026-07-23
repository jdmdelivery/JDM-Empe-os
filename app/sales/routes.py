"""Ventas, reservas básicas."""

from datetime import timedelta

from flask import flash, redirect, render_template, url_for
from flask_login import current_user, login_required
from flask_wtf import FlaskForm
from wtforms import DecimalField, IntegerField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, NumberRange, Optional

from app.extensions import db
from app.models import Customer, Item, ItemMovement, Reservation, Sale, SaleItem, SalePayment, Warranty
from app.sales import sales_bp
from app.services.audit_service import log_action
from app.services.cash_service import add_movement, get_open_session
from app.services.numbering import next_code
from app.utils.decorators import permission_required
from app.utils.datetime_utils import local_now
from app.utils.money import money_add, money_sub, to_decimal


class SaleForm(FlaskForm):
    customer_id = SelectField("Cliente comprador", coerce=int, validators=[Optional()])
    item_id = SelectField("Artículo", coerce=int, validators=[DataRequired()])
    sale_price = DecimalField("Precio final", places=2, validators=[DataRequired(), NumberRange(min=0)])
    discount = DecimalField("Descuento", places=2, default=0, validators=[Optional()])
    tax = DecimalField("Impuesto", places=2, default=0, validators=[Optional()])
    payment_method = SelectField(
        "Método",
        choices=[("efectivo", "Efectivo"), ("tarjeta", "Tarjeta"), ("transferencia", "Transferencia"), ("mixto", "Mixto")],
        default="efectivo",
    )
    cash_received = DecimalField("Efectivo recibido", places=2, validators=[Optional()])
    warranty_days = IntegerField("Días de garantía", default=0, validators=[Optional(), NumberRange(min=0)])
    conditions = TextAreaField("Condiciones", validators=[Optional()])
    submit = SubmitField("Registrar venta")


class ReservationForm(FlaskForm):
    customer_id = SelectField("Cliente", coerce=int, validators=[DataRequired()])
    item_id = SelectField("Artículo", coerce=int, validators=[DataRequired()])
    deposit = DecimalField("Depósito", places=2, default=0, validators=[Optional()])
    notes = StringField("Notas", validators=[Optional()])
    submit = SubmitField("Reservar")


@sales_bp.route("/")
@login_required
@permission_required("sales.view", "sales.manage")
def index():
    query = Sale.query.filter_by(is_deleted=False)
    if not current_user.has_role("superadmin", "auditor"):
        query = query.filter_by(branch_id=current_user.branch_id)
    sales = query.order_by(Sale.sold_at.desc()).limit(200).all()
    return render_template("sales/index.html", title="Ventas", sales=sales)


@sales_bp.route("/create", methods=["GET", "POST"])
@login_required
@permission_required("sales.manage")
def create():
    form = SaleForm()
    form.customer_id.choices = [(0, "— Público general —")] + [
        (c.id, f"{c.code} · {c.full_name}")
        for c in Customer.query.filter_by(is_deleted=False).limit(300)
    ]
    form.item_id.choices = [(0, "—")] + [
        (i.id, f"{i.code} · {i.brand or ''} {i.model or ''} · {i.sale_price or i.estimated_value or 0}")
        for i in Item.query.filter(
            Item.is_deleted.is_(False),
            Item.status.in_(["disponible_venta", "autorizado_inventario"]),
        ).limit(300)
    ]
    if form.validate_on_submit():
        item = db.session.get(Item, form.item_id.data)
        if item is None or form.item_id.data == 0:
            flash("Seleccione un artículo disponible.", "danger")
        elif item.status not in {"disponible_venta", "autorizado_inventario"}:
            flash("El artículo no está disponible para venta.", "danger")
        else:
            discount = to_decimal(form.discount.data or 0)
            tax = to_decimal(form.tax.data or 0)
            price = to_decimal(form.sale_price.data)
            total = money_add(money_sub(price, discount), tax)
            last = Sale.query.order_by(Sale.id.desc()).first()
            invoice = next_code("FAC", last.invoice_number if last else None)
            branch_id = current_user.branch_id or item.branch_id
            warranty_until = None
            if form.warranty_days.data:
                warranty_until = local_now().date() + timedelta(days=int(form.warranty_days.data))
            cash_received = to_decimal(form.cash_received.data) if form.cash_received.data is not None else total
            change = money_sub(cash_received, total) if form.payment_method.data == "efectivo" else to_decimal(0)
            sale = Sale(
                invoice_number=invoice,
                subtotal=price,
                discount=discount,
                tax=tax,
                total=total,
                payment_method=form.payment_method.data,
                cash_received=cash_received,
                change_amount=change,
                warranty_days=form.warranty_days.data or 0,
                warranty_until=warranty_until,
                conditions=form.conditions.data,
                customer_id=form.customer_id.data or None,
                branch_id=branch_id,
                seller_id=current_user.id,
            )
            if sale.customer_id == 0:
                sale.customer_id = None
            db.session.add(sale)
            db.session.flush()
            db.session.add(
                SaleItem(
                    sale_id=sale.id,
                    item_id=item.id,
                    original_price=item.sale_price or item.estimated_value or price,
                    discount=discount,
                    final_price=total,
                )
            )
            db.session.add(
                SalePayment(sale_id=sale.id, method=form.payment_method.data, amount=total)
            )
            old = item.status
            item.status = "vendido"
            db.session.add(
                ItemMovement(
                    item_id=item.id,
                    movement_type="venta",
                    from_status=old,
                    to_status="vendido",
                    reference=invoice,
                    user_id=current_user.id,
                    branch_id=branch_id,
                )
            )
            if form.warranty_days.data:
                db.session.add(
                    Warranty(
                        sale_id=sale.id,
                        item_id=item.id,
                        certificate_number=next_code("GAR", None),
                        starts_on=local_now().date(),
                        ends_on=warranty_until,
                        terms=form.conditions.data,
                    )
                )
            log_action(
                action="create",
                module="sales",
                record_type="sale",
                record_id=sale.id,
                new_value={"invoice": invoice, "total": str(total)},
            )
            db.session.commit()
            session = get_open_session(branch_id)
            if session:
                add_movement(
                    session=session,
                    movement_type="venta",
                    concept=f"Venta {invoice}",
                    amount=total,
                    method=form.payment_method.data,
                    related_type="sale",
                    related_id=sale.id,
                    reference=invoice,
                    user_id=current_user.id,
                )
            flash(f"Venta {invoice} registrada.", "success")
            return redirect(url_for("sales.index"))
    return render_template("sales/form.html", title="Nueva venta", form=form)


@sales_bp.route("/reservations", methods=["GET", "POST"])
@login_required
@permission_required("sales.manage")
def reservations():
    form = ReservationForm()
    form.customer_id.choices = [(0, "—")] + [
        (c.id, c.full_name) for c in Customer.query.filter_by(is_deleted=False).limit(300)
    ]
    form.item_id.choices = [(0, "—")] + [
        (i.id, i.code)
        for i in Item.query.filter(
            Item.is_deleted.is_(False), Item.status == "disponible_venta"
        ).limit(300)
    ]
    if form.validate_on_submit() and form.customer_id.data and form.item_id.data:
        item = db.session.get(Item, form.item_id.data)
        reservation = Reservation(
            item_id=form.item_id.data,
            customer_id=form.customer_id.data,
            deposit=to_decimal(form.deposit.data or 0),
            notes=form.notes.data,
            branch_id=current_user.branch_id,
            created_by_id=current_user.id,
            expires_at=local_now() + timedelta(days=3),
        )
        if item:
            item.status = "reservado"
        db.session.add(reservation)
        db.session.commit()
        flash("Reserva creada.", "success")
        return redirect(url_for("sales.reservations"))
    rows = Reservation.query.filter_by(is_deleted=False).order_by(Reservation.id.desc()).limit(100).all()
    return render_template("sales/reservations.html", title="Reservas", form=form, reservations=rows)