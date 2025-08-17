import logging
import os
import tomllib
from pathlib import Path

import settings
from brotli_asgi import BrotliMiddleware
from fastapi import FastAPI

from routes.auth_route import router as auth_router
from routes.public_route import router as public_router
from routes.spotify_route import router as spotify_router
from routes.friendship import router as friendship_router
from settings import PROJECT_PATH
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware

from utils import setup_logs

logger = logging.getLogger("lykd.main")
setup_logs()


def get_version() -> str:
    """Read version from pyproject.toml"""

    with open(PROJECT_PATH / "pyproject.toml", "rb") as f:
        pyproject = tomllib.load(f)
    return pyproject["project"]["version"]


def update_database():  # pragma: no cover
    """Init the DB or run the Alembic migrations"""
    import alembic.config

    if not Path("alembic.ini").is_file():
        os.chdir(settings.BACKEND_DIR)

    try:
        alembic.config.main(
            argv=[
                "--raiseerr",
                "upgrade",
                "head",
            ]
        )
    except Exception as e:
        logger.exception(f"Cannot run DB migrations: {e}")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application"""
    update_database()
    app = FastAPI(
        title="LYKD",
        description="Your likes made social",
        version=get_version(),
        middleware=[
            Middleware(BrotliMiddleware, minimum_size=1000),
            Middleware(SessionMiddleware, secret_key=settings.SESSION_SECRET_KEY),
        ],
        swagger_ui_parameters={
            "defaultModelsExpandDepth": 0,
        },  # collapse the swagger schema
    )

    # Mount routers
    app.include_router(auth_router)
    app.include_router(spotify_router)
    app.include_router(public_router)
    app.include_router(friendship_router, tags=["friendship"])

    return app
