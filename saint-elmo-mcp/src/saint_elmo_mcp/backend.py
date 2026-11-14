"""HTTP client for the Saint Elmo backend.

Every tool goes through `BackendClient`. It forwards the agent key and turns
backend failures into `ToolError`s whose text an agent can act on. Policy
outcomes are normal 2xx responses and pass straight through (ADR 0001).
"""

from typing import Any

import httpx
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import BaseModel, ValidationError


class BackendClient:
    def __init__(
        self,
        base_url: str,
        *,
        timeout: float = 30.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._http = httpx.AsyncClient(
            base_url=base_url, timeout=timeout, transport=transport
        )

    async def aclose(self) -> None:
        await self._http.aclose()

    async def post(self, path: str, *, agent_key: str, json: Any) -> Any:
        return await self._request("POST", path, agent_key=agent_key, json=json)

    async def get(
        self, path: str, *, agent_key: str, params: dict[str, Any] | None = None
    ) -> Any:
        return await self._request("GET", path, agent_key=agent_key, params=params)

    async def _request(self, method: str, path: str, *, agent_key: str, **kwargs: Any) -> Any:
        try:
            response = await self._http.request(
                method,
                path,
                headers={"Authorization": f"Bearer {agent_key}"},
                **kwargs,
            )
        except httpx.TransportError as exc:
            raise ToolError(
                f"BACKEND_UNAVAILABLE: the Saint Elmo backend could not be reached "
                f"({type(exc).__name__}). Try again shortly."
            ) from exc

        if response.is_success:
            return response.json()

        raise _tool_error_from(response)


def request_body(**fields: Any) -> dict[str, Any]:
    """A JSON body of only the fields given: `None` means "not given", so the
    backend applies its own default instead of receiving an explicit null."""
    return {name: value for name, value in fields.items() if value is not None}


def parse_response[M: BaseModel](model: type[M], data: Any) -> M:
    """Validate a backend response against a tool's output model.

    A mismatch means the backend contract changed under us. It is reported as
    an anticipated error instead of a crash, so the agent and the logs see why.
    """
    try:
        return model.model_validate(data)
    except ValidationError as exc:
        fields = sorted({".".join(str(p) for p in e["loc"]) for e in exc.errors()})
        raise ToolError(
            f"BACKEND_CONTRACT_MISMATCH: unexpected response shape from the backend "
            f"(fields: {', '.join(fields)}). This is a Saint Elmo bug, not your request."
        ) from exc


def _tool_error_from(response: httpx.Response) -> ToolError:
    """Map the backend error envelope to agent-readable text.

    Envelope: {"error": {"code", "message", "requestId"?, "details"?: [{field, message}]}}
    """
    try:
        error = response.json()["error"]
        code, message = error["code"], error["message"]
    except (ValueError, KeyError, TypeError):
        if response.status_code >= 500:
            return ToolError(
                f"BACKEND_UNAVAILABLE: the Saint Elmo backend failed "
                f"(HTTP {response.status_code}). Try again shortly."
            )
        return ToolError(f"HTTP_ERROR: the backend answered HTTP {response.status_code}.")

    text = f"{code}: {message}"
    details = error.get("details") or []
    if details:
        text += "\n" + "\n".join(
            f"- {d.get('field', '?')}: {d.get('message', '')}" for d in details
        )
    if request_id := error.get("requestId"):
        text += f"\n(request {request_id})"
    return ToolError(text)
