import logging
from typing import Literal

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core import messages

logger = logging.getLogger(__name__)

ApiErrorCode = Literal[
    "not_found",
    "validation_error",
    "unauthorized",
    "conflict",
    "upload_failed",
    "generation_failed",
    "rate_limited",
    "unknown",
]

_STATUS_BY_CODE: dict[str, int] = {
    "not_found": status.HTTP_404_NOT_FOUND,
    "validation_error": status.HTTP_422_UNPROCESSABLE_CONTENT,
    "unauthorized": status.HTTP_403_FORBIDDEN,
    "conflict": status.HTTP_409_CONFLICT,
    "upload_failed": status.HTTP_400_BAD_REQUEST,
    "generation_failed": status.HTTP_500_INTERNAL_SERVER_ERROR,
    "rate_limited": status.HTTP_429_TOO_MANY_REQUESTS,
    "unknown": status.HTTP_500_INTERNAL_SERVER_ERROR,
}


class ApiError(Exception):
    """
    Mirrors the frontend's ApiError: an English code for branching and a
    ready-to-display Persian message so no component ever translates anything.
    """

    def __init__(self, code: ApiErrorCode, message_fa: str) -> None:
        super().__init__(f"{code}: {message_fa}")
        self.code = code
        self.message_fa = message_fa

    @property
    def status_code(self) -> int:
        return _STATUS_BY_CODE.get(self.code, 500)


def not_found(message_fa: str) -> ApiError:
    return ApiError("not_found", message_fa)


def forbidden(message_fa: str) -> ApiError:
    return ApiError("unauthorized", message_fa)


def invalid(message_fa: str) -> ApiError:
    return ApiError("validation_error", message_fa)


def generation_failed(message_fa: str | None = None) -> ApiError:
    return ApiError("generation_failed", message_fa or messages.GENERATION_FAILED)


def conflict(message_fa: str) -> ApiError:
    return ApiError("conflict", message_fa)


def _payload(code: str, message_fa: str) -> dict[str, str]:
    return {"code": code, "message_fa": message_fa}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _handle_api_error(_: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_payload(exc.code, exc.message_fa),
        )

    @app.exception_handler(RequestValidationError)
    async def _handle_validation(
        _: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # Pydantic's English detail is for our logs, not the seller's screen.
        logger.info("request validation failed: %s", exc.errors())
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content=_payload("validation_error", messages.GENERIC),
        )

    @app.exception_handler(Exception)
    async def _handle_unexpected(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled error", exc_info=exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_payload("unknown", messages.GENERIC),
        )
