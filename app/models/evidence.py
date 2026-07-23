"""Evidencias fotográficas, firmas y excepciones."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db
from app.models.mixins import SoftDeleteMixin, TimestampMixin
from app.utils.datetime_utils import utc_now


class EvidenceFile(db.Model, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "evidence_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    uuid: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, index=True)
    evidence_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    related_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    related_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    customer_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    deliverer_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    item_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    contract_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    purchase_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    safe_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sha256_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(30), default="activo", nullable=False)
    deletion_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    captured_by_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    branch_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    def __repr__(self) -> str:
        return f"<EvidenceFile {self.uuid}>"


class OperationSignature(db.Model, TimestampMixin):
    __tablename__ = "operation_signatures"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    signer_role: Mapped[str] = mapped_column(String(40), nullable=False)
    related_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    related_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    customer_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    deliverer_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    sha256_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    declaration_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    accepted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    captured_by_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    branch_id: Mapped[int | None] = mapped_column(Integer, nullable=True)


class OperationException(db.Model, TimestampMixin):
    __tablename__ = "operation_exceptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    exception_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    related_type: Mapped[str] = mapped_column(String(60), nullable=False)
    related_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    missing_item: Mapped[str | None] = mapped_column(String(120), nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    authorized_by_id: Mapped[int] = mapped_column(Integer, nullable=False)
    authorized_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    branch_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)