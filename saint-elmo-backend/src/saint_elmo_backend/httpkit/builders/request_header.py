from typing import Self


class RequestHeaderBuilder:
    def __init__(self) -> None:
        self._request_header: dict[str, str] = dict()

    def add_content_type(self, content_type: str = "application/json") -> Self:
        self._request_header["Content-Type"] = content_type
        return self

    def add_accept(self, accept: str = "application/json") -> Self:
        self._request_header["Accept"] = accept
        return self

    def add_authorization(self, authorization: str) -> Self:
        self._request_header["Authorization"] = authorization
        return self

    def add_custom_field(self, key: str, value: str) -> Self:
        self._request_header[key] = value
        return self

    def add_user_agent(self, user_agent: str) -> Self:
        self._request_header["User-Agent"] = user_agent
        return self

    def build(self) -> dict[str, str]:
        return self._request_header
