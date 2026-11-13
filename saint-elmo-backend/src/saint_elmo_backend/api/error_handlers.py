from typing import Any

from loguru import logger

from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse

from saint_elmo_backend.core.schema import CamelBaseModel

from saint_elmo_backend.api.exceptions import ErrorCode, SomethingWentWrong, SaintElmoHTTPException


class ErrorFieldDetail(CamelBaseModel):
    field: str
    message: str


class ErrorBody(CamelBaseModel):
    code: ErrorCode
    message: str
    request_id: str | None = None
    details: list[ErrorFieldDetail] | None = None


class ErrorEnvelope(CamelBaseModel):
    error: ErrorBody


def _prepare_envelope(
    error_code: ErrorCode,
    message: str,
    request: Request,
    details: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    envelope = ErrorEnvelope(
        error=ErrorBody(
            code=error_code,
            message=message,
            request_id=getattr(request.state, "request_id", None),
            details=details,
        )
    )
    return envelope.model_dump(mode="json", by_alias=True, exclude_none=True)


async def _handle_saint_elmo_error(
    request: Request, exc: SaintElmoHTTPException
) -> Response:
    return JSONResponse(
        status_code=exc.status_code,
        content=_prepare_envelope(
            error_code=exc.error_code,
            message=exc.detail,
            request=request,
        ),
        headers=exc.headers,
    )


async def _handle_unexpected_error(request: Request, exc: Exception) -> Response:
    logger.exception(
        "Unhandled error on %s %s", request.method, request.url.path, exc_info=exc
    )
    return await _handle_saint_elmo_error(request, SomethingWentWrong())


async def _handle_starlette_error(
    request: Request, exc: StarletteHTTPException
) -> Response:
    return JSONResponse(
        status_code=exc.status_code,
        content=_prepare_envelope(
            error_code=ErrorCode.HTTP_ERROR,
            message=exc.detail,
            request=request,
        ),
        headers=exc.headers,
    )


async def _handle_validation_error(
    request: Request, exc: RequestValidationError
) -> Response:
    details = [
        {"field": ".".join(str(p) for p in e["loc"][1:]), "message": e["msg"]}
        for e in exc.errors()
    ]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=_prepare_envelope(
            error_code=ErrorCode.VALIDATION_ERROR,
            message="Request validation failed",
            request=request,
            details=details,
        ),
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(SaintElmoHTTPException, _handle_saint_elmo_error)
    app.add_exception_handler(StarletteHTTPException, _handle_starlette_error)
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
    app.add_exception_handler(Exception, _handle_unexpected_error)
