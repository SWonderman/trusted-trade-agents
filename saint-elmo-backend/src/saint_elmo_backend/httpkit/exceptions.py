from collections.abc import Mapping
from http import HTTPMethod
from typing import override

# Constants

_RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})


# Core


class HttpkitError(Exception):
    """
    Core exception for the Httpkit module
    """

    _default_retryable: bool = False

    def __init__(self, message: str):
        super().__init__(message)

    def is_retryable(self) -> bool:
        return self._default_retryable


# Transport


class HttpkitTransportError(HttpkitError):
    def __init__(self, message: str, method: HTTPMethod, url: str) -> None:
        super().__init__(message)

        self.method: HTTPMethod = method
        self.url: str = url


class HttpkitTimeoutError(HttpkitTransportError):
    _default_retryable: bool = True


class HttpkitConnectionError(HttpkitTransportError):
    _default_retryable: bool = True


# Status


class HttpkitStatusError(HttpkitError):
    def __init__(
        self,
        message: str,
        method: HTTPMethod,
        url: str,
        status_code: int,
        error_body: str,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        super().__init__(message)

        self.method: HTTPMethod = method
        self.url: str = url
        self.status_code: int = status_code
        self.error_body: str = error_body
        self.headers: Mapping[str, str] = headers or {}

    @override
    def is_retryable(self) -> bool:
        return self.status_code in _RETRYABLE_STATUS_CODES


# Validation


class HttpkitValidationError(HttpkitError):
    def __init__(
        self,
        message: str,
        method: HTTPMethod,
        url: str,
        status_code: int,
    ) -> None:
        super().__init__(message)

        self.method: HTTPMethod = method
        self.url: str = url
        self.status_code: int = status_code
