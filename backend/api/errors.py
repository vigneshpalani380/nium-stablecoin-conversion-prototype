"""Error envelope handlers. Never leak stack traces or raw DB errors."""
from __future__ import annotations

import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from backend.domain.errors import AppError, SimulatedTimeout
from backend.schemas.serializers import error_body

log = logging.getLogger("wallet")


def install(app: FastAPI) -> None:
    @app.middleware("http")
    async def add_request_id(request: Request, call_next):  # type: ignore[no-untyped-def]
        rid = request.headers.get("X-Request-ID") or f"req-{uuid.uuid4().hex[:12]}"
        request.state.request_id = rid
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        return response

    def rid(request: Request) -> str | None:
        return getattr(request.state, "request_id", None)

    @app.exception_handler(AppError)
    async def app_error(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            error_body(exc.code, exc.message, exc.retryable, rid(request), exc.details or None),
            status_code=exc.http_status,
        )

    @app.exception_handler(SimulatedTimeout)
    async def simulated_timeout(request: Request, exc: SimulatedTimeout) -> JSONResponse:
        return JSONResponse(
            error_body(
                "RESPONSE_TIMEOUT",
                "The response was lost (simulated). The conversion may have completed; "
                "check its status with your original reference. Do not resubmit.",
                True,
                rid(request),
                {"idempotency_key": exc.idempotency_key},
            ),
            status_code=504,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        fields = [".".join(str(p) for p in e.get("loc", [])) for e in exc.errors()]
        return JSONResponse(
            error_body("VALIDATION_ERROR", "The request is missing fields or has fields of the wrong type.",
                       False, rid(request), {"fields": fields}),
            status_code=422,
        )

    @app.exception_handler(Exception)
    async def unexpected(request: Request, exc: Exception) -> JSONResponse:
        log.exception("unhandled error", exc_info=exc)
        return JSONResponse(
            error_body("INTERNAL_ERROR",
                       "Something went wrong. Any partial changes were rolled back. "
                       "Check the conversion status with your original reference before retrying.",
                       True, rid(request)),
            status_code=500,
        )
