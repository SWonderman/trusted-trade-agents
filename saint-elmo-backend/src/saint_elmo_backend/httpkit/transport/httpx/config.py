from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class HttpxClientConfig:
    # NOTE: base_url defaults to an empty string so that clients can build an absolute URLs (needed for request signing).
    base_url: str = field(default="")
