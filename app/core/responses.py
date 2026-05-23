from typing import Any

from fastapi import HTTPException
from fastapi.responses import JSONResponse


def success_response(
    data: Any = None,
    message: str | None = None,
    status_code: int = 200,
) -> JSONResponse:
    body: dict[str, Any] = {"success": True}
    if message:
        body["message"] = message
    if data is not None:
        body["data"] = data
    return JSONResponse(status_code=status_code, content=body)


def error_response(
    message: str,
    status_code: int = 400,
    errors: dict[str, list[str]] | None = None,
    **extra: Any,
) -> JSONResponse:
    body: dict[str, Any] = {"success": False, "message": message}
    if errors:
        body["errors"] = errors
    body.update(extra)
    return JSONResponse(status_code=status_code, content=body)


def raise_api_error(
    message: str,
    status_code: int = 400,
    errors: dict[str, list[str]] | None = None,
    **extra: Any,
) -> None:
    detail: dict[str, Any] = {"success": False, "message": message}
    if errors:
        detail["errors"] = errors
    detail.update(extra)
    raise HTTPException(status_code=status_code, detail=detail)
