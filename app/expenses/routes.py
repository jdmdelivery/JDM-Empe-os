"""Gastos e ingresos externos."""

from flask import flash, redirect, render_template, url_for
from flask_login import current_user, login_required
from flask_wtf import FlaskForm
from wtforms import DecimalField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, NumberRange, Optional

from app.expenses import expenses_bp
from app.extensions import db
from app.models import Expense, ExpenseCategory
from app.services.audit_service import log_action
from app.services.cash_service import add_movement, get_open_session
from app.utils.decorators import permission_required
from app.utils.money import to_decimal

DEFAULT_EXPENSE_CATEGORIES = [
    ("alquiler", "Alquiler"),
    ("electricidad", "Electricidad"),
    ("internet", "Internet"),
    ("nomina", "Nómina"),
    ("reparaciones", "Reparaciones"),
    ("transporte", "Transporte"),
    ("seguridad", "Seguridad"),
    ("suministros", "Suministros"),
    ("publicidad", "Publicidad"),
    ("otros", "Otros"),
]


def seed_expense_categories():
    for code, name in DEFAULT_EXPENSE_CATEGORIES:
        if ExpenseCategory.query.filter_by(code=code).first() is None:
            db.session.add(ExpenseCategory(code=code, name=name, is_active=True))
    db.session.commit()


class ExpenseForm(FlaskForm):
    entry_type = SelectField(
        "Tipo",
        choices=[("gasto", "Gasto"), ("ingreso", "Ingreso externo")],
        default="gasto",
    )
    category_id = SelectField("Categoría", coerce=int, validators=[Optional()])
    concept = StringField("Concepto", validators=[DataRequired()])
    amount = DecimalField("Monto", places=2, validators=[DataRequired(), NumberRange(min=0.01)])
    method = SelectField(
        "Método",
        choices=[("efectivo", "Efectivo"), ("transferencia", "Transferencia")],
        default="efectivo",
    )
    notes = TextAreaField("Notas", validators=[Optional()])
    submit = SubmitField("Guardar")


@expenses_bp.route("/")
@login_required
@permission_required("expenses.view", "expenses.manage")
def index():
    seed_expense_categories()
    query = Expense.query.filter_by(is_deleted=False)
    if not current_user.has_role("superadmin", "auditor"):
        query = query.filter_by(branch_id=current_user.branch_id)
    expenses = query.order_by(Expense.occurred_at.desc()).limit(200).all()
    return render_template("expenses/index.html", title="Gastos e ingresos", expenses=expenses)


@expenses_bp.route("/create", methods=["GET", "POST"])
@login_required
@permission_required("expenses.manage")
def create():
    seed_expense_categories()
    form = ExpenseForm()
    form.category_id.choices = [(0, "—")] + [
        (c.id, c.name) for c in ExpenseCategory.query.filter_by(is_active=True).all()
    ]
    if form.validate_on_submit():
        branch_id = current_user.branch_id
        if not branch_id:
            from app.models import Branch

            main = Branch.query.filter_by(is_main=True).first()
            branch_id = main.id
        expense = Expense(
            entry_type=form.entry_type.data,
            category_id=form.category_id.data or None,
            concept=form.concept.data,
            amount=to_decimal(form.amount.data),
            method=form.method.data,
            notes=form.notes.data,
            branch_id=branch_id,
            created_by_id=current_user.id,
            status="aprobado",
        )
        if expense.category_id == 0:
            expense.category_id = None
        db.session.add(expense)
        log_action(
            action="create",
            module="expenses",
            record_type="expense",
            new_value={"concept": expense.concept, "amount": str(expense.amount)},
        )
        db.session.commit()
        session = get_open_session(branch_id)
        if session:
            add_movement(
                session=session,
                movement_type="gasto" if expense.entry_type == "gasto" else "ingreso",
                concept=expense.concept,
                amount=expense.amount,
                method=expense.method,
                related_type="expense",
                related_id=expense.id,
                user_id=current_user.id,
            )
        flash("Registro guardado.", "success")
        return redirect(url_for("expenses.index"))
    return render_template("expenses/form.html", title="Nuevo gasto/ingreso", form=form)