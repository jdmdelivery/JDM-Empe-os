"""Usuarios del sistema."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from flask_login import UserMixin
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db, login_manager
from app.models.mixins import SoftDeleteMixin, TimestampMixin
from app.utils.datetime_utils import utc_now

if TYPE_CHECKING:
    from app.models.branch import Branch
    from app.models.role import Role


class User(UserMixin, db.Model, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    # Columna real; Flask-Login usa la propiedad is_active más abajo.
    account_active: Mapped[bool] = mapped_column(
        "is_active", Boolean, default=True, nullable=False, index=True
    )
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    password_reset_token: Mapped[str | None] = mapped_column(String(120), nullable=True)
    password_reset_expires: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"), nullable=False, index=True)
    branch_id: Mapped[int | None] = mapped_column(
        ForeignKey("branches.id"), nullable=True, index=True
    )

    role: Mapped["Role"] = relationship("Role", back_populates="users", lazy="joined")
    branch: Mapped["Branch | None"] = relationship("Branch", back_populates="users", lazy="joined")

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def is_locked(self) -> bool:
        if self.locked_until is None:
            return False
        locked_until = self.locked_until
        # SQLite puede devolver datetimes naive tras persistir.
        if locked_until.tzinfo is None:
            locked_until = locked_until.replace(tzinfo=timezone.utc)
        return locked_until > utc_now()

    @property
    def is_active_user(self) -> bool:
        return bool(self.account_active) and not self.is_deleted and not self.is_locked

    @property
    def is_active(self) -> bool:  # type: ignore[override]
        """Usado por Flask-Login para permitir o denegar la sesión."""
        return self.is_active_user

    def get_id(self) -> str:
        return str(self.id)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def register_failed_login(self, max_attempts: int, lockout_minutes: int) -> None:
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= max_attempts:
            self.locked_until = utc_now() + timedelta(minutes=lockout_minutes)

    def clear_failed_logins(self) -> None:
        self.failed_login_attempts = 0
        self.locked_until = None

    def has_permission(self, code: str) -> bool:
        if self.role is None:
            return False
        if self.role.code == "superadmin":
            return True
        return self.role.has_permission(code)

    def has_any_permission(self, *codes: str) -> bool:
        return any(self.has_permission(code) for code in codes)

    def has_role(self, *codes: str) -> bool:
        return self.role is not None and self.role.code in codes

    def can_access_branch(self, branch_id: int | None) -> bool:
        if self.has_role("superadmin", "auditor"):
            return True
        if branch_id is None:
            return False
        return self.branch_id == branch_id

    def __repr__(self) -> str:
        return f"<User {self.username}>"


@login_manager.user_loader
def load_user(user_id: str) -> User | None:
    if not user_id:
        return None
    try:
        return db.session.get(User, int(user_id))
    except Exception:
        # BD no migrada o sesión inválida (común en el primer deploy de Render)
        return None