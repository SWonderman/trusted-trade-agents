from typing import override

from pydantic import JsonValue

import httpx

from saint_elmo_backend.httpkit.response import ResponseWrapper


class HttpxResponse(ResponseWrapper):
    def __init__(self, response: httpx.Response):
        self._response: httpx.Response = response

    @override
    def ok(self) -> bool:
        return 200 <= self._response.status_code < 300

    @override
    def status_code(self) -> int:
        return self._response.status_code

    @override
    def text(self) -> str:
        return self._response.text

    @override
    def json(self) -> JsonValue:
        return self._response.json()

    @override
    def headers(self) -> dict[str, str]:
        return dict(self._response.headers)
