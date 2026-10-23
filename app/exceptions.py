from typing import Any, Optional
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from app.schemas import ErrorResponse


class DataExtractionException(Exception):
    """Base exception for extraction service."""
    def __init__(self, message: str, error_code: str = "EXTRACTION_ERROR", details: Optional[Any] = None, status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details
        self.status_code = status_code


class EmptyInputException(DataExtractionException):
    """Raised when the input text is blank, whitespace-only, or too short."""
    def __init__(self, message: str = "Input text payload is empty or too short for extraction.", details: Optional[Any] = None):
        super().__init__(
            message=message,
            error_code="EMPTY_INPUT_PAYLOAD",
            details=details,
            status_code=status.HTTP_400_BAD_REQUEST
        )


class PayloadTooLargeException(DataExtractionException):
    """Raised when input text exceeds maximum allowed character or token limit."""
    def __init__(self, current_length: int, max_length: int):
        super().__init__(
            message=f"Input payload too large ({current_length} characters). Maximum allowed is {max_length} characters.",
            error_code="PAYLOAD_TOO_LARGE",
            details={"current_length": current_length, "max_length": max_length},
            status_code=413
        )


class SchemaValidationException(DataExtractionException):
    """Raised when extracted data cannot conform to the target schema after retries."""
    def __init__(self, message: str, validation_errors: Any, raw_response: Optional[str] = None):
        super().__init__(
            message=message,
            error_code="SCHEMA_VALIDATION_FAILURE",
            details={"validation_errors": validation_errors, "raw_response": raw_response},
            status_code=422
        )


class LLMTimeoutException(DataExtractionException):
    """Raised when LLM service times out."""
    def __init__(self, message: str = "Upstream LLM API request timed out. Please try again."):
        super().__init__(
            message=message,
            error_code="GATEWAY_TIMEOUT",
            status_code=status.HTTP_504_GATEWAY_TIMEOUT
        )


class LLMServiceException(DataExtractionException):
    """Raised when LLM API returns unexpected bad gateway or authentication errors."""
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(
            message=message,
            error_code="UPSTREAM_LLM_ERROR",
            details=details,
            status_code=status.HTTP_502_BAD_GATEWAY
        )


def register_exception_handlers(app: FastAPI) -> None:
    """Registers unified error handling across FastAPI application."""

    @app.exception_handler(DataExtractionException)
    async def extraction_exception_handler(request: Request, exc: DataExtractionException):
        response_model = ErrorResponse(
            success=False,
            error_code=exc.error_code,
            message=exc.message,
            details=exc.details
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=response_model.model_dump()
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        response_model = ErrorResponse(
            success=False,
            error_code="REQUEST_VALIDATION_ERROR",
            message="Incoming HTTP request body failed parameter validation.",
            details=exc.errors()
        )
        return JSONResponse(
            status_code=422,
            content=response_model.model_dump()
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        response_model = ErrorResponse(
            success=False,
            error_code="INTERNAL_SERVER_ERROR",
            message=f"An unexpected internal error occurred: {str(exc)}",
            details=None
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=response_model.model_dump()
        )
