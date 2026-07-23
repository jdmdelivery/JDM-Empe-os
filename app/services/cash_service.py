"""Servicio de caja."""

from __future__ import annotations

from decimal import Decimal

from app.extensions import db
from app.models import CashMovement, CashRegister, CashSession
from app.services.audit_service import log_action
from app.utils.datetime_utils import utc_now
from app.utils.money import money_add, money_sub, to_decimal


def ensure_register(branch_id: int) -> CashRegister:
    register = CashRegister.query.filter_by(branch_id=branch_id, is_active=True).first()
    if register is None:
        register = CashRegister(
            code="CAJA-1",
            name="Caja principal",
            branch_id=branch_id,
            is_active=True,
        )
        db.session.add(register)
        db.session.commit()
    return register


def get_open_session(branch_id: int) -> CashSession | None:
    return CashSession.query.filter_by(branch_id=branch_id, status="abierta").first()


def open_session(*, branch_id: int, opening_amount: Decimal, user_id: int | None) -> CashSession:
    if get_open_session(branch_id):
        raise ValueError("Ya existe una caja abierta en esta sucursal.")
    register = ensure_register(branch_id)
    session = CashSession(
        register_id=register.id,
        branch_id=branch_id,
        opened_by_id=user_id,
        opening_amount=to_decimal(opening_amount),
        status="abierta",
    )
    db.session.add(session)
    db.session.flush()
    db.session.add(
        CashMovement(
            session_id=session.id,
            movement_type="apertura",
            concept="Apertura de caja",
            amount=to_decimal(opening_amount),
            user_id=user_id,
            branch_id=branch_id,
        )
    )
    log_action(action="cash_open", module="cash", record_type="cash_session", record_id=session.id)
    db.session.commit()
    return session


def add_movement(
    *,
    session: CashSession,
    movement_type: str,
    concept: str,
    amount: Decimal,
    method: str = "efectivo",
    related_type: str | None = None,
    related_id: int | None = None,
    reference: str | None = None,
    user_id: int | None = None,
) -> CashMovement:
    if session.status != "abierta":
        raise ValueError("La caja no está abierta.")
    movement = CashMovement(
        session_id=session.id,
        movement_type=movement_type,
        concept=concept,
        amount=to_decimal(amount),
        method=method,
        related_type=related_type,
        related_id=related_id,
        reference=reference,
        user_id=user_id,
        branch_id=session.branch_id,
    )
    db.session.add(movement)
    db.session.commit()
    return movement


def session_balance(session: CashSession) -> Decimal:
    total = to_decimal(session.opening_amount)
    for m in session.movements:
        if m.is_deleted or m.status != "activo" or m.movement_type == "apertura":
            continue
        if m.movement_type in {"ingreso", "venta", "pago_empeno", "deposito"}:
            total = money_add(total, m.amount)
        elif m.movement_type in {"egreso", "compra", "gasto", "retiro"}:
            total = money_sub(total, m.amount)
    return total


def close_session(
    *,
    session: CashSession,
    closing_amount: Decimal,
    user_id: int | None,
    notes: str | None = None,
) -> CashSession:
    expected = session_balance(session)
    session.expected_amount = expected
    session.closing_amount = to_decimal(closing_amount)
    session.difference_amount = money_sub(session.closing_amount, expected)
    session.status = "cerrada"
    session.closed_by_id = user_id
    session.closed_at = utc_now()
    session.notes = notes
    log_action(
        action="cash_close",
        module="cash",
        record_type="cash_session",
        record_id=session.id,
        new_value={
            "expected": str(expected),
            "closing": str(session.closing_amount),
            "difference": str(session.difference_amount),
        },
    )
    db.session.commit()
    return session
