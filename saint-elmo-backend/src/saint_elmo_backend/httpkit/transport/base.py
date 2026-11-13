from types import TracebackType
from typing import Protocol, Self

from saint_elmo_backend.httpkit.dataclasses import Request
from saint_elmo_backend.httpkit.response import ResponseWrapper


class SyncTransport(Protocol):
    def __enter__(self) -> Self: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...

    def call(self, request: Request) -> ResponseWrapper: ...

    def shutdown(self) -> None: ...


class AsyncTransport(Protocol):
    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...

    async def acall(self, request: Request) -> ResponseWrapper: ...

    async def ashutdown(self) -> None: ...
