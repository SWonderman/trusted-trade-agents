import re

from typing import overload
from collections.abc import Mapping, Iterable

from pydantic import BaseModel, ConfigDict

UNDERSCORE_RE = re.compile(r"(?<=[^\-_])[\-_]+[^\-_]")


def _process_keys(str_or_iter, fn):
    if isinstance(str_or_iter, list):
        return [_process_keys(k, fn) for k in str_or_iter]
    if isinstance(str_or_iter, Mapping):
        return {fn(k): _process_keys(v, fn) for k, v in str_or_iter.items()}
    return str_or_iter


def _is_none(_in):
    return "" if _in is None else re.sub(r"\s+", "", str(_in))


@overload
def camelize(str_or_iter: list) -> list: ...


@overload
def camelize(str_or_iter: dict) -> dict: ...


@overload
def camelize(str_or_iter: str) -> str: ...


def camelize[T](str_or_iter: T) -> T:
    """
    Convert a string, dict, or list of dicts to camel case.
    """
    if isinstance(str_or_iter, (list, Mapping)):
        return _process_keys(str_or_iter, camelize)

    s = _is_none(str_or_iter)
    if s.isupper() or s.isnumeric():
        return str_or_iter

    if len(s) != 0 and not s[:2].isupper():
        s = s[0].lower() + s[1:]

    # For string "hello_world", match will contain the regex capture group for "_w".
    return UNDERSCORE_RE.sub(lambda m: m.group(0)[-1].upper(), s)


def _to_camel(value: str | Iterable) -> str:
    return camelize(str_or_iter=value)


class CamelBaseModel(BaseModel):
    model_config = ConfigDict(alias_generator=_to_camel, populate_by_name=True)
