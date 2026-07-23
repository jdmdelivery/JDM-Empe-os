"""Caja, gastos e ingresos."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
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


class CashRegister(db.Model, TimestampMixin):
    __tablename__ = "cash_registers"
    __table_args__ = (UniqueConstraint("code", "branch_id", name="uq_cash_register_branch"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(30), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id"), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    branch = relationship("Branch", foreign_keys=[branch_id])
    sessions: Mapped[list["CashSession"]] = relationship("CashSession", back_populates="register")


class CashSession(db.Model, TimestampMixin):
    __tablename__ = "cash_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    register_id: Mapped[int] = mapped_column(
        ForeignKey("cash_registers.id"), nullable=False, index=True
    )
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id"), nullable=False, index=True)
    opened_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    closed_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    opening_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    closing_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    expected_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    difference_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="abierta", nullable=False, index=True)
    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    register: Mapped[CashRegister] = relationship("CashRegister", back_populates="sessions")
    movements: Mapped[list["CashMovement"]] = relationship(
        "CashMovement", back_populates="session", cascade="all, delete-orphan"
    )


class CashMovement(db.Model, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "cash_movements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("cash_sessions.id"), nullable=False, index=True
    )
    movement_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    concept: Mapped[str] = mapped_column(String(150), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    method: Mapped[str] = mapped_column(String(40), default="efectivo", nullable=False)
    reference: Mapped[str | None] = mapped_column(String(80), nullable=True)
    related_type: Mapped[str | None] = mapped_column(String(60), nullable=True)
    related_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="activo", nullable=False)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    branch_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    moved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    session: Mapped[CashSession] = relationship("CashSession", back_populates="movements")


class ExpenseCategory(db.Model, TimestampMixin):
    __tablename__ = "expense_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Expense(db.Model, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entry_type: Mapped[str] = mapped_column(String(20), default="gasto", nullable=False)  # gasto|ingreso
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("expense_categories.id"), nullable=True
    )
    concept: Mapped[str] = mapped_column(String(200), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    method: Mapped[str] = mapped_column(String(40), default="efectivo", nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="aprobado", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    receipt_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id"), nullable=False, index=True)
    created_by_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    approved_by_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    category = relationship("ExpenseCategory", foreign_keys=[category_id])
    branch = relationship("Branch", foreign_keys=[branch_id])