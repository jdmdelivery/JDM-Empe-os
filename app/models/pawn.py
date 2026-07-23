"""Contratos de empeño, versiones (snapshot), pagos y renovaciones."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

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

if TYPE_CHECKING:
    from app.models.branch import Branch
    from app.models.customer import Customer
    from app.models.deliverer import Deliverer
    from app.models.item import Item
    from app.models.user import User


class InterestRule(db.Model, TimestampMixin):
    __tablename__ = "interest_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    scope: Mapped[str] = mapped_column(String(40), default="global", nullable=False)
    scope_ref: Mapped[str | None] = mapped_column(String(80), nullable=True)
    percent: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    interest_type: Mapped[str] = mapped_column(String(40), default="simple_mensual", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class FeeRule(db.Model, TimestampMixin):
    __tablename__ = "fee_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    fee_type: Mapped[str] = mapped_column(String(40), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    percent: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Penalty(db.Model, TimestampMixin):
    __tablename__ = "penalties"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    mode: Mapped[str] = mapped_column(String(40), default="mensual", nullable=False)
    percent: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=0, nullable=False)
    fixed_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    days_before_apply: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class PawnContract(db.Model, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "pawn_contracts"
    __table_args__ = (UniqueConstraint("contract_number", name="uq_pawn_contract_number"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    contract_number: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(40), default="activo", nullable=False, index=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    duration_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    grace_days: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    capital: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    capital_balance: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    interest_balance: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    fee_balance: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    late_fee_balance: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    discount_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    percent: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    interest_type: Mapped[str] = mapped_column(String(40), default="simple_mensual", nullable=False)
    frequency: Mapped[str] = mapped_column(String(40), default="mensual", nullable=False)
    interest_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    fees_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    total_due: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    conditions: Mapped[str | None] = mapped_column(Text, nullable=True)
    observations: Mapped[str | None] = mapped_column(Text, nullable=True)
    percent_manual: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    percent_original: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    percent_change_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    percent_authorized_by_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    payment_order: Mapped[str] = mapped_column(
        String(80), default="mora,cargos,interes,capital", nullable=False
    )
    late_percent: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=0, nullable=False)
    late_fixed: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    late_mode: Mapped[str] = mapped_column(String(40), default="mensual", nullable=False)
    declaration_accepted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_payment_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    authorized_for_inventory: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    authorized_inventory_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    authorized_inventory_by_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    renewal_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    parent_contract_id: Mapped[int | None] = mapped_column(
        ForeignKey("pawn_contracts.id"), nullable=True
    )

    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False, index=True)
    deliverer_id: Mapped[int] = mapped_column(ForeignKey("deliverers.id"), nullable=False, index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), nullable=False, index=True)
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id"), nullable=False, index=True)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    customer: Mapped["Customer"] = relationship("Customer", foreign_keys=[customer_id])
    deliverer: Mapped["Deliverer"] = relationship("Deliverer", foreign_keys=[deliverer_id])
    item: Mapped["Item"] = relationship("Item", foreign_keys=[item_id])
    branch: Mapped["Branch"] = relationship("Branch", foreign_keys=[branch_id])
    created_by: Mapped["User | None"] = relationship("User", foreign_keys=[created_by_id])
    versions: Mapped[list["PawnContractVersion"]] = relationship(
        "PawnContractVersion", back_populates="contract", cascade="all, delete-orphan"
    )
    payments: Mapped[list["PawnPayment"]] = relationship(
        "PawnPayment", back_populates="contract", cascade="all, delete-orphan"
    )
    renewals: Mapped[list["Renewal"]] = relationship(
        "Renewal", back_populates="contract", cascade="all, delete-orphan"
    )

    @property
    def pending_total(self) -> Decimal:
        from app.utils.money import money_add

        return money_add(
            self.capital_balance,
            self.interest_balance,
            self.fee_balance,
            self.late_fee_balance,
        )


class PawnContractVersion(db.Model, TimestampMixin):
    """Snapshot inmutable de reglas al crear/renovar."""

    __tablename__ = "pawn_contract_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    contract_id: Mapped[int] = mapped_column(
        ForeignKey("pawn_contracts.id"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    snapshot_json: Mapped[str] = mapped_column(Text, nullable=False)
    approved_by_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    contract: Mapped[PawnContract] = relationship("PawnContract", back_populates="versions")


class PawnPayment(db.Model, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "pawn_payments"
    __table_args__ = (UniqueConstraint("receipt_number", name="uq_pawn_payment_receipt"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    receipt_number: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    idempotency_key: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    payment_type: Mapped[str] = mapped_column(String(40), default="parcial", nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    method: Mapped[str] = mapped_column(String(40), default="efectivo", nullable=False)
    previous_balance: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    new_balance: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    payer_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_voided: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    void_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    paid_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    contract_id: Mapped[int] = mapped_column(
        ForeignKey("pawn_contracts.id"), nullable=False, index=True
    )
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False, index=True)
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id"), nullable=False, index=True)
    received_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    contract: Mapped[PawnContract] = relationship("PawnContract", back_populates="payments")
    allocations: Mapped[list["PawnPaymentAllocation"]] = relationship(
        "PawnPaymentAllocation", back_populates="payment", cascade="all, delete-orphan"
    )


class PawnPaymentAllocation(db.Model, TimestampMixin):
    __tablename__ = "pawn_payment_allocations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    payment_id: Mapped[int] = mapped_column(
        ForeignKey("pawn_payments.id"), nullable=False, index=True
    )
    concept: Mapped[str] = mapped_column(String(40), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)

    payment: Mapped[PawnPayment] = relationship("PawnPayment", back_populates="allocations")


class Renewal(db.Model, TimestampMixin):
    __tablename__ = "renewals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    renewal_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    amount_paid: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    previous_due_date: Mapped[date] = mapped_column(Date, nullable=False)
    new_due_date: Mapped[date] = mapped_column(Date, nullable=False)
    percent_applied: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    renewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    contract_id: Mapped[int] = mapped_column(
        ForeignKey("pawn_contracts.id"), nullable=False, index=True
    )
    payment_id: Mapped[int | None] = mapped_column(ForeignKey("pawn_payments.id"), nullable=True)
    renewed_by_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    branch_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    contract: Mapped[PawnContract] = relationship("PawnContract", back_populates="renewals")