from dataclasses import replace
from http import HTTPMethod
from json import JSONDecodeError

from typing import overload, Any
from collections.abc import Mapping
from abc import ABC, abstractmethod

from pydantic import BaseModel, JsonValue, ValidationError

from saint_elmo_backend.httpkit.dataclasses import Request, Response
from saint_elmo_backend.httpkit.exceptions import (
    HttpkitStatusError,
    HttpkitValidationError,
)
from saint_elmo_backend.httpkit.response import ResponseWrapper
from saint_elmo_backend.httpkit.transport.base import AsyncTransport, SyncTransport


class _HttpkitBaseClient(ABC):
    def __init__(self, api_url: str, api_key: str) -> None:
        self._api_url: str = api_url
        self._api_key: str = api_key

    @abstractmethod
    def _get_headers(self, request: Request) -> Mapping[str, str]:
        pass

    def _build_request(
        self,
        url: str,
        method: HTTPMethod = HTTPMethod.GET,
        headers: Mapping[str, str] | None = None,
        params: Mapping[str, str] | None = None,
        json: JsonValue | None = None,
        content: bytes | None = None,
        timeout: float | None = None,
    ) -> Request:
        request = Request(
            method=method,
            url=url,
            headers={},
            params=params,
            json=json,
            content=content,
            timeout=timeout,
        )
        client_headers = self._get_headers(request=request)

        return replace(request, headers={**client_headers, **(headers or {})})


class HttpkitBaseSyncClient(_HttpkitBaseClient, ABC):
    def __init__(self, api_url: str, api_key: str, transport: SyncTransport) -> None:
        super().__init__(api_url=api_url, api_key=api_key)

        self._transport: SyncTransport = transport

    @overload
    def request[T: BaseModel](
        self,
        url: str,
        *,
        method: HTTPMethod = HTTPMethod.GET,
        headers: Mapping[str, str] | None = None,
        params: Mapping[str, str] | None = None,
        json: JsonValue | None = None,
        content: bytes | None = None,
        timeout: float | None = None,
        response_model: type[T],
    ) -> Response[T]: ...
    @overload
    def request(
        self,
        url: str,
        *,
        method: HTTPMethod = HTTPMethod.GET,
        headers: Mapping[str, str] | None = None,
        params: Mapping[str, str] | None = None,
        json: JsonValue | None = None,
        content: bytes | None = None,
        timeout: float | None = None,
        response_model: None = None,
    ) -> Response[JsonValue | None]: ...

    def request[T: BaseModel](
        self,
        url: str,
        method: HTTPMethod = HTTPMethod.GET,
        headers: Mapping[str, str] | None = None,
        params: Mapping[str, str] | None = None,
        json: JsonValue | None = None,
        content: bytes | None = None,
        timeout: float | None = None,
        response_model: type[T] | None = None,
    ) -> Response[Any]:
        final_request = self._build_request(
            method=method,
            url=url,
            headers=headers,
            params=params,
            json=json,
            content=content,
            timeout=timeout,
        )

        raw_response = self._transport.call(request=final_request)

        return _build_response(
            raw_response=raw_response,
            method=method,
            url=url,
            response_model=response_model,
        )


class HttpkitBaseAsyncClient(_HttpkitBaseClient, ABC):
    def __init__(self, api_url: str, api_key: str, transport: AsyncTransport) -> None:
        super().__init__(api_url=api_url, api_key=api_key)

        self._transport: AsyncTransport = transport

    @overload
    async def arequest[T: BaseModel](
        self,
        url: str,
        *,
        method: HTTPMethod = HTTPMethod.GET,
        headers: Mapping[str, str] | None = None,
        params: Mapping[str, str] | None = None,
        json: JsonValue | None = None,
        content: bytes | None = None,
        timeout: float | None = None,
        response_model: type[T],
    ) -> Response[T]: ...
    @overload
    async def arequest(
        self,
        url: str,
        *,
        method: HTTPMethod = HTTPMethod.GET,
        headers: Mapping[str, str] | None = None,
        params: Mapping[str, str] | None = None,
        json: JsonValue | None = None,
        content: bytes | None = None,
        timeout: float | None = None,
        response_model: None = None,
    ) -> Response[JsonValue | None]: ...

    async def arequest[T: BaseModel](
        self,
        url: str,
        method: HTTPMethod = HTTPMethod.GET,
        headers: Mapping[str, str] | None = None,
        params: Mapping[str, str] | None = None,
        json: JsonValue | None = None,
        content: bytes | None = None,
        timeout: float | None = None,
        response_model: type[T] | None = None,
    ) -> Response[Any]:
        request = self._build_request(
            method=method,
            url=url,
            headers=headers,
            params=params,
            json=json,
            content=content,
            timeout=timeout,
        )

        raw_response = await self._transport.acall(request=request)

        return _build_response(
            raw_response=raw_response,
            method=method,
            url=url,
            response_model=response_model,
        )


@overload
def _build_response[T: BaseModel](
    raw_response: ResponseWrapper,
    method: HTTPMethod,
    url: str,
    response_model: type[T],
) -> Response[T]: ...
@overload
def _build_response(
    raw_response: ResponseWrapper,
    method: HTTPMethod,
    url: str,
    response_model: None,
) -> Response[JsonValue | None]: ...


def _build_response[T: BaseModel](
    raw_response: ResponseWrapper,
    method: HTTPMethod,
    url: str,
    response_model: type[T] | None,
) -> Response[Any]:
    if not raw_response.ok():
        raise HttpkitStatusError(
            message="Received non-ok status code",
            method=method,
            url=url,
            status_code=raw_response.status_code(),
            error_body=raw_response.text(),
        )

    payload: T | JsonValue | None
    if response_model:
        try:
            payload = response_model.model_validate(raw_response.json())
        except (JSONDecodeError, ValidationError) as e:
            raise HttpkitValidationError(
                message="Could not validate received response body",
                method=method,
                url=url,
                status_code=raw_response.status_code(),
            ) from e
    elif not raw_response.text():
        payload = None
    else:
        try:
            payload = raw_response.json()
        except JSONDecodeError as e:
            raise HttpkitValidationError(
                message="Could not JSON decode received response body",
                method=method,
                url=url,
                status_code=raw_response.status_code(),
            ) from e

    return Response(
        payload=payload,
        status_code=raw_response.status_code(),
        headers=raw_response.headers(),
    )
