from fastapi import APIRouter, Depends, File, UploadFile

from app.config import get_settings
from app.core.deps import get_current_user
from app.core.responses import raise_api_error, success_response
from app.models.user import User
from app.services.file_service import public_url, save_upload

router = APIRouter(prefix="/uploads", tags=["Upload"])
settings = get_settings()


def _serialize_upload(relative: str, meta: dict) -> dict:
    return {
        "url": public_url(relative),
        "path": relative,
        "filename": relative.split("/")[-1],
        "size_bytes": meta.get("size_bytes"),
        "content_type": meta.get("content_type"),
        "original_size_bytes": meta.get("original_size_bytes"),
        "compressed": meta.get("compressed", False),
    }


@router.post("")
async def upload_file(
    file: UploadFile = File(..., description="Foto/dokumen bukti (BE kompresi gambar max 2MB)"),
    folder: str = "complaints",
    user: User = Depends(get_current_user),
):
    """
    Unggah satu file. FE kirim file utuh; BE kompresi gambar dan simpan.
    Gunakan `url` dari response di field `photos` / `evidence_after_photos` saat buat/tutup laporan.
    """
    relative, meta = await save_upload(file, subfolder=folder)
    return success_response(
        data=_serialize_upload(relative, meta),
        message="File berhasil diunggah.",
        status_code=201,
    )


@router.post("/batch")
async def upload_files(
    files: list[UploadFile] = File(..., description="Beberapa file sekaligus"),
    folder: str = "complaints",
    user: User = Depends(get_current_user),
):
    if not files:
        raise_api_error("Tidak ada file.", 400)
    if len(files) > settings.max_complaint_photos:
        raise_api_error(f"Maksimal {settings.max_complaint_photos} file per unggahan.", 400)

    items = []
    for f in files:
        relative, meta = await save_upload(f, subfolder=folder)
        items.append(_serialize_upload(relative, meta))

    return success_response(
        data={"items": items, "count": len(items)},
        message="File berhasil diunggah.",
        status_code=201,
    )
