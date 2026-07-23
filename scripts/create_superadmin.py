"""Crea o verifica el superadministrador inicial."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from app import create_app
from app.services.seed_service import ensure_superadmin


def main() -> None:
    parser = argparse.ArgumentParser(description="Crear superadministrador de JDM Empeños")
    parser.add_argument("--username", default=os.getenv("SUPERADMIN_USERNAME", "superadmin"))
    parser.add_argument("--email", default=os.getenv("SUPERADMIN_EMAIL", "admin@example.com"))
    parser.add_argument("--password", default=os.getenv("SUPERADMIN_PASSWORD", "Cambiar123!"))
    parser.add_argument("--first-name", default="Super")
    parser.add_argument("--last-name", default="Administrador")
    args = parser.parse_args()

    app = create_app(os.getenv("FLASK_ENV", "development"))
    with app.app_context():
        from app.extensions import db

        db.create_all()
        user = ensure_superadmin(
            username=args.username,
            email=args.email,
            password=args.password,
            first_name=args.first_name,
            last_name=args.last_name,
        )
        print("Superadministrador listo:")
        print(f"  Usuario: {user.username}")
        print(f"  Correo:  {user.email}")
        print("  Nota: cambie la contraseña al iniciar sesión.")


if __name__ == "__main__":
    main()