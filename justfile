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
