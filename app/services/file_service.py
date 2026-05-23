import io
import uuid
from pathlib import Path

from fastapi import UploadFile
from PIL import Image

from app.config import get_settings
from app.core.constants import ALLOWED_IMAGE_EXT, ALLOWED_IMAGE_TYPES
from app.core.responses import raise_api_error

settings = get_settings()


def ensure_upload_dir() -> Path:
    path = Path(settings.upload_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def public_url(relative_path: str) -> str:
    rel = relative_path.replace("\\", "/").lstrip("/")
    return f"{settings.public_base_url.rstrip('/')}/uploads/{rel}"


async def save_complaint_image(file: UploadFile, subfolder: str = "complaints") -> str:
    if file.content_type and file.content_type not in ALLOWED_IMAGE_TYPES:
        raise_api_error("Format file tidak didukung. Gunakan JPG atau PNG.", 400)

    ext = Path(file.filename or "photo.jpg").suffix.lower()
    if ext not in ALLOWED_IMAGE_EXT:
        ext = ".jpg"

    raw = await file.read()
    if len(raw) > settings.max_upload_bytes:
        raise_api_error(f"Ukuran file maksimal {settings.max_upload_mb}MB.", 400)

    upload_root = ensure_upload_dir() / subfolder
    upload_root.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{ext}"
    dest = upload_root / filename

    # Kompresi otomatis
    try:
        img = Image.open(io.BytesIO(raw))
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
            dest = dest.with_suffix(".jpg")
        img.thumbnail((1920, 1920))
        img.save(dest, format="JPEG", quality=85, optimize=True)
        relative = f"{subfolder}/{dest.name}"
    except Exception:
        dest.write_bytes(raw)
        relative = f"{subfolder}/{filename}"

    return relative
