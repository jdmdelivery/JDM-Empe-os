"""Repositorio de sucursales."""

from __future__ import annotations

from app.extensions import db
from app.models import Branch


class BranchRepository:
    @staticmethod
    def get_by_id(branch_id: int) -> Branch | None:
        return db.session.get(Branch, branch_id)

    @staticmethod
    def list_all(include_inactive: bool = True) -> list[Branch]:
        query = Branch.query.filter_by(is_deleted=False)
        if not include_inactive:
            query = query.filter_by(is_active=True)
        return query.order_by(Branch.name.asc()).all()

    @staticmethod
    def code_exists(code: str, exclude_id: int | None = None) -> bool:
        query = Branch.query.filter(Branch.code == code, Branch.is_deleted.is_(False))
        if exclude_id:
            query = query.filter(Branch.id != exclude_id)
        return query.first() is not None

    @staticmethod
    def save(branch: Branch) -> Branch:
        db.session.add(branch)
        db.session.commit()
        return branch