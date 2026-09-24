"""Consistent error envelopes. Raw stack traces are never returned to clients."""
from __future__ import annotations

import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("pathfinder.errors")


class AppError(Exception):
    status_code = 400
    code = "bad_request"

    def __init__(self, message: str, *, code: str | None = None, status_code: int | None = None, details: dict | None = None):
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        if status_code:
            self.status_code = status_code
        self.details = details or {}


class NotFound(AppError):
    status_code = 404
    code = "not_found"


class Unauthorized(AppError):
    status_code = 401
    code = "unauthorized"


class Forbidden(AppError):
    status_code = 403
    code = "forbidden"


class Conflict(AppError):
    status_code = 409
    code = "conflict"


class RateLimited(AppError):
    status_code = 429
    code = "rate_limited"


class InvalidFile(AppError):
    status_code = 415
    code = "invalid_file"


class AIProviderError(AppError):
    status_code = 502
    code = "ai_provider_error"


class InvalidAIOutput(AppError):
    status_code = 502
    code = "invalid_ai_output"


def _envelope(status: int, code: str, message: str, details: dict | None = None, request_id: str | None = None):
    body = {"error": {"code": code, "message": message}}
    if details:
        body["error"]["details"] = details
    if request_id:
        body["error"]["request_id"] = request_id
    return JSONResponse(status_code=status, content=body)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError):
        return _envelope(exc.status_code, exc.code, exc.message, exc.details)

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, exc: StarletteHTTPException):
        code = {401: "unauthorized", 403: "forbidden", 404: "not_found", 405: "method_not_allowed"}.get(exc.status_code, "http_error")
        return _envelope(exc.status_code, code, str(exc.detail))

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError):
        fields = [
            {"field": ".".join(str(p) for p in err.get("loc", []) if p != "body"), "message": err.get("msg", "Invalid value")}
            for err in exc.errors()
        ]
        return _envelope(422, "validation_error", "Some fields need attention.", {"fields": fields})

    @app.exception_handler(SQLAlchemyError)
    async def _db_error(_: Request, exc: SQLAlchemyError):
        rid = uuid.uuid4().hex[:12]
        log.exception("database error [%s]", rid, exc_info=exc)
        return _envelope(503, "database_error", "We couldn't reach your data right now. Please try again shortly.", request_id=rid)

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception):
        rid = uuid.uuid4().hex[:12]
        log.exception("unhandled error [%s]", rid, exc_info=exc)
        return _envelope(500, "internal_error", "Something went wrong on our side. Please try again.", request_id=rid)
