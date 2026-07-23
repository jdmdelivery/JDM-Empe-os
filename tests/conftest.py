"""Fixtures de pruebas."""

from __future__ import annotations

import pytest

from app import create_app
from app.extensions import db
from app.services.category_seed import seed_item_categories
from app.services.seed_service import ensure_superadmin, seed_permissions_and_roles


@pytest.fixture()
def app():
    application = create_app("testing")
    with application.app_context():
        db.create_all()
        seed_permissions_and_roles()
        seed_item_categories()
        ensure_superadmin(
            username="superadmin",
            email="admin@example.com",
            password="TestPass123!",
            must_change_password=False,
        )
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def auth_client(client):
    response = client.post(
        "/login",
        data={
            "username": "superadmin",
            "password": "TestPass123!",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    return client