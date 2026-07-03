import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config.settings import get_settings
from app.schemas.errors import ErrorBody, ErrorResponse

logger = structlog.get_logger()


def _safe_message(exc: Exception) -> str:
    settings = get_settings()
    if settings.rashid_debug:
        return str(exc)
    return "Internal server error"


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
        detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        body = ErrorResponse(
            error=ErrorBody(
                code=f"http_{exc.status_code}",
                message=detail,
                message_fa=detail,
            )
        )
        return JSONResponse(status_code=exc.status_code, content=body.model_dump())

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
        body = ErrorResponse(
            error=ErrorBody(
                code="validation_error",
                message="Invalid request",
                message_fa="درخواست نامعتبر",
                details={"field_count": len(exc.errors())},
            )
        )
        return JSONResponse(status_code=422, content=body.model_dump())

    @app.exception_handler(Exception)
    async def generic_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_exception")
        body = ErrorResponse(
            error=ErrorBody(
                code="internal_error",
                message=_safe_message(exc),
                message_fa="خطای داخلی سرور",
            )
        )
        return JSONResponse(status_code=500, content=body.model_dump())
