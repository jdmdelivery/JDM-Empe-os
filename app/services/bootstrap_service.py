"""Bootstrap de base de datos para deploys (Render)."""

from __future__ import annotations

import logging
import os

from flask import Flask

logger = logging.getLogger(__name__)


def bootstrap_database(app: Flask) -> None:
    """Aplica migraciones y datos base. Seguro llamar más de una vez."""
    with app.app_context():
        try:
            from flask_migrate import upgrade

            upgrade()
            logger.info("Migraciones aplicadas correctamente.")
        except Exception:
            logger.exception("flask db upgrade falló; intentando create_all()")
            from app.extensions import db

            db.create_all()

        try:
            from app.services.seed_service import bootstrap_phase2, ensure_superadmin

            bootstrap_phase2()
            username = (os.getenv("SUPERADMIN_USERNAME") or "").strip()
            password = (os.getenv("SUPERADMIN_PASSWORD") or "").strip()
            email = (os.getenv("SUPERADMIN_EMAIL") or "admin@example.com").strip()
            if username and password:
                ensure_superadmin(
                    username=username,
                    email=email,
                    password=password,
                    first_name="JDM",
                    last_name="Admin",
                    must_change_password=False,
                    update_password=True,
                )
                logger.info("Superadmin asegurado: %s", username)
            else:
                # Usuario por defecto solo si no hay ninguno
                from app.models import User

                if User.query.filter_by(is_deleted=False).count() == 0:
                    ensure_superadmin(must_change_password=True)
                    logger.info("Superadmin por defecto creado.")
        except Exception:
            logger.exception("Seed / superadmin falló")
