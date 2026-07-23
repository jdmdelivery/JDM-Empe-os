"""Categorías de artículos predeterminadas."""

from __future__ import annotations

from app.extensions import db
from app.models import ItemCategory

DEFAULT_CATEGORIES: list[dict] = [
    {"code": "celulares", "name": "Celulares", "requires_imei": True, "requires_serial": True},
    {"code": "computadoras", "name": "Computadoras", "requires_serial": True},
    {"code": "tabletas", "name": "Tabletas", "requires_serial": True},
    {"code": "televisores", "name": "Televisores", "requires_serial": True},
    {"code": "consolas", "name": "Consolas", "requires_serial": True},
    {"code": "herramientas", "name": "Herramientas"},
    {"code": "electrodomesticos", "name": "Electrodomésticos"},
    {"code": "joyas", "name": "Joyas", "requires_serial": False},
    {"code": "oro", "name": "Oro", "requires_serial": False},
    {"code": "plata", "name": "Plata", "requires_serial": False},
    {"code": "relojes", "name": "Relojes"},
    {"code": "bocinas", "name": "Bocinas"},
    {"code": "camaras", "name": "Cámaras", "requires_serial": True},
    {"code": "bicicletas", "name": "Bicicletas", "requires_serial": True},
    {
        "code": "motocicletas",
        "name": "Motocicletas",
        "requires_serial": True,
        "is_vehicle": True,
    },
    {
        "code": "vehiculos",
        "name": "Vehículos",
        "requires_serial": True,
        "is_vehicle": True,
    },
    {"code": "equipos_comerciales", "name": "Equipos comerciales"},
    {"code": "otros", "name": "Otros"},
]


def seed_item_categories() -> None:
    for idx, item in enumerate(DEFAULT_CATEGORIES):
        category = ItemCategory.query.filter_by(code=item["code"]).first()
        if category is None:
            category = ItemCategory(
                code=item["code"],
                name=item["name"],
                requires_imei=bool(item.get("requires_imei", False)),
                requires_serial=bool(item.get("requires_serial", True)),
                is_vehicle=bool(item.get("is_vehicle", False)),
                is_active=True,
                sort_order=idx,
            )
            db.session.add(category)
        else:
            category.name = item["name"]
            category.requires_imei = bool(item.get("requires_imei", False))
            category.requires_serial = bool(item.get("requires_serial", True))
            category.is_vehicle = bool(item.get("is_vehicle", False))
            category.sort_order = idx
    db.session.commit()