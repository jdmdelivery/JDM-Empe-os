"""Buscador global Fase 2."""

from __future__ import annotations

from sqlalchemy import or_

from app.models import Customer, Deliverer, Item


def global_search(term: str, *, limit: int = 20) -> dict[str, list]:
    q = (term or "").strip()
    if len(q) < 2:
        return {"customers": [], "deliverers": [], "articles": []}

    like = f"%{q}%"
    customers = (
        Customer.query.filter(
            Customer.is_deleted.is_(False),
            or_(
                Customer.code.ilike(like),
                Customer.first_name.ilike(like),
                Customer.last_name.ilike(like),
                Customer.national_id.ilike(like),
                Customer.phone_primary.ilike(like),
                Customer.whatsapp.ilike(like),
            ),
        )
        .order_by(Customer.created_at.desc())
        .limit(limit)
        .all()
    )
    deliverers = (
        Deliverer.query.filter(
            Deliverer.is_deleted.is_(False),
            or_(
                Deliverer.code.ilike(like),
                Deliverer.first_name.ilike(like),
                Deliverer.last_name.ilike(like),
                Deliverer.national_id.ilike(like),
                Deliverer.phone.ilike(like),
            ),
        )
        .order_by(Deliverer.created_at.desc())
        .limit(limit)
        .all()
    )
    items = (
        Item.query.filter(
            Item.is_deleted.is_(False),
            or_(
                Item.code.ilike(like),
                Item.barcode.ilike(like),
                Item.qr_code.ilike(like),
                Item.serial_number.ilike(like),
                Item.imei.ilike(like),
                Item.brand.ilike(like),
                Item.model.ilike(like),
                Item.chassis_number.ilike(like),
                Item.plate_number.ilike(like),
            ),
        )
        .order_by(Item.created_at.desc())
        .limit(limit)
        .all()
    )
    return {"customers": customers, "deliverers": deliverers, "articles": items}