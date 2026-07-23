"""Repositorio de usuarios."""

from __future__ import annotations

from app.extensions import db
from app.models import User


class UserRepository:
    @staticmethod
    def get_by_id(user_id: int) -> User | None:
        return db.session.get(User, user_id)

    @staticmethod
    def list_active(branch_id: int | None = None) -> list[User]:
        query = User.query.filter_by(is_deleted=False)
        if branch_id is not None:
            query = query.filter_by(branch_id=branch_id)
        return query.order_by(User.first_name.asc(), User.last_name.asc()).all()

    @staticmethod
    def username_exists(username: str, exclude_id: int | None = None) -> bool:
        query = User.query.filter(User.username == username)
        if exclude_id:
            query = query.filter(User.id != exclude_id)
        return query.first() is not None

    @staticmethod
    def email_exists(email: str, exclude_id: int | None = None) -> bool:
        query = User.query.filter(User.email == email)
        if exclude_id:
            query = query.filter(User.id != exclude_id)
        return query.first() is not None

    @staticmethod
    def save(user: User) -> User:
        db.session.add(user)
        db.session.commit()
        return user