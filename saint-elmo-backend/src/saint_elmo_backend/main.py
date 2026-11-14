from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from saint_elmo_backend.api.error_handlers import register_error_handlers
from saint_elmo_backend.api.middleware import RequestContextMiddleware
from saint_elmo_backend.api.v1.router import router as api_v1_router
from saint_elmo_backend.api.well_known import router as well_known_router
from saint_elmo_backend.core.logger import setup_logger
from saint_elmo_backend.core.settings import get_settings
from saint_elmo_backend.db.engine import dispose_engine
from saint_elmo_backend.valio_aimo.client import create_valio_aimo_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    # One Valio Aimo client (one connection pool) for the app's lifetime; routes get it
    # through the `get_valio_aimo_client` dependency
    valio_aimo_client = create_valio_aimo_client(get_settings())
    app.state.valio_aimo_client = valio_aimo_client
    try:
        yield
    finally:
        await valio_aimo_client.aclose()
        await dispose_engine()


def create_app() -> FastAPI:
    setup_logger()

    app = FastAPI(lifespan=lifespan, title="Saint Elmo API")

    # TODO(sw): this should probably be read from env
    origins = [
        "http://localhost:5173",
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Added last so it runs outermost: request_id is bound before any other
    # middleware or handler emits a log line
    app.add_middleware(RequestContextMiddleware)

    @app.get("/", include_in_schema=False)
    def health_check():
        return {"status": "ok"}

    register_error_handlers(app)

    app.include_router(api_v1_router)
    app.include_router(well_known_router)

    return app


app = create_app()
