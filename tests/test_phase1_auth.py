"""Pruebas Fase 1: autenticación, roles y seguridad."""

from __future__ import annotations

from app.extensions import db
from app.models import Role, User
from app.services.auth_service import authenticate
from app.services.seed_service import ensure_superadmin
from app.utils.money import format_money, percent_of, to_decimal


def test_healthz(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_login_page(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert b"Iniciar sesi" in response.data or "Iniciar sesión".encode("utf-8") in response.data


def test_login_success(client, app):
    with app.app_context():
        ensure_superadmin(
            username="superadmin",
            email="admin@example.com",
            password="TestPass123!",
            must_change_password=False,
        )
    response = client.post(
        "/login",
        data={"username": "superadmin", "password": "TestPass123!"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Panel" in response.data or "Panel principal".encode("utf-8") in response.data


def test_login_failure_and_lockout(app):
    with app.app_context():
        user = ensure_superadmin(
            username="lockuser",
            email="lock@example.com",
            password="TestPass123!",
            must_change_password=False,
        )
        app.config["LOGIN_MAX_ATTEMPTS"] = 3
        app.config["LOGIN_LOCKOUT_MINUTES"] = 15

        for _ in range(3):
            ok, _msg, _u = authenticate("lockuser", "wrong")
            assert ok is False

        db.session.refresh(user)
        assert user.is_locked is True


def test_permissions_superadmin(app):
    with app.app_context():
        user = ensure_superadmin(
            username="superadmin",
            email="admin@example.com",
            password="TestPass123!",
            must_change_password=False,
        )
        assert user.has_permission("branches.manage")
        assert user.has_permission("settings.manage")
        assert user.has_role("superadmin")


def test_cashier_cannot_manage_branches(app, client):
    with app.app_context():
        ensure_superadmin(
            username="superadmin",
            email="admin@example.com",
            password="TestPass123!",
            must_change_password=False,
        )
        role = Role.query.filter_by(code="cashier").first()
        cashier = User(
            username="cajero1",
            email="cajero@example.com",
            first_name="Cajero",
            last_name="Uno",
            role_id=role.id,
            account_active=True,
            must_change_password=False,
        )
        cashier.set_password("TestPass123!")
        db.session.add(cashier)
        db.session.commit()

    client.post(
        "/login",
        data={"username": "cajero1", "password": "TestPass123!"},
        follow_redirects=True,
    )
    response = client.get("/branches/create", follow_redirects=True)
    assert response.status_code in {403, 200}
    # Backend debe denegar: 403 o redirección sin acceso a formulario de creación privilegiada
    if response.status_code == 200:
        assert b"Nueva sucursal" not in response.data or b"403" in response.data or b"denegado" in response.data.lower()


def test_money_decimal_helpers():
    assert to_decimal("10.5") == to_decimal("10.50")
    assert percent_of("10000", "12") == to_decimal("1200.00")
    assert format_money("1000.5", "RD$").startswith("RD$")
    assert "float" not in type(percent_of(100, 10)).__name__.lower()


def test_dashboard_requires_login(client):
    response = client.get("/dashboard/", follow_redirects=False)
    assert response.status_code in {302, 401}