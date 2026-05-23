"""
Entry production Railway — PORT dari env (Railway inject), bukan $PORT di shell.
Jalankan: python start_railway.py
"""
import os

import uvicorn

if __name__ == "__main__":
    raw_port = os.environ.get("PORT")
    if not raw_port:
        print("WARNING: env PORT kosong — pakai fallback 8080 (Railway biasanya inject PORT otomatis)")
    port = int(raw_port or "8080")
    print(f"Starting uvicorn on 0.0.0.0:{port} (PORT env={raw_port!r})")
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        log_level=os.environ.get("LOG_LEVEL", "info").lower(),
    )
