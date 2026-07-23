"""Persona que entrega el artículo."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.mixins import SoftDeleteMixin, TimestampMixin
from app.utils.datetime_utils import utc_now

if TYPE_CHECKING:
    from app.models.branch import Branch
    from app.models.customer import Customer
    from app.models.user import User


class Deliverer(db.Model, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "deliverers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)
    is_same_as_customer: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    national_id: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    passport: Mapped[str | None] = mapped_column(String(40), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    relationship_to_customer: Mapped[str | None] = mapped_column(String(120), nullable=True)
    delivery_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    photo_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    document_front_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    document_back_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    holding_item_photo_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    signature_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    legitimate_origin_accepted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    declaration_accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    declaration_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    observations: Mapped[str | None] = mapped_column(Text, nullable=True)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False, index=True)
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id"), nullable=False, index=True)
    received_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    customer: Mapped["Customer"] = relationship("Customer", foreign_keys=[customer_id])
    branch: Mapped["Branch"] = relationship("Branch", foreign_keys=[branch_id])
    received_by: Mapped["User | None"] = relationship("User", foreign_keys=[received_by_id])
    documents: Mapped[list["DelivererDocument"]] = relationship(
        "DelivererDocument", back_populates="deliverer", cascade="all, delete-orphan"
    )
    signatures: Mapped[list["DelivererSignature"]] = relationship(
        "DelivererSignature", back_populates="deliverer", cascade="all, delete-orphan"
    )

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    def __repr__(self) -> str:
        return f"<Deliverer {self.code}>"


class DelivererDocument(db.Model, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "deliverer_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    deliverer_id: Mapped[int] = mapped_column(
        ForeignKey("deliverers.id"), nullable=False, index=True
    )
    document_type: Mapped[str] = mapped_column(String(50), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    safe_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sha256_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    uploaded_by_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    deliverer: Mapped[Deliverer] = relationship("Deliverer", back_populates="documents")


class DelivererSignature(db.Model, TimestampMixin):
    __tablename__ = "deliverer_signatures"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    deliverer_id: Mapped[int] = mapped_column(
        ForeignKey("deliverers.id"), nullable=False, index=True
    )
    signature_type: Mapped[str] = mapped_column(String(50), default="deliverer", nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    sha256_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    accepted_declaration: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    accepted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    captured_by_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    deliverer: Mapped[Deliverer] = relationship("Deliverer", back_populates="signatures")