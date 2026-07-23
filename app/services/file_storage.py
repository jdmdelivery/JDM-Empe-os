"""Almacenamiento seguro de archivos (nunca base64 en BD)."""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from pathlib import Path

from flask import current_app
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

ALLOWED_MIME = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}

MAX_IMAGE_EDGE = 1600
JPEG_QUALITY = 85


def _optimize_image_bytes(data: bytes, *, ext: str) -> tuple[bytes, str, str | None]:
    """Reduce peso de fotos (redimensiona y re-codifica) sin tocar firmas pequeñas."""
    try:
        from io import BytesIO

        from PIL import Image

        img = Image.open(BytesIO(data))
        img = img.convert("RGB") if img.mode not in {"RGB", "L"} else img
        w, h = img.size
        if max(w, h) > MAX_IMAGE_EDGE:
            img.thumbnail((MAX_IMAGE_EDGE, MAX_IMAGE_EDGE))
        out = BytesIO()
        if ext in {"jpg", "jpeg", "webp"} or w * h > 400_000:
            img.save(out, format="JPEG", quality=JPEG_QUALITY, optimize=True)
            return out.getvalue(), "jpg", "image/jpeg"
        img.save(out, format="PNG", optimize=True)
        return out.getvalue(), "png", "image/png"
    except Exception:  # noqa: BLE001
        return data, ext, ALLOWED_MIME.get(f"image/{ext}")


@dataclass
class StoredFile:
    uuid: str
    relative_path: str
    absolute_path: str
    safe_name: str
    mime_type: str | None
    file_size: int
    sha256_hash: str
    url_path: str


def _uploads_root() -> Path:
    root = Path(current_app.config["UPLOAD_FOLDER"])
    root.mkdir(parents=True, exist_ok=True)
    return root


def compute_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def save_upload(
    file_storage: FileStorage,
    *,
    folder: str,
    allowed_extensions: set[str] | None = None,
) -> StoredFile:
    if file_storage is None or not file_storage.filename:
        raise ValueError("No se recibió ningún archivo.")

    original = secure_filename(file_storage.filename)
    ext = Path(original).suffix.lower().lstrip(".")
    allowed = allowed_extensions or current_app.config.get(
        "ALLOWED_IMAGE_EXTENSIONS", {"jpg", "jpeg", "png", "webp"}
    )
    if ext not in allowed:
        raise ValueError(f"Tipo de archivo no permitido: .{ext}")

    data = file_storage.read()
    if not data:
        raise ValueError("El archivo está vacío.")

    max_size = current_app.config.get("MAX_CONTENT_LENGTH", 16 * 1024 * 1024)
    if len(data) > max_size:
        raise ValueError("El archivo excede el tamaño máximo permitido.")

    mime = file_storage.mimetype
    if mime and mime not in ALLOWED_MIME and ext in {"jpg", "jpeg", "png", "webp"}:
        # Algunos navegadores envían mime vacío o genérico
        mime = {
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
            "webp": "image/webp",
        }.get(ext)

    file_uuid = str(uuid.uuid4())
    # Prefer JPEG optimizado para fotos grandes; firmas PNG se mantienen.
    if ext in {"jpg", "jpeg", "png", "webp"} and folder != "signatures":
        data, ext, mime = _optimize_image_bytes(data, ext=ext)
    safe_name = f"{file_uuid}.{ext}"
    target_dir = _uploads_root() / folder
    target_dir.mkdir(parents=True, exist_ok=True)
    absolute = target_dir / safe_name
    absolute.write_bytes(data)

    relative = f"{folder}/{safe_name}".replace("\\", "/")
    return StoredFile(
        uuid=file_uuid,
        relative_path=relative,
        absolute_path=str(absolute),
        safe_name=safe_name,
        mime_type=mime,
        file_size=len(data),
        sha256_hash=compute_sha256(data),
        url_path=f"/uploads/{relative}",
    )


def save_base64_image(
    data_url: str,
    *,
    folder: str,
    default_ext: str = "png",
) -> StoredFile:
    """Guarda firma/captura enviada como data URL; el archivo queda en disco, no en BD."""
    import base64

    if not data_url or "," not in data_url:
        raise ValueError("Imagen en formato no válido.")

    header, encoded = data_url.split(",", 1)
    ext = default_ext
    mime = None
    if "image/png" in header:
        ext, mime = "png", "image/png"
    elif "image/jpeg" in header or "image/jpg" in header:
        ext, mime = "jpg", "image/jpeg"
    elif "image/webp" in header:
        ext, mime = "webp", "image/webp"

    raw = base64.b64decode(encoded)
    if not raw:
        raise ValueError("Imagen vacía.")

    file_uuid = str(uuid.uuid4())
    safe_name = f"{file_uuid}.{ext}"
    target_dir = _uploads_root() / folder
    target_dir.mkdir(parents=True, exist_ok=True)
    absolute = target_dir / safe_name
    absolute.write_bytes(raw)

    relative = f"{folder}/{safe_name}".replace("\\", "/")
    return StoredFile(
        uuid=file_uuid,
        relative_path=relative,
        absolute_path=str(absolute),
        safe_name=safe_name,
        mime_type=mime,
        file_size=len(raw),
        sha256_hash=compute_sha256(raw),
        url_path=f"/uploads/{relative}",
    )