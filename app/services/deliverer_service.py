"""Helpers de persona que entrega."""

from __future__ import annotations

from app.extensions import db
from app.models import Customer, Deliverer
from app.services.numbering import next_deliverer_code


def _last_deliverer_code() -> str | None:
    row = Deliverer.query.order_by(Deliverer.id.desc()).first()
    return row.code if row else None


def ensure_customer_deliverer(customer: Customer, *, user_id: int | None = None) -> Deliverer:
    """Obtiene o crea la persona que entrega = mismo cliente."""
    existing = (
        Deliverer.query.filter_by(
            customer_id=customer.id,
            is_same_as_customer=True,
            is_deleted=False,
        )
        .order_by(Deliverer.id.desc())
        .first()
    )
    if existing:
        return existing

    deliverer = Deliverer(
        code=next_deliverer_code(_last_deliverer_code()),
        is_same_as_customer=True,
        first_name=customer.first_name,
        last_name=customer.last_name,
        national_id=customer.national_id,
        phone=customer.phone_primary,
        address=customer.address,
        relationship_to_customer="Mismo cliente",
        legitimate_origin_accepted=True,
        customer_id=customer.id,
        branch_id=customer.branch_id,
        received_by_id=user_id,
    )
    db.session.add(deliverer)
    db.session.commit()
    return deliverer


def ensure_deliverers_for_customers(customers: list[Customer], *, user_id: int | None = None) -> None:
    for customer in customers:
        ensure_customer_deliverer(customer, user_id=user_id)
