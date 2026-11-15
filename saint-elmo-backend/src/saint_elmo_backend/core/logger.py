import logging
import sys
from typing import override

from loguru import logger

from saint_elmo_backend.core.settings import get_settings


class InterceptHandler(logging.Handler):
    @override
    def emit(self, record: logging.LogRecord) -> None:
        try:
            level: str | int = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


_INTERCEPTED_LOGGERS = (
    "uvicorn",
    "uvicorn.error",
    "uvicorn.access",
    "fastapi",
    "sqlalchemy",
    "sqlalchemy.engine",
    "asyncpg",
    "alembic",
    "saint_elmo_backend",
)

_DEV_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<magenta>{extra}</magenta> | "
    "{message}"
)


def setup_logger() -> None:
    cfg = get_settings()

    # Redirect stdlib logging into loguru
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    for name in _INTERCEPTED_LOGGERS:
        std_logger = logging.getLogger(name)
        std_logger.handlers = []
        std_logger.propagate = True

    logger.remove()

    if cfg.debug:
        # Dev-oriented
        _ = logger.add(
            sys.stdout,
            level=cfg.log_level,
            format=_DEV_FORMAT,
            colorize=True,
            backtrace=True,
            diagnose=True,
            enqueue=True,
        )
    else:
        # As JSON
        _ = logger.add(
            sys.stdout,
            level=cfg.log_level,
            serialize=True,
            backtrace=True,
            diagnose=False,  # do not serialize local variables into logs
            enqueue=True,
        )
