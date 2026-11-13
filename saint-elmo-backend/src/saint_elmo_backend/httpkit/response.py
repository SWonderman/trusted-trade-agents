from abc import ABC, abstractmethod
from collections.abc import Mapping

from pydantic import JsonValue


class ResponseWrapper(ABC):
    @abstractmethod
    def ok(self) -> bool:
        pass

    # NOTE(sw): to make sure that all status codes are supported, this function will return an int instead of an enum
    @abstractmethod
    def status_code(self) -> int:
        pass

    @abstractmethod
    def text(self) -> str:
        pass

    @abstractmethod
    def json(self) -> JsonValue:
        pass

    @abstractmethod
    def headers(self) -> Mapping[str, str]:
        pass
