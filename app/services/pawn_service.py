"""Servicio de empeños, pagos y renovaciones."""

from __future__ import annotations

import json
import secrets
from datetime import date, timedelta
from decimal import Decimal

from flask import has_request_context, request
from flask_login import current_user

from app.extensions import db
from app.models import (
    Item,
    ItemMovement,
    PawnContract,
    PawnContractVersion,
    PawnPayment,
    PawnPaymentAllocation,
    Renewal,
)
from app.services.audit_service import log_action
from app.services.finance_service import (
    allocate_payment,
    build_breakdown,
    calculate_late_fee,
    days_between,
)
from app.services.numbering import next_code
from app.utils.datetime_utils import local_now, utc_now
from app.utils.money import ZERO, money_add, to_decimal


def _last_contract_number() -> str | None:
    row = PawnContract.query.order_by(PawnContract.id.desc()).first()
    return row.contract_number if row else None


def _last_receipt_number() -> str | None:
    row = PawnPayment.query.order_by(PawnPayment.id.desc()).first()
    return row.receipt_number if row else None


def resolve_default_percent(*, branch_id: int | None = None, category_id: int | None = None) -> Decimal:
    from app.models import Setting

    setting = Setting.query.filter_by(key="default_interest_percent").first()
    return to_decimal(setting.value if setting and setting.value else "10")


def create_pawn_contract(
    *,
    customer_id: int,
    deliverer_id: int,
    item_id: int,
    branch_id: int,
    capital: Decimal,
    percent: Decimal,
    interest_type: str,
    duration_days: int,
    grace_days: int,
    fees_amount: Decimal = ZERO,
    late_percent: Decimal = ZERO,
    late_fixed: Decimal = ZERO,
    late_mode: str = "mensual",
    conditions: str | None = None,
    observations: str | None = None,
    percent_manual: bool = False,
    percent_original: Decimal | None = None,
    percent_change_reason: str | None = None,
    declaration_accepted: bool = False,
    user_id: int | None = None,
) -> PawnContract:
    if has_request_context() and current_user.is_authenticated:
        user_id = user_id or current_user.id

    start = local_now().date()
    breakdown = build_breakdown(
        capital=capital,
        percent=percent,
        interest_type=interest_type,
        fixed_fee=fees_amount,
        grace_days=grace_days,
        start_date=start,
        duration_days=duration_days,
    )
    number = next_code("EMP", _last_contract_number())
    contract = PawnContract(
        contract_number=number,
        status="activo",
        start_date=start,
        duration_days=duration_days,
        due_date=breakdown.due_date or (start + timedelta(days=duration_days)),
        grace_days=grace_days,
        capital=breakdown.capital,
        capital_balance=breakdown.capital,
        interest_balance=breakdown.interest,
        fee_balance=breakdown.fees,
        late_fee_balance=ZERO,
        percent=breakdown.percent,
        interest_type=interest_type,
        interest_amount=breakdown.interest,
        fees_amount=breakdown.fees,
        total_due=breakdown.total,
        conditions=conditions,
        observations=observations,
        percent_manual=percent_manual,
        percent_original=percent_original,
        percent_change_reason=percent_change_reason,
        percent_authorized_by_id=user_id if percent_manual else None,
        late_percent=to_decimal(late_percent),
        late_fixed=to_decimal(late_fixed),
        late_mode=late_mode,
        declaration_accepted=declaration_accepted,
        signed_at=utc_now() if declaration_accepted else None,
        customer_id=customer_id,
        deliverer_id=deliverer_id,
        item_id=item_id,
        branch_id=branch_id,
        created_by_id=user_id,
    )
    db.session.add(contract)
    db.session.flush()

    snapshot = {
        "percent": str(contract.percent),
        "interest_type": contract.interest_type,
        "frequency": contract.frequency,
        "late_percent": str(contract.late_percent),
        "late_fixed": str(contract.late_fixed),
        "late_mode": contract.late_mode,
        "grace_days": contract.grace_days,
        "payment_order": contract.payment_order,
        "fees_amount": str(contract.fees_amount),
        "capital": str(contract.capital),
        "interest_amount": str(contract.interest_amount),
        "total_due": str(contract.total_due),
        "approved_by_id": user_id,
    }
    db.session.add(
        PawnContractVersion(
            contract_id=contract.id,
            version_number=1,
            snapshot_json=json.dumps(snapshot, ensure_ascii=False),
            approved_by_id=user_id,
        )
    )

    item = db.session.get(Item, item_id)
    if item:
        old_status = item.status
        item.status = "empenado"
        item.loan_amount = breakdown.capital
        item.customer_id = customer_id
        item.deliverer_id = deliverer_id
        db.session.add(
            ItemMovement(
                item_id=item.id,
                movement_type="empeño",
                from_status=old_status,
                to_status="empenado",
                reference=contract.contract_number,
                user_id=user_id,
                branch_id=branch_id,
            )
        )

    log_action(
        action="create",
        module="pawn",
        record_type="pawn_contract",
        record_id=contract.id,
        new_value={"number": contract.contract_number, "percent": str(contract.percent)},
        reason=percent_change_reason,
    )
    db.session.commit()
    return contract


def refresh_late_fee(contract: PawnContract, as_of: date | None = None) -> Decimal:
    today = as_of or local_now().date()
    grace_end = contract.due_date + timedelta(days=contract.grace_days or 0)
    days_late = days_between(grace_end, today)
    if days_late <= 0:
        return contract.late_fee_balance
    late = calculate_late_fee(
        contract.capital_balance,
        late_percent=contract.late_percent,
        late_fixed=contract.late_fixed,
        days_late=days_late,
        mode=contract.late_mode,
    )
    contract.late_fee_balance = late
    return late


def register_payment(
    *,
    contract: PawnContract,
    amount: Decimal,
    method: str,
    payment_type: str,
    payer_name: str | None,
    notes: str | None,
    idempotency_key: str | None = None,
    user_id: int | None = None,
) -> PawnPayment:
    key = idempotency_key or secrets.token_hex(16)
    existing = PawnPayment.query.filter_by(idempotency_key=key).first()
    if existing:
        return existing

    refresh_late_fee(contract)
    previous = contract.pending_total
    default_order = tuple(
        (contract.payment_order or "mora,cargos,interes,capital").split(",")
    )
    # Tipo de pago: el cliente elige solo interés, abono a capital, etc.
    type_orders = {
        "interes": ("interes",),
        "solo_interes": ("interes",),
        "capital": ("capital",),
        "abono": ("capital",),
        "mora": ("mora",),
        "parcial": default_order,
        "total": default_order,
        "liquidacion": default_order,
        "auto": default_order,
    }
    order = type_orders.get(payment_type, default_order)
    allocation = allocate_payment(
        amount,
        {
            "mora": contract.late_fee_balance,
            "cargos": contract.fee_balance,
            "interes": contract.interest_balance,
            "capital": contract.capital_balance,
        },
        order=order,
    )
    contract.late_fee_balance = allocation.new_balances.get("mora", ZERO)
    contract.fee_balance = allocation.new_balances.get("cargos", ZERO)
    contract.interest_balance = allocation.new_balances.get("interes", ZERO)
    contract.capital_balance = allocation.new_balances.get("capital", ZERO)
    contract.last_payment_at = utc_now()
    new_balance = contract.pending_total
    if new_balance <= ZERO:
        contract.status = "pagado"
        if contract.item:
            old = contract.item.status
            contract.item.status = "pendiente_retiro"
            db.session.add(
                ItemMovement(
                    item_id=contract.item_id,
                    movement_type="pago_total",
                    from_status=old,
                    to_status="pendiente_retiro",
                    reference=contract.contract_number,
                    user_id=user_id,
                    branch_id=contract.branch_id,
                )
            )

    receipt = next_code("REC", _last_receipt_number())
    resolved_payer = (payer_name or "").strip() or (
        contract.customer.full_name if contract.customer else None
    )
    payment = PawnPayment(
        receipt_number=receipt,
        idempotency_key=key,
        payment_type=payment_type,
        amount=to_decimal(amount),
        method=method,
        previous_balance=previous,
        new_balance=new_balance,
        payer_name=resolved_payer,
        notes=notes,
        contract_id=contract.id,
        customer_id=contract.customer_id,
        branch_id=contract.branch_id,
        received_by_id=user_id,
    )
    db.session.add(payment)
    db.session.flush()
    for concept, value in allocation.applied.items():
        if value > ZERO:
            db.session.add(
                PawnPaymentAllocation(payment_id=payment.id, concept=concept, amount=value)
            )
    log_action(
        action="payment",
        module="payments",
        record_type="pawn_payment",
        record_id=payment.id,
        new_value={"receipt": receipt, "amount": str(payment.amount)},
    )
    db.session.commit()
    return payment


def renew_contract(
    *,
    contract: PawnContract,
    amount_paid: Decimal,
    method: str = "efectivo",
    user_id: int | None = None,
) -> Renewal:
    # Pago típico de renovación: interés + mora (+ cargos)
    pay_amount = money_add(
        min(to_decimal(amount_paid), money_add(contract.interest_balance, contract.late_fee_balance, contract.fee_balance)),
    )
    if pay_amount <= ZERO:
        raise ValueError("Debe pagar al menos interés/mora para renovar.")

    payment = register_payment(
        contract=contract,
        amount=pay_amount,
        method=method,
        payment_type="renovacion",
        payer_name=contract.customer.full_name if contract.customer else None,
        notes="Renovación de contrato",
        user_id=user_id,
    )
    previous_due = contract.due_date
    contract.due_date = contract.due_date + timedelta(days=contract.duration_days or 30)
    contract.status = "renovado"
    contract.renewal_count += 1
    # Regenerar interés del nuevo período con snapshot original
    from app.services.finance_service import calculate_interest

    new_interest = calculate_interest(
        contract.capital_balance, contract.percent, interest_type=contract.interest_type
    )
    contract.interest_balance = money_add(contract.interest_balance, new_interest)
    contract.interest_amount = new_interest
    renewal_number = f"{contract.contract_number}-R{contract.renewal_count:02d}"
    renewal = Renewal(
        renewal_number=renewal_number,
        amount_paid=payment.amount,
        previous_due_date=previous_due,
        new_due_date=contract.due_date,
        percent_applied=contract.percent,
        contract_id=contract.id,
        payment_id=payment.id,
        renewed_by_id=user_id,
        branch_id=contract.branch_id,
    )
    db.session.add(renewal)
    if contract.item:
        contract.item.status = "renovado"
    log_action(
        action="renew",
        module="renewals",
        record_type="renewal",
        record_id=renewal.id,
        new_value={"number": renewal_number},
    )
    db.session.commit()
    return renewal


def update_expiration_statuses() -> int:
    today = local_now().date()
    updated = 0
    contracts = PawnContract.query.filter(
        PawnContract.is_deleted.is_(False),
        PawnContract.status.in_(["activo", "renovado", "proximo_vencer", "vencido", "en_periodo_gracia"]),
    ).all()
    for contract in contracts:
        refresh_late_fee(contract)
        days_to_due = days_between(today, contract.due_date)
        grace_end = contract.due_date + timedelta(days=contract.grace_days or 0)
        if contract.status in {"pagado", "retirado", "autorizado_inventario", "disponible_venta"}:
            continue
        if today > grace_end:
            if contract.status != "pendiente_autorizacion" and not contract.authorized_for_inventory:
                contract.status = "pendiente_autorizacion"
                updated += 1
        elif today > contract.due_date:
            contract.status = "en_periodo_gracia" if today <= grace_end else "vencido"
            updated += 1
        elif 0 <= days_to_due <= 3:
            contract.status = "proximo_vencer"
            updated += 1
    db.session.commit()
    return updated