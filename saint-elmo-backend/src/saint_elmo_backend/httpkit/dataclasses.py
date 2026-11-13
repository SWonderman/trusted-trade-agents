from collections.abc import Mapping
from dataclasses import dataclass
from http import HTTPMethod

from pydantic import JsonValue


@dataclass(frozen=True, slots=True)
class Request:
    method: HTTPMethod
    url: str
    headers: Mapping[str, str]
    params: Mapping[str, str] | None = None
    json: JsonValue | None = None
    content: bytes | None = None
    timeout: float | None = None

    def __post_init__(self):
        if self.json and self.content:
            raise ValueError(
                "JSON and content are mutually exclusive and cannot be both defined at the same time, choose either one."
            )


@dataclass(frozen=True, slots=True)
class Response[T]:
    payload: T | None
    status_code: int
    headers: Mapping[str, str]

    def require_payload(self) -> T:
        """
        In some cases, the payload has to be there. If that assumption is violated and the state of the world
        does not match the 'expectations', there is a clear mismatch between reality and the application logic.

        Raises:
            ValueError: when payload is `None`
        """
        if self.payload is None:
            raise ValueError("Expected payload but got none")

        return self.payload
