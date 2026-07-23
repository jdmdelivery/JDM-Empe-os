"""Pruebas Fases 3-6: finanzas, pagos, idempotencia, caja."""

from __future__ import annotations

from decimal import Decimal

from app.services.finance_service import (
    allocate_payment,
    build_breakdown,
    calculate_interest,
    calculate_late_fee,
    role_percent_limit,
)
from app.services.pawn_service import create_pawn_contract, register_payment
from app.services.cash_service import close_session, open_session, session_balance
from app.services.seed_service import ensure_superadmin
from app.extensions import db
from app.models import Branch, Customer, Deliverer, Item, ItemCategory
from app.services.category_seed import seed_item_categories
from app.utils.money import to_decimal


def test_interest_and_allocation_decimal():
    interest = calculate_interest("10000", "12", interest_type="simple_mensual")
    assert interest == Decimal("1200.00")
    late = calculate_late_fee("10000", late_percent="5", days_late=2, mode="mensual")
    assert late == Decimal("500.00")
    breakdown = build_breakdown(capital="10000", percent="10", fixed_fee="100")
    assert breakdown.total == Decimal("11100.00")
    result = allocate_payment(
        "1500",
        {"mora": "200", "cargos": "100", "interes": "500", "capital": "10000"},
    )
    assert result.applied["mora"] == Decimal("200.00")
    assert result.applied["cargos"] == Decimal("100.00")
    assert result.applied["interes"] == Decimal("500.00")
    assert result.applied["capital"] == Decimal("700.00")
    assert role_percent_limit("cashier") == Decimal("12.00")
    assert role_percent_limit("superadmin") is None


def _seed_ops(app):
    with app.app_context():
        ensure_superadmin(
            username="superadmin",
            email="admin@example.com",
            password="TestPass123!",
            must_change_password=False,
        )
        seed_item_categories()
        branch = Branch.query.filter_by(is_main=True).first()
        customer = Customer(
            code="CLI-2026-009001",
            first_name="Ana",
            last_name="Test",
            national_id="00111112222",
            phone_primary="8090001111",
            branch_id=branch.id,
            status="activo",
        )
        db.session.add(customer)
        db.session.flush()
        deliverer = Deliverer(
            code="ENT-2026-009001",
            is_same_as_customer=True,
            first_name="Ana",
            last_name="Test",
            national_id="00111112222",
            legitimate_origin_accepted=True,
            customer_id=customer.id,
            branch_id=branch.id,
        )
        db.session.add(deliverer)
        db.session.flush()
        category = ItemCategory.query.filter_by(code="celulares").first()
        item = Item(
            code="ART-2026-009001",
            category_id=category.id,
            brand="Demo",
            model="X1",
            serial_number="SN-FIN-001",
            status="en_evaluacion",
            branch_id=branch.id,
            customer_id=customer.id,
            deliverer_id=deliverer.id,
        )
        db.session.add(item)
        db.session.commit()
        return branch.id, customer.id, deliverer.id, item.id


def test_pawn_payment_idempotency(app):
    branch_id, customer_id, deliverer_id, item_id = _seed_ops(app)
    with app.app_context():
        contract = create_pawn_contract(
            customer_id=customer_id,
            deliverer_id=deliverer_id,
            item_id=item_id,
            branch_id=branch_id,
            capital=to_decimal("10000"),
            percent=to_decimal("10"),
            interest_type="simple_mensual",
            duration_days=30,
            grace_days=3,
            declaration_accepted=True,
            user_id=1,
        )
        p1 = register_payment(
            contract=contract,
            amount=to_decimal("500"),
            method="efectivo",
            payment_type="parcial",
            payer_name="Ana",
            notes=None,
            idempotency_key="idem-test-1",
            user_id=1,
        )
        p2 = register_payment(
            contract=contract,
            amount=to_decimal("500"),
            method="efectivo",
            payment_type="parcial",
            payer_name="Ana",
            notes=None,
            idempotency_key="idem-test-1",
            user_id=1,
        )
        assert p1.id == p2.id
        assert contract.pending_total < to_decimal("11100")


def test_cash_open_close(app):
    branch_id, *_ = _seed_ops(app)
    with app.app_context():
        session = open_session(branch_id=branch_id, opening_amount=to_decimal("5000"), user_id=1)
        assert session_balance(session) == Decimal("5000.00")
        closed = close_session(
            session=session, closing_amount=to_decimal("5000"), user_id=1, notes="OK"
        )
        assert closed.status == "cerrada"
        assert closed.difference_amount == Decimal("0.00")


def test_old_contract_keeps_percent(app):
    branch_id, customer_id, deliverer_id, item_id = _seed_ops(app)
    with app.app_context():
        contract = create_pawn_contract(
            customer_id=customer_id,
            deliverer_id=deliverer_id,
            item_id=item_id,
            branch_id=branch_id,
            capital=to_decimal("8000"),
            percent=to_decimal("15"),
            interest_type="simple_mensual",
            duration_days=30,
            grace_days=3,
            percent_manual=True,
            percent_original=to_decimal("10"),
            percent_change_reason="Cliente frecuente",
            declaration_accepted=True,
            user_id=1,
        )
        assert contract.percent == Decimal("15.00")
        assert len(contract.versions) == 1
        from app.models import Setting

        setting = Setting.query.filter_by(key="default_interest_percent").first()
        if setting:
            setting.value = "20"
            db.session.commit()
        db.session.refresh(contract)
        assert contract.percent == Decimal("15.00")