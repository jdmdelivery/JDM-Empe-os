"""Repositorio de clientes."""

from __future__ import annotations

from sqlalchemy import or_

from app.extensions import db
from app.models import Customer


class CustomerRepository:
    @staticmethod
    def get_by_id(customer_id: int) -> Customer | None:
        return db.session.get(Customer, customer_id)

    @staticmethod
    def last_code() -> str | None:
        row = (
            Customer.query.filter(Customer.code.like("CLI-%"))
            .order_by(Customer.id.desc())
            .first()
        )
        return row.code if row else None

    @staticmethod
    def find_by_national_id(national_id: str, exclude_id: int | None = None) -> list[Customer]:
        query = Customer.query.filter(
            Customer.national_id == national_id,
            Customer.is_deleted.is_(False),
        )
        if exclude_id:
            query = query.filter(Customer.id != exclude_id)
        return query.all()

    @staticmethod
    def search(
        term: str = "",
        status: str = "",
        branch_id: int | None = None,
    ) -> list[Customer]:
        query = Customer.query.filter(Customer.is_deleted.is_(False))
        if branch_id is not None:
            query = query.filter(Customer.branch_id == branch_id)
        if status:
            query = query.filter(Customer.status == status)
        if term:
            like = f"%{term.strip()}%"
            query = query.filter(
                or_(
                    Customer.code.ilike(like),
                    Customer.first_name.ilike(like),
                    Customer.last_name.ilike(like),
                    Customer.national_id.ilike(like),
                    Customer.phone_primary.ilike(like),
                    Customer.whatsapp.ilike(like),
                )
            )
        return query.order_by(Customer.created_at.desc()).limit(200).all()