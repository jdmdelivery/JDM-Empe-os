"""Pruebas Fase 2: clientes, deliverers, artículos, hash y búsqueda."""

from __future__ import annotations

from io import BytesIO

from app.extensions import db
from app.models import Customer, Deliverer, Item, ItemCategory
from app.services.category_seed import seed_item_categories
from app.services.file_storage import compute_sha256
from app.services.numbering import next_customer_code, next_item_code
from app.services.search_service import global_search
from app.services.seed_service import ensure_superadmin


def _login(client, app):
    with app.app_context():
        ensure_superadmin(
            username="superadmin",
            email="admin@example.com",
            password="TestPass123!",
            must_change_password=False,
        )
        seed_item_categories()
    return client.post(
        "/login",
        data={"username": "superadmin", "password": "TestPass123!"},
        follow_redirects=True,
    )


def test_numbering_and_hash():
    assert next_customer_code(None).startswith("CLI-")
    assert next_item_code("ART-2026-000001") == "ART-2026-000002"
    assert len(compute_sha256(b"hola")) == 64


def test_create_customer(client, app):
    _login(client, app)
    response = client.post(
        "/customers/create",
        data={
            "first_name": "Juan",
            "last_name": "Diaz",
            "national_id": "00112345678",
            "phone_primary": "8095551212",
            "country": "Republica Dominicana",
            "status": "activo",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        customer = Customer.query.filter_by(national_id="00112345678").first()
        assert customer is not None
        assert customer.code.startswith("CLI-")


def test_duplicate_customer_requires_auth(client, app):
    _login(client, app)
    payload = {
        "first_name": "Maria",
        "last_name": "Lopez",
        "national_id": "00199998888",
        "phone_primary": "8095559999",
        "status": "activo",
        "country": "Republica Dominicana",
    }
    client.post("/customers/create", data=payload, follow_redirects=True)
    response = client.post("/customers/create", data=payload, follow_redirects=True)
    assert b"duplic" in response.data.lower() or "duplic".encode() in response.data.lower()


def test_create_item_and_duplicate_serial(client, app):
    _login(client, app)
    with app.app_context():
        seed_item_categories()
        category = ItemCategory.query.filter_by(code="celulares").first()
        category_id = category.id

    response = client.post(
        "/items/create",
        data={
            "category_id": str(category_id),
            "customer_id": "0",
            "deliverer_id": "0",
            "brand": "Samsung",
            "model": "A54",
            "serial_number": "SN-TEST-001",
            "imei": "356938035643809",
            "status": "en_evaluacion",
            "estimated_value": "15000.00",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        item = Item.query.filter_by(serial_number="SN-TEST-001").first()
        assert item is not None

    blocked = client.post(
        "/items/create",
        data={
            "category_id": str(category_id),
            "customer_id": "0",
            "deliverer_id": "0",
            "brand": "Samsung",
            "model": "A54",
            "serial_number": "SN-TEST-001",
            "status": "en_evaluacion",
        },
        follow_redirects=True,
    )
    assert b"autoriz" in blocked.data.lower() or b"duplic" in blocked.data.lower()


def test_global_search(client, app):
    _login(client, app)
    with app.app_context():
        from app.models import Branch

        branch = Branch.query.filter_by(is_main=True).first()
        customer = Customer(
            code="CLI-2026-000099",
            first_name="Pedro",
            last_name="Busqueda",
            national_id="00222223333",
            phone_primary="8091112233",
            branch_id=branch.id,
            status="activo",
        )
        db.session.add(customer)
        db.session.commit()
        results = global_search("Busqueda")
        assert len(results["customers"]) >= 1

    response = client.get("/search?q=Pedro", follow_redirects=True)
    assert response.status_code == 200
    assert b"Pedro" in response.data


def test_categories_seeded(app):
    with app.app_context():
        seed_item_categories()
        assert ItemCategory.query.count() >= 10
        assert ItemCategory.query.filter_by(code="celulares").first().requires_imei is True