from typing import Self
from types import TracebackType

import httpx

from saint_elmo_backend.httpkit.dataclasses import Request
from saint_elmo_backend.httpkit.exceptions import (
    HttpkitConnectionError,
    HttpkitTimeoutError,
    HttpkitTransportError,
)
from saint_elmo_backend.httpkit.response import ResponseWrapper

from saint_elmo_backend.httpkit.transport.httpx.config import HttpxClientConfig
from saint_elmo_backend.httpkit.transport.httpx.response import HttpxResponse


class HttpxAsyncTransport:
    def __init__(self, config: HttpxClientConfig | None = None) -> None:
        self._client: httpx.AsyncClient = httpx.AsyncClient(
            base_url=config.base_url if config else ""
        )

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.ashutdown()

    async def acall(self, request: Request) -> ResponseWrapper:
        try:
            return HttpxResponse(
                await self._client.request(
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

    async def ashutdown(self) -> None:
        await self._client.aclose()
