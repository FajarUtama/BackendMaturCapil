from fastapi import APIRouter

from app.api.v1 import audit_logs, auth, categories, complaints, users

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(complaints.router)
api_router.include_router(categories.router)
api_router.include_router(users.router)
api_router.include_router(audit_logs.router)
