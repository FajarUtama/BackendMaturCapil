"""
Entry point untuk Railpack / platform yang menjalankan main.py di root.
Aplikasi FastAPI sebenarnya ada di app.main:app
"""
from app.main import app

__all__ = ["app"]
