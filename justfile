# List available recipes
default:
    @just --list

# Install dependencies and the git pre-commit hook
setup:
    cd saint-elmo-backend && uv sync
    cd saint-elmo-mcp && uv sync
    saint-elmo-backend/.venv/bin/pre-commit install
