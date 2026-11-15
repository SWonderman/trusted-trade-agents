# List available recipes
default:
    @just --list

# Install dependencies and the git pre-commit hook
setup:
    cd saint-elmo-backend && uv sync
    cd saint-elmo-mcp && uv sync
    saint-elmo-backend/.venv/bin/pre-commit install

# Issue an Agent token for a seeded agent and print it once (preset: Purchasing or "Research only")
issue-agent-token agent buyer_admin_email preset="Purchasing":
    cd saint-elmo-backend && uv run python -m saint_elmo_backend.agents.command "{{agent}}" "{{buyer_admin_email}}" "{{preset}}"

# Start the MCP server on http://127.0.0.1:8001/mcp (the backend must be running)
mcp:
    cd saint-elmo-mcp && uv run saint-elmo-mcp

# Build and start the whole stack in Docker: console :3000, MCP :8001, backend :8000
up:
    docker compose up --build

# Issue an Agent token from the running Docker stack (the counterpart of issue-agent-token)
compose-token agent buyer_admin_email preset="Purchasing":
    docker compose exec backend python -m saint_elmo_backend.agents.command "{{agent}}" "{{buyer_admin_email}}" "{{preset}}"
