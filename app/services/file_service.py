import io
import uuid
from pathlib import Path
from typing import Any

from fastapi import UploadFile
from PIL import Image

from app.config import get_settings
from app.core.constants import (
    ALLOWED_DOCUMENT_EXT,
    ALLOWED_DOCUMENT_TYPES,
    ALLOWED_IMAGE_EXT,
    ALLOWED_IMAGE_TYPES,
    UPLOAD_FOLDERS,
)
from app.core.responses import raise_api_error

settings = get_settings()


def ensure_upload_dir() -> Path:
    path = Path(settings.upload_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def public_url(relative_path: str) -> str:
    rel = relative_path.replace("\\", "/").lstrip("/")
    return f"{settings.public_base_url.rstrip('/')}/uploads/{rel}"


def relative_path_from_public_url(url: str) -> str:
    """Ambil path relatif dari URL publik atau path yang sudah relatif."""
    url = url.strip()
    if not url:
        return url
    base = f"{settings.public_base_url.rstrip('/')}/uploads/"
    if url.startswith(base):
        return url[len(base) :]
    if "/uploads/" in url:
        return url.split("/uploads/", 1)[1].lstrip("/")
    return url.lstrip("/")


def _is_image(content_type: str | None, ext: str) -> bool:
    if content_type and content_type in ALLOWED_IMAGE_TYPES:
        return True
    return ext in ALLOWED_IMAGE_EXT


def _is_document(content_type: str | None, ext: str) -> bool:
    if content_type and content_type in ALLOWED_DOCUMENT_TYPES:
        return True
    return ext in ALLOWED_DOCUMENT_EXT


def _compress_image_to_max_bytes(raw: bytes, max_bytes: int) -> bytes:
    try:
        img = Image.open(io.BytesIO(raw))
    except Exception as exc:
        raise_api_error("File gambar tidak valid atau rusak.", 400) from exc

    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    max_dim = 1920
    quality = 88
    best: bytes | None = None

    while max_dim >= 400:
        trial = img.copy()
        trial.thumbnail((max_dim, max_dim))
        buf = io.BytesIO()
        trial.save(buf, format="JPEG", quality=quality, optimize=True)
        data = buf.getvalue()
        if best is None or len(data) < len(best):
            best = data
        if len(data) <= max_bytes:
            return data
        quality -= 12
        if quality < 45:
            max_dim = int(max_dim * 0.75)
            quality = 82

    if best and len(best) <= max_bytes:
        return best

    raise_api_error(
        f"Gambar tidak dapat dikompresi hingga maksimal {settings.max_upload_mb}MB. "
        "Coba foto dengan resolusi lebih kecil.",
        400,
    )


def _save_bytes(data: bytes, subfolder: str, suffix: str) -> tuple[str, dict[str, Any]]:
    upload_root = ensure_upload_dir() / subfolder
    upload_root.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{suffix}"
    dest = upload_root / filename
    dest.write_bytes(data)
    relative = f"{subfolder}/{filename}"
    return relative, {"size_bytes": len(data), "stored_as": suffix}


async def save_upload(
    file: UploadFile,
    subfolder: str = "complaints",
) -> tuple[str, dict[str, Any]]:
    """
    Terima file utuh dari FE, simpan di server (gambar dikompresi ≤ max_upload_mb).
    Mengembalikan path relatif + metadata untuk response API.
    """
    if subfolder not in UPLOAD_FOLDERS:
        raise_api_error(f"Folder upload tidak valid: {subfolder}", 400)

    ext = Path(file.filename or "file").suffix.lower()
    content_type = (file.content_type or "").split(";")[0].strip().lower()

    raw = await file.read()
    if len(raw) > settings.max_upload_input_bytes:
        raise_api_error(
            f"Ukuran unggahan terlalu besar (maks. {settings.max_upload_input_mb}MB sebelum diproses).",
            400,
        )
    if not raw:
        raise_api_error("File kosong.", 400)

    max_out = settings.max_upload_bytes

    if _is_image(content_type, ext):
        compressed = _compress_image_to_max_bytes(raw, max_out)
        relative, meta = _save_bytes(compressed, subfolder, ".jpg")
        meta["content_type"] = "image/jpeg"
        meta["original_size_bytes"] = len(raw)
        meta["compressed"] = True
        return relative, meta

    if _is_document(content_type, ext):
        if ext not in ALLOWED_DOCUMENT_EXT:
            ext = ".pdf"
        if len(raw) > max_out:
            raise_api_error(
                f"Dokumen maksimal {settings.max_upload_mb}MB (tanpa kompresi).",
                400,
            )
        relative, meta = _save_bytes(raw, subfolder, ext)
        meta["content_type"] = content_type or "application/pdf"
        meta["original_size_bytes"] = len(raw)
        meta["compressed"] = False
        return relative, meta

    raise_api_error(
        "Format tidak didukung. Gambar: JPG, PNG, WebP. Dokumen: PDF.",
        400,
    )


async def save_complaint_image(file: UploadFile, subfolder: str = "complaints") -> str:
    relative, _ = await save_upload(file, subfolder=subfolder)
    return relative
