"""Caja: apertura, movimientos y cierre."""

from flask import flash, redirect, render_template, url_for
from flask_login import current_user, login_required
from flask_wtf import FlaskForm
from wtforms import DecimalField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, NumberRange, Optional

from app.cash import cash_bp
from app.services.cash_service import (
    add_movement,
    close_session,
    get_open_session,
    open_session,
    session_balance,
)
from app.utils.decorators import permission_required
from app.utils.money import to_decimal


class OpenCashForm(FlaskForm):
    opening_amount = DecimalField("Monto inicial", places=2, validators=[DataRequired(), NumberRange(min=0)])
    submit = SubmitField("Abrir caja")


class MovementForm(FlaskForm):
    movement_type = SelectField(
        "Tipo",
        choices=[
            ("ingreso", "Ingreso"),
            ("egreso", "Egreso"),
            ("retiro", "Retiro"),
            ("deposito", "Depósito"),
        ],
    )
    concept = StringField("Concepto", validators=[DataRequired()])
    amount = DecimalField("Monto", places=2, validators=[DataRequired(), NumberRange(min=0.01)])
    method = SelectField(
        "Método",
        choices=[("efectivo", "Efectivo"), ("transferencia", "Transferencia")],
        default="efectivo",
    )
    submit = SubmitField("Registrar movimiento")


class CloseCashForm(FlaskForm):
    closing_amount = DecimalField("Monto de cierre / arqueo", places=2, validators=[DataRequired()])
    notes = TextAreaField("Observaciones", validators=[Optional()])
    submit = SubmitField("Cerrar caja")


@cash_bp.route("/", methods=["GET", "POST"])
@login_required
@permission_required("cash.view", "cash.manage")
def index():
    if not current_user.branch_id and not current_user.has_role("superadmin"):
        flash("Debe tener sucursal asignada.", "danger")
        return redirect(url_for("dashboard.index"))
    branch_id = current_user.branch_id
    if not branch_id:
        from app.models import Branch

        main = Branch.query.filter_by(is_main=True).first()
        branch_id = main.id if main else None
    session = get_open_session(branch_id) if branch_id else None
    open_form = OpenCashForm()
    move_form = MovementForm()
    close_form = CloseCashForm()

    if open_form.validate_on_submit() and open_form.submit.data and current_user.has_permission("cash.manage"):
        try:
            open_session(
                branch_id=branch_id,
                opening_amount=to_decimal(open_form.opening_amount.data),
                user_id=current_user.id,
            )
            flash("Caja abierta.", "success")
            return redirect(url_for("cash.index"))
        except ValueError as exc:
            flash(str(exc), "danger")

    if session and move_form.validate_on_submit() and move_form.submit.data and current_user.has_permission("cash.manage"):
        add_movement(
            session=session,
            movement_type=move_form.movement_type.data,
            concept=move_form.concept.data,
            amount=to_decimal(move_form.amount.data),
            method=move_form.method.data,
            user_id=current_user.id,
        )
        flash("Movimiento registrado.", "success")
        return redirect(url_for("cash.index"))

    if session and close_form.validate_on_submit() and close_form.submit.data and current_user.has_permission("cash.manage"):
        close_session(
            session=session,
            closing_amount=to_decimal(close_form.closing_amount.data),
            user_id=current_user.id,
            notes=close_form.notes.data,
        )
        flash("Caja cerrada.", "warning")
        return redirect(url_for("cash.index"))

    balance = session_balance(session) if session else None
    return render_template(
        "cash/index.html",
        title="Caja",
        session=session,
        balance=balance,
        open_form=open_form,
        move_form=move_form,
        close_form=close_form,
    )