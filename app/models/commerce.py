"""Compras directas, ventas, reservas, devoluciones y garantías."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.mixins import SoftDeleteMixin, TimestampMixin
from app.utils.datetime_utils import utc_now


class DirectPurchase(db.Model, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "direct_purchases"
    __table_args__ = (UniqueConstraint("purchase_number", name="uq_direct_purchase_number"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    purchase_number: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    estimated_value: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    negotiated_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    paid_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    payment_method: Mapped[str] = mapped_column(String(40), default="efectivo", nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="disponible_venta", nullable=False)
    observations: Mapped[str | None] = mapped_column(Text, nullable=True)
    declaration_accepted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    purchased_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False, index=True)
    deliverer_id: Mapped[int] = mapped_column(ForeignKey("deliverers.id"), nullable=False, index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), nullable=False, index=True)
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id"), nullable=False, index=True)
    buyer_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    customer = relationship("Customer", foreign_keys=[customer_id])
    deliverer = relationship("Deliverer", foreign_keys=[deliverer_id])
    item = relationship("Item", foreign_keys=[item_id])
    branch = relationship("Branch", foreign_keys=[branch_id])


class Sale(db.Model, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "sales"
    __table_args__ = (UniqueConstraint("invoice_number", name="uq_sales_invoice"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    invoice_number: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    discount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    tax: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    payment_method: Mapped[str] = mapped_column(String(40), default="efectivo", nullable=False)
    cash_received: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    change_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="completada", nullable=False)
    warranty_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    warranty_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    conditions: Mapped[str | None] = mapped_column(Text, nullable=True)
    sold_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id"), nullable=True)
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id"), nullable=False, index=True)
    seller_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    customer = relationship("Customer", foreign_keys=[customer_id])
    branch = relationship("Branch", foreign_keys=[branch_id])
    items: Mapped[list["SaleItem"]] = relationship(
        "SaleItem", back_populates="sale", cascade="all, delete-orphan"
    )
    payments: Mapped[list["SalePayment"]] = relationship(
        "SalePayment", back_populates="sale", cascade="all, delete-orphan"
    )


class SaleItem(db.Model, TimestampMixin):
    __tablename__ = "sale_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sale_id: Mapped[int] = mapped_column(ForeignKey("sales.id"), nullable=False, index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), nullable=False, index=True)
    original_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    discount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    final_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)

    sale: Mapped[Sale] = relationship("Sale", back_populates="items")
    item = relationship("Item", foreign_keys=[item_id])


class SalePayment(db.Model, TimestampMixin):
    __tablename__ = "sale_payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sale_id: Mapped[int] = mapped_column(ForeignKey("sales.id"), nullable=False, index=True)
    method: Mapped[str] = mapped_column(String(40), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    reference: Mapped[str | None] = mapped_column(String(120), nullable=True)

    sale: Mapped[Sale] = relationship("Sale", back_populates="payments")


class Reservation(db.Model, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "reservations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), nullable=False, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False)
    deposit: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="activa", nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    branch_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_by_id: Mapped[int | None] = mapped_column(Integer, nullable=True)


class ReturnRecord(db.Model, TimestampMixin):
    __tablename__ = "returns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sale_id: Mapped[int] = mapped_column(ForeignKey("sales.id"), nullable=False, index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    refund_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    authorized_by_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    returned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class Warranty(db.Model, TimestampMixin):
    __tablename__ = "warranties"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sale_id: Mapped[int] = mapped_column(ForeignKey("sales.id"), nullable=False, index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), nullable=False)
    certificate_number: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    starts_on: Mapped[date] = mapped_column(Date, nullable=False)
    ends_on: Mapped[date] = mapped_column(Date, nullable=False)
    terms: Mapped[str | None] = mapped_column(Text, nullable=True)


class Transfer(db.Model, TimestampMixin):
    __tablename__ = "transfers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), nullable=False, index=True)
    from_branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id"), nullable=False)
    to_branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="enviado", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    sent_by_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    received_by_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ItemMovement(db.Model, TimestampMixin):
    __tablename__ = "item_movements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), nullable=False, index=True)
    movement_type: Mapped[str] = mapped_column(String(40), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    to_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    reference: Mapped[str | None] = mapped_column(String(80), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    branch_id: Mapped[int | None] = mapped_column(Integer, nullable=True)