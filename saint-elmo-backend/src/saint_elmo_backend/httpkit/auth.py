import base64

from typing import Literal


def b64_encode_credentials(
    left: str, right: str, encoding: Literal["ascii", "utf-8"] = "ascii"
) -> str:
    key_bytes = f"{left}:{right}".encode(encoding=encoding)
    base64_bytes = base64.b64encode(key_bytes)
    return base64_bytes.decode(encoding=encoding)
