"""Copias de seguridad básicas."""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from flask import current_app

from app.extensions import db
from app.models import BackupRecord
from app.utils.datetime_utils import local_now


def create_sqlite_backup(user_id: int | None = None) -> BackupRecord:
    uri = current_app.config.get("SQLALCHEMY_DATABASE_URI", "")
    backup_dir = Path(current_app.config["UPLOAD_FOLDER"]).parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = local_now().strftime("%Y%m%d_%H%M%S")
    filename = f"jdm_backup_{stamp}.db"
    target = backup_dir / filename

    if uri.startswith("sqlite:///"):
        source = Path(uri.replace("sqlite:///", "", 1))
        if not source.exists():
            raise FileNotFoundError("No se encontró la base SQLite.")
        shutil.copy2(source, target)
        status = "completado"
    else:
        # En PostgreSQL se registra la intención; usar pg_dump en producción.
        target.write_text(
            f"Backup lógico solicitado {datetime.utcnow().isoformat()}Z\n"
            "Ejecute pg_dump sobre DATABASE_URL.\n",
            encoding="utf-8",
        )
        status = "manual_postgres"

    record = BackupRecord(
        filename=filename,
        file_path=str(target),
        file_size=target.stat().st_size if target.exists() else 0,
        backup_type="manual",
        status=status,
        created_by_id=user_id,
        notes="Copia generada desde el sistema",
    )
    db.session.add(record)
    db.session.commit()
    return record


def restore_sqlite_backup(backup_id: int) -> BackupRecord:
    """Restaura un respaldo SQLite. Reinicie la app inmediatamente después."""
    record = db.session.get(BackupRecord, backup_id)
    if record is None:
        raise FileNotFoundError("Respaldo no encontrado.")
    source = Path(record.file_path)
    if not source.exists():
        raise FileNotFoundError("Archivo de respaldo ausente en disco.")

    uri = current_app.config.get("SQLALCHEMY_DATABASE_URI", "")
    if not uri.startswith("sqlite:///"):
        raise RuntimeError(
            "Restauración automática solo está disponible con SQLite. "
            "En PostgreSQL use pg_restore / dump."
        )
    target = Path(uri.replace("sqlite:///", "", 1))
    safety = target.with_name(
        f"{target.stem}.pre_restore_{local_now().strftime('%Y%m%d_%H%M%S')}{target.suffix}"
    )
    # Marcar en la BD actual antes de reemplazar el archivo.
    record.status = "restaurado"
    record.notes = ((record.notes or "") + f" | Restaurado; previo en {safety.name}").strip(" |")
    db.session.commit()
    db.session.remove()

    if target.exists():
        shutil.copy2(target, safety)
    shutil.copy2(source, target)
    return record