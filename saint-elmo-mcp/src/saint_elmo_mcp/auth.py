"""Reading the agent key from the incoming MCP request.

The MCP server never checks the key: it only requires that one is present and
passes it on to the backend, which owns authentication (ADR 0001).
"""

from collections.abc import Mapping

from mcp.server.mcpserver import Context
from mcp.server.mcpserver.exceptions import ToolError

AGENT_KEY_HEADER = "x-agent-key"


def agent_key_from_headers(headers: Mapping[str, str] | None) -> str:
    headers = headers or {}

    key = headers.get(AGENT_KEY_HEADER, "").strip()
    if key:
        return key

    scheme, _, token = headers.get("authorization", "").partition(" ")
    if scheme.lower() == "bearer" and token.strip():
        return token.strip()

    raise ToolError(
        "MISSING_AGENT_KEY: no agent key on this request. Configure your MCP client "
        "to send your agent key as the 'X-Agent-Key' header "
        "(or as 'Authorization: Bearer <key>')."
    )


def agent_key(ctx: Context) -> str:
    return agent_key_from_headers(ctx.headers)
