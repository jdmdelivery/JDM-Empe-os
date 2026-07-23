"""Inicialización de datos base del sistema."""

from __future__ import annotations

from app.extensions import db
from app.models import Branch, Permission, Role, Setting, User
from app.services.permissions_seed import (
    DEFAULT_SETTINGS,
    PERMISSIONS,
    ROLE_PERMISSIONS,
    ROLES,
)


def seed_permissions_and_roles() -> None:
    permission_map: dict[str, Permission] = {}
    for item in PERMISSIONS:
        permission = Permission.query.filter_by(code=item["code"]).first()
        if permission is None:
            permission = Permission(
                code=item["code"],
                name=item["name"],
                module=item["module"],
                description=item.get("description"),
            )
            db.session.add(permission)
        else:
            permission.name = item["name"]
            permission.module = item["module"]
        permission_map[item["code"]] = permission

    db.session.flush()

    for role_data in ROLES:
        role = Role.query.filter_by(code=role_data["code"]).first()
        if role is None:
            role = Role(
                code=role_data["code"],
                name=role_data["name"],
                description=role_data.get("description"),
                is_system=True,
            )
            db.session.add(role)
            db.session.flush()
        else:
            role.name = role_data["name"]
            role.description = role_data.get("description")

        codes = ROLE_PERMISSIONS.get(role_data["code"], [])
        if "*" in codes:
            role.permissions = list(permission_map.values())
        else:
            role.permissions = [permission_map[code] for code in codes if code in permission_map]

    db.session.commit()


def seed_default_settings() -> None:
    for item in DEFAULT_SETTINGS:
        setting = Setting.query.filter_by(key=item["key"]).first()
        if setting is None:
            db.session.add(
                Setting(
                    key=item["key"],
                    value=item.get("value", ""),
                    value_type=item.get("value_type", "string"),
                    category=item.get("category", "general"),
                    label=item.get("label"),
                    description=item.get("description"),
                    is_public=bool(item.get("is_public", False)),
                )
            )
    db.session.commit()


def ensure_main_branch() -> Branch:
    branch = Branch.query.filter_by(is_main=True, is_deleted=False).first()
    if branch is None:
        branch = Branch(
            code="SUC-001",
            name="Sucursal Principal",
            city="Santo Domingo",
            province="Distrito Nacional",
            country="República Dominicana",
            is_active=True,
            is_main=True,
        )
        db.session.add(branch)
        db.session.commit()
    return branch


def ensure_superadmin(
    *,
    username: str = "superadmin",
    email: str = "admin@example.com",
    password: str = "Cambiar123!",
    first_name: str = "Super",
    last_name: str = "Administrador",
    must_change_password: bool = True,
) -> User:
    seed_permissions_and_roles()
    seed_default_settings()
    branch = ensure_main_branch()
    role = Role.query.filter_by(code="superadmin").first()
    if role is None:
        raise RuntimeError("No se pudo crear el rol superadmin.")

    user = User.query.filter(
        (User.username == username) | (User.email == email)
    ).first()
    if user is None:
        user = User(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            role_id=role.id,
            branch_id=branch.id,
            account_active=True,
            must_change_password=must_change_password,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
    return user


def bootstrap_phase1() -> None:
    seed_permissions_and_roles()
    seed_default_settings()
    ensure_main_branch()


def bootstrap_phase2() -> None:
    bootstrap_phase1()
    from app.services.category_seed import seed_item_categories

    seed_item_categories()