"""Mixins comunes para modelos."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.utils.datetime_utils import utc_now


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )


class SoftDeleteMixin:
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Sin FK para evitar dependencia circular branches <-> users.
    deleted_by_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    def soft_delete(self, user_id: int | None = None) -> None:
        self.is_deleted = True
        self.deleted_at = utc_now()
        self.deleted_by_id = user_id

    def restore(self) -> None:
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by_id = None


class ActiveMixin:
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)