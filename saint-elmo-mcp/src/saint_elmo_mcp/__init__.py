from saint_elmo_mcp.backend import BackendClient
from saint_elmo_mcp.server import build_server
from saint_elmo_mcp.settings import get_settings


def main() -> None:
    settings = get_settings()
    backend = BackendClient(
        settings.backend_base_url, timeout=settings.backend_timeout_seconds
    )
    build_server(backend).run(
        "streamable-http",
        host=settings.mcp_host,
        port=settings.mcp_port,
        stateless_http=True,
        json_response=True,
    )
