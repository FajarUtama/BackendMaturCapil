import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.router import api_router
from app.config import get_masked_database_url, get_settings
from app.database import Base, check_database_connection, engine, verify_database_connection
from app.services.file_service import ensure_upload_dir
from app.services.permissions import ensure_permissions_exist

settings = get_settings()
logging.basicConfig(level=logging.DEBUG if settings.debug else logging.INFO)
logger = logging.getLogger(__name__)
logger.info("Database target: %s", get_masked_database_url())


@asynccontextmanager
async def lifespan(app: FastAPI):
    verify_database_connection()
    try:
        Base.metadata.create_all(bind=engine)
        print("DATABASE CONNECTED")
    except Exception as e:
        import traceback

        print("REAL DATABASE ERROR:")
        print(repr(e))
        traceback.print_exc()
        raise

    ensure_upload_dir()
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        ensure_permissions_exist(db)
    finally:
        db.close()
    logger.info("Database tables ready")
    yield


app = FastAPI(
    title=settings.app_name,
    description="API Backend MaturCapil Semarang — Sistem Pengaduan Masyarakat",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

upload_path = Path(settings.upload_dir)
upload_path.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(upload_path)), name="uploads")

app.include_router(api_router, prefix="/api/v1")


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if isinstance(exc.detail, dict) and "success" in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "message": str(exc.detail)},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors: dict[str, list[str]] = {}
    for err in exc.errors():
        loc = err.get("loc", [])
        field = str(loc[-1]) if loc else "body"
        errors.setdefault(field, []).append(err.get("msg", "Invalid"))
    return JSONResponse(
        status_code=422,
        content={"success": False, "message": "Validasi gagal.", "errors": errors},
    )


@app.get("/health", tags=["Health"])
def health():
    db_ok = check_database_connection()
    return {
        "status": "ok" if db_ok else "degraded",
        "app": settings.app_name,
        "database": "connected" if db_ok else "disconnected",
    }
