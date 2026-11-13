from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from saint_elmo_backend.core.logger import setup_logger

from saint_elmo_backend.db.engine import dispose_engine

from saint_elmo_backend.api.middleware import RequestContextMiddleware
from saint_elmo_backend.api.error_handlers import register_error_handlers
from saint_elmo_backend.api.v1.router import router as api_v1_router

@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        yield
    finally:
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

    return app


app = create_app()