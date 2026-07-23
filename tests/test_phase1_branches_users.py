"""Pruebas Fase 1: sucursales, usuarios y configuración."""

from __future__ import annotations

from app.models import Branch, Setting
from app.services.seed_service import ensure_superadmin


def _login_super(client, app):
    with app.app_context():
        ensure_superadmin(
            username="superadmin",
            email="admin@example.com",
            password="TestPass123!",
            must_change_password=False,
        )
    return client.post(
        "/login",
        data={"username": "superadmin", "password": "TestPass123!"},
        follow_redirects=True,
    )


def test_create_branch(client, app):
    _login_super(client, app)
    response = client.post(
        "/branches/create",
        data={
            "code": "SUC-010",
            "name": "Sucursal Norte",
            "city": "Santiago",
            "country": "Republica Dominicana",
            "is_active": "y",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        branch = Branch.query.filter_by(code="SUC-010").first()
        assert branch is not None
        assert branch.name == "Sucursal Norte"


def test_create_user(client, app):
    _login_super(client, app)
    with app.app_context():
        from app.models import Role

        role = Role.query.filter_by(code="admin").first()
        branch = Branch.query.filter_by(is_main=True).first()
        role_id = role.id
        branch_id = branch.id

    response = client.post(
        "/users/create",
        data={
            "username": "admin.norte",
            "email": "admin.norte@example.com",
            "first_name": "Ana",
            "last_name": "Perez",
            "role_id": str(role_id),
            "branch_id": str(branch_id),
            "password": "TestPass123!",
            "password2": "TestPass123!",
            "account_active": "y",
            "must_change_password": "y",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Usuario creado correctamente" in response.data
    with app.app_context():
        from app.models import User

        user = User.query.filter_by(username="admin.norte").first()
        assert user is not None
        assert user.role.code == "admin"


def test_settings_update(client, app):
    _login_super(client, app)
    response = client.post(
        "/settings/",
        data={
            "business_name": "JDM Empenos RD",
            "business_rnc": "123",
            "currency_symbol": "RD$",
            "timezone": "America/Santo_Domingo",
            "default_interest_percent": "12",
            "default_grace_days": "5",
            "default_duration_days": "30",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        setting = Setting.query.filter_by(key="business_name").first()
        assert setting is not None
        assert setting.value == "JDM Empenos RD"
        symbol = Setting.query.filter_by(key="currency_symbol").first()
        assert symbol.value == "RD$"


def test_audit_page(client, app):
    _login_super(client, app)
    response = client.get("/audit/")
    assert response.status_code == 200
    assert "Auditor".encode("utf-8") in response.data
