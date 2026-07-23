"""Clientes y datos relacionados."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.mixins import SoftDeleteMixin, TimestampMixin
from app.utils.datetime_utils import utc_now

if TYPE_CHECKING:
    from app.models.branch import Branch
    from app.models.user import User


CUSTOMER_STATUSES = (
    "activo",
    "bloqueado",
    "restringido",
    "en_revision",
    "inactivo",
)


class Customer(db.Model, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    national_id: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    passport: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    other_document: Mapped[str | None] = mapped_column(String(60), nullable=True)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    phone_primary: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    phone_secondary: Mapped[str | None] = mapped_column(String(30), nullable=True)
    whatsapp: Mapped[str | None] = mapped_column(String(30), nullable=True)
    email: Mapped[str | None] = mapped_column(String(120), nullable=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sector: Mapped[str | None] = mapped_column(String(120), nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    province: Mapped[str | None] = mapped_column(String(120), nullable=True)
    country: Mapped[str] = mapped_column(String(80), default="República Dominicana", nullable=False)
    occupation: Mapped[str | None] = mapped_column(String(120), nullable=True)
    workplace: Mapped[str | None] = mapped_column(String(150), nullable=True)
    approximate_income: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    reference_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    reference_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    photo_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    document_front_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    document_back_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    signature_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    internal_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="activo", nullable=False, index=True)
    duplicate_authorized: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    duplicate_authorized_by_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duplicate_authorization_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id"), nullable=False, index=True)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    branch: Mapped["Branch"] = relationship("Branch", foreign_keys=[branch_id])
    created_by: Mapped["User | None"] = relationship("User", foreign_keys=[created_by_id])
    documents: Mapped[list["CustomerDocument"]] = relationship(
        "CustomerDocument", back_populates="customer", cascade="all, delete-orphan"
    )
    references: Mapped[list["CustomerReference"]] = relationship(
        "CustomerReference", back_populates="customer", cascade="all, delete-orphan"
    )

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    def __repr__(self) -> str:
        return f"<Customer {self.code}>"


class CustomerDocument(db.Model, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "customer_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False, index=True)
    document_type: Mapped[str] = mapped_column(String(50), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    original_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    safe_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sha256_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_by_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    customer: Mapped[Customer] = relationship("Customer", back_populates="documents")


class CustomerReference(db.Model, TimestampMixin):
    __tablename__ = "customer_references"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    relationship_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    customer: Mapped[Customer] = relationship("Customer", back_populates="references")