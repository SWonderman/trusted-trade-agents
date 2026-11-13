from types import TracebackType
from typing import Self

import httpx

from saint_elmo_backend.httpkit.dataclasses import Request
from saint_elmo_backend.httpkit.response import ResponseWrapper
from saint_elmo_backend.httpkit.exceptions import (
    HttpkitTransportError,
    HttpkitTimeoutError,
    HttpkitConnectionError,
)

from saint_elmo_backend.httpkit.transport.httpx.response import HttpxResponse
from saint_elmo_backend.httpkit.transport.httpx.config import HttpxClientConfig


class HttpxSyncTransport:
    def __init__(self, config: HttpxClientConfig | None = None) -> None:
        self._client: httpx.Client = httpx.Client(
            base_url=config.base_url if config else ""
        )

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.shutdown()

    def call(self, request: Request) -> ResponseWrapper:
        try:
            return HttpxResponse(
                self._client.request(
                    method=request.method,
                    url=request.url,
                    headers=request.headers,
                    params=request.params,
                    json=request.json,
                    content=request.content,
                    timeout=httpx.USE_CLIENT_DEFAULT
                    if request.timeout is None
                    else request.timeout,
                )
            )
        except httpx.TimeoutException as e:
            raise HttpkitTimeoutError(
                message=str(e), method=request.method, url=request.url
            ) from e
        except httpx.NetworkError as e:
            raise HttpkitConnectionError(
                message=str(e), method=request.method, url=request.url
            ) from e
        except httpx.RequestError as e:
            raise HttpkitTransportError(
                message=str(e), method=request.method, url=request.url
            ) from e

    def shutdown(self) -> None:
        self._client.close()
