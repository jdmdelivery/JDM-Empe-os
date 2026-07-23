"""Artículos, categorías, imágenes y evaluaciones."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.mixins import SoftDeleteMixin, TimestampMixin
from app.utils.datetime_utils import utc_now

if TYPE_CHECKING:
    from app.models.branch import Branch
    from app.models.customer import Customer
    from app.models.deliverer import Deliverer
    from app.models.user import User


ITEM_STATUSES = (
    "en_evaluacion",
    "pendiente_documentacion",
    "empenado",
    "renovado",
    "pagado",
    "pendiente_retiro",
    "retirado",
    "vencido",
    "en_periodo_gracia",
    "pendiente_autorizacion",
    "autorizado_inventario",
    "disponible_venta",
    "reservado",
    "vendido",
    "devuelto",
    "danado",
    "en_reparacion",
    "transferido",
    "perdido",
    "bloqueado",
    "eliminado_logicamente",
)


class ItemCategory(db.Model, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "item_categories"
    __table_args__ = (UniqueConstraint("code", name="uq_item_categories_code"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("item_categories.id"), nullable=True, index=True
    )
    requires_imei: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    requires_serial: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_vehicle: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    parent: Mapped["ItemCategory | None"] = relationship(
        "ItemCategory", remote_side="ItemCategory.id"
    )
    items: Mapped[list["Item"]] = relationship(
        "Item",
        back_populates="category",
        foreign_keys="Item.category_id",
    )

    def __repr__(self) -> str:
        return f"<ItemCategory {self.code}>"


class Item(db.Model, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False, index=True)
    barcode: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    qr_code: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    brand: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    serial_number: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    imei: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    chassis_number: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    plate_number: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    color: Mapped[str | None] = mapped_column(String(60), nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    physical_condition: Mapped[str | None] = mapped_column(String(80), nullable=True)
    functional_condition: Mapped[str | None] = mapped_column(String(80), nullable=True)
    damages: Mapped[str | None] = mapped_column(Text, nullable=True)
    scratches: Mapped[str | None] = mapped_column(Text, nullable=True)
    missing_parts: Mapped[str | None] = mapped_column(Text, nullable=True)
    accessories: Mapped[str | None] = mapped_column(Text, nullable=True)
    estimated_value: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    purchase_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    loan_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    min_sale_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    sale_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    location: Mapped[str | None] = mapped_column(String(120), nullable=True)
    shelf: Mapped[str | None] = mapped_column(String(60), nullable=True)
    warehouse: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(
        String(40), default="en_evaluacion", nullable=False, index=True
    )
    duplicate_authorized: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    duplicate_authorized_by_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duplicate_authorization_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    video_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    observations: Mapped[str | None] = mapped_column(Text, nullable=True)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("item_categories.id"), nullable=True, index=True
    )
    subcategory_id: Mapped[int | None] = mapped_column(
        ForeignKey("item_categories.id"), nullable=True
    )
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id"), nullable=False, index=True)
    customer_id: Mapped[int | None] = mapped_column(
        ForeignKey("customers.id"), nullable=True, index=True
    )
    deliverer_id: Mapped[int | None] = mapped_column(
        ForeignKey("deliverers.id"), nullable=True, index=True
    )
    received_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    category: Mapped["ItemCategory | None"] = relationship(
        "ItemCategory", foreign_keys=[category_id], back_populates="items"
    )
    subcategory: Mapped["ItemCategory | None"] = relationship(
        "ItemCategory", foreign_keys=[subcategory_id]
    )
    branch: Mapped["Branch"] = relationship("Branch", foreign_keys=[branch_id])
    customer: Mapped["Customer | None"] = relationship("Customer", foreign_keys=[customer_id])
    deliverer: Mapped["Deliverer | None"] = relationship("Deliverer", foreign_keys=[deliverer_id])
    received_by: Mapped["User | None"] = relationship("User", foreign_keys=[received_by_id])
    images: Mapped[list["ItemImage"]] = relationship(
        "ItemImage", back_populates="item", cascade="all, delete-orphan"
    )
    evaluations: Mapped[list["ItemEvaluation"]] = relationship(
        "ItemEvaluation", back_populates="item", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Item {self.code}>"


class ItemImage(db.Model, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "item_images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), nullable=False, index=True)
    image_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
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
    customer_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    deliverer_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    item: Mapped[Item] = relationship("Item", back_populates="images")


class ItemEvaluation(db.Model, TimestampMixin):
    __tablename__ = "item_evaluations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), nullable=False, index=True)
    new_value_approx: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    used_value_approx: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    physical_condition: Mapped[str | None] = mapped_column(String(80), nullable=True)
    functional_condition: Mapped[str | None] = mapped_column(String(80), nullable=True)
    recommended_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    max_loan_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    suggested_value: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    approved_value: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    risk_level: Mapped[str | None] = mapped_column(String(40), nullable=True)
    sale_ease: Mapped[str | None] = mapped_column(String(40), nullable=True)
    demand_level: Mapped[str | None] = mapped_column(String(40), nullable=True)
    evaluator_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    change_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    evaluated_by_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    approved_by_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    item: Mapped[Item] = relationship("Item", back_populates="evaluations")