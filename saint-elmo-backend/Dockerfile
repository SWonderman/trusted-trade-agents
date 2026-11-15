# Saint Elmo backend (FastAPI). Built by the root compose.yml, which also runs this image
# once as `migrate` (migrations and seed data) before serving it as `backend`.
FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:0.13.5 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_DEV=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Dependencies first, so code changes don't reinstall them
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-install-project

COPY . .
RUN uv sync --locked

EXPOSE 8000
CMD ["uvicorn", "saint_elmo_backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
