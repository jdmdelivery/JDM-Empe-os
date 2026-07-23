"""Rutas de pagos."""

from __future__ import annotations

import secrets

from flask import Response, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.forms.pawn_forms import PaymentForm
from app.models import EvidenceFile, OperationSignature, PawnContract, PawnPayment
from app.payments import payments_bp
from app.services.cash_service import add_movement, get_open_session
from app.services.file_storage import save_base64_image
from app.services.pawn_service import register_payment
from app.utils.decorators import permission_required
from app.utils.money import format_money, to_decimal


@payments_bp.route("/")
@login_required
@permission_required("payments.view", "payments.manage")
def index():
    query = PawnPayment.query.filter_by(is_deleted=False, is_voided=False)
    if not current_user.has_role("superadmin", "auditor"):
        query = query.filter_by(branch_id=current_user.branch_id)
    payments = query.order_by(PawnPayment.paid_at.desc()).limit(200).all()
    return render_template("payments/index.html", title="Pagos", payments=payments)


@payments_bp.route("/create", methods=["GET", "POST"])
@login_required
@permission_required("payments.manage")
def create():
    form = PaymentForm()
    contracts = PawnContract.query.filter(
        PawnContract.is_deleted.is_(False),
        PawnContract.status.in_(
            ["activo", "renovado", "proximo_vencer", "vencido", "en_periodo_gracia"]
        ),
    )
    if not current_user.has_role("superadmin"):
        contracts = contracts.filter_by(branch_id=current_user.branch_id)
    form.contract_id.choices = [(0, "— Seleccione —")] + [
        (c.id, f"{c.contract_number} · pendiente {format_money(c.pending_total)}")
        for c in contracts.order_by(PawnContract.id.desc()).limit(200)
    ]
    if not form.is_submitted():
        form.idempotency_key.data = secrets.token_hex(12)
        preselect = request.args.get("contract_id", type=int)
        if preselect:
            form.contract_id.data = preselect

    if form.validate_on_submit():
        contract = db.session.get(PawnContract, form.contract_id.data)
        if contract is None or form.contract_id.data == 0:
            flash("Seleccione un contrato.", "danger")
        else:
            payment = register_payment(
                contract=contract,
                amount=to_decimal(form.amount.data),
                method=form.method.data,
                payment_type=form.payment_type.data,
                payer_name=form.payer_name.data,
                notes=form.notes.data,
                idempotency_key=form.idempotency_key.data or secrets.token_hex(12),
                user_id=current_user.id,
            )
            if form.signature_data.data and str(form.signature_data.data).startswith(
                "data:image"
            ):
                stored = save_base64_image(
                    form.signature_data.data, folder="signatures"
                )
                db.session.add(
                    OperationSignature(
                        signer_role="customer",
                        related_type="pawn_payment",
                        related_id=payment.id,
                        customer_id=contract.customer_id,
                        file_path=stored.relative_path,
                        sha256_hash=stored.sha256_hash,
                        declaration_text="Firma de pago / abono",
                        ip_address=request.headers.get(
                            "X-Forwarded-For", request.remote_addr
                        ),
                        captured_by_id=current_user.id,
                        branch_id=contract.branch_id,
                    )
                )
                db.session.add(
                    EvidenceFile(
                        uuid=stored.uuid,
                        evidence_type="payment_signature",
                        related_type="pawn_payment",
                        related_id=payment.id,
                        customer_id=contract.customer_id,
                        file_path=stored.relative_path,
                        file_url=stored.url_path,
                        safe_name=stored.safe_name,
                        mime_type=stored.mime_type,
                        file_size=stored.file_size,
                        sha256_hash=stored.sha256_hash,
                        captured_by_id=current_user.id,
                        branch_id=contract.branch_id,
                    )
                )
                db.session.commit()
            session = get_open_session(contract.branch_id)
            if session:
                add_movement(
                    session=session,
                    movement_type="pago_empeno",
                    concept=f"Pago {payment.receipt_number}",
                    amount=payment.amount,
                    method=payment.method,
                    related_type="pawn_payment",
                    related_id=payment.id,
                    reference=payment.receipt_number,
                    user_id=current_user.id,
                )
            labels = {
                "interes": "solo interés",
                "abono": "abono a capital",
                "capital": "abono a capital",
                "mora": "mora",
                "auto": "automático",
                "parcial": "parcial",
                "total": "liquidación",
                "liquidacion": "liquidación",
            }
            flash(
                f"Pago {payment.receipt_number} registrado ({labels.get(form.payment_type.data, form.payment_type.data)}).",
                "success",
            )
            return redirect(url_for("payments.receipt", payment_id=payment.id))

    selected = None
    balances = {}
    if form.contract_id.data and form.contract_id.data != 0:
        selected = db.session.get(PawnContract, form.contract_id.data)
        if selected:
            from app.services.pawn_service import refresh_late_fee

            refresh_late_fee(selected)
            db.session.commit()
            balances = {
                "interest": str(to_decimal(selected.interest_balance)),
                "capital": str(to_decimal(selected.capital_balance)),
                "late": str(to_decimal(selected.late_fee_balance)),
                "fees": str(to_decimal(selected.fee_balance)),
                "total": str(to_decimal(selected.pending_total)),
            }
    return render_template(
        "payments/form.html",
        title="Registrar pago",
        form=form,
        contract=selected,
        balances=balances,
    )


@payments_bp.route("/<int:payment_id>/receipt")
@login_required
@permission_required("payments.view", "payments.manage")
def receipt(payment_id: int):
    payment = db.session.get(PawnPayment, payment_id)
    if payment is None:
        flash("Recibo no encontrado.", "danger")
        return redirect(url_for("payments.index"))
    signature = (
        OperationSignature.query.filter_by(
            related_type="pawn_payment", related_id=payment.id
        )
        .order_by(OperationSignature.id.desc())
        .first()
    )
    return render_template(
        "payments/receipt.html",
        title=f"Recibo {payment.receipt_number}",
        payment=payment,
        signature=signature,
    )