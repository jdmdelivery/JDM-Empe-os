"""Rutas de renovaciones."""

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.forms.pawn_forms import RenewalForm
from app.models import PawnContract, Renewal
from app.renewals import renewals_bp
from app.services.pawn_service import renew_contract
from app.utils.decorators import permission_required
from app.utils.money import format_money, to_decimal


@renewals_bp.route("/")
@login_required
@permission_required("pawn.view", "pawn.manage")
def index():
    query = Renewal.query
    renewals = query.order_by(Renewal.renewed_at.desc()).limit(200).all()
    return render_template("renewals/index.html", title="Renovaciones", renewals=renewals)


@renewals_bp.route("/create", methods=["GET", "POST"])
@login_required
@permission_required("pawn.manage")
def create():
    form = RenewalForm()
    contracts = PawnContract.query.filter(
        PawnContract.is_deleted.is_(False),
        PawnContract.status.in_(["activo", "renovado", "proximo_vencer", "vencido", "en_periodo_gracia"]),
    )
    if not current_user.has_role("superadmin"):
        contracts = contracts.filter_by(branch_id=current_user.branch_id)
    form.contract_id.choices = [(0, "— Seleccione —")] + [
        (
            c.id,
            f"{c.contract_number} · interés/mora {format_money(c.interest_balance + c.late_fee_balance + c.fee_balance)}",
        )
        for c in contracts.order_by(PawnContract.id.desc()).limit(200)
    ]
    if not form.is_submitted():
        preselect = request.args.get("contract_id", type=int)
        if preselect:
            form.contract_id.data = preselect
    if form.validate_on_submit():
        contract = db.session.get(PawnContract, form.contract_id.data)
        if contract is None or form.contract_id.data == 0:
            flash("Seleccione un contrato.", "danger")
        else:
            try:
                renewal = renew_contract(
                    contract=contract,
                    amount_paid=to_decimal(form.amount.data),
                    method=form.method.data,
                    user_id=current_user.id,
                )
                flash(f"Renovación {renewal.renewal_number} aplicada.", "success")
                return redirect(url_for("renewals.index"))
            except ValueError as exc:
                flash(str(exc), "danger")
    return render_template("renewals/form.html", title="Renovar contrato", form=form)