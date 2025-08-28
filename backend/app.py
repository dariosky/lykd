import logging
import os
import tomllib
from contextlib import asynccontextmanager
from pathlib import Path

import setproctitle

import settings
from brotli_asgi import BrotliMiddleware
from fastapi import FastAPI, APIRouter

from routes.auth_route import router as auth_router
from routes.public_route import router as public_router
from routes.spotify_route import router as spotify_router
from routes.friendship import router as friendship_router
from routes.recent_route import router as recent_router
from routes.ignore_route import router as ignore_router
from routes.spotify_streaming import router as streaming_router
from services import Spotify
from settings import PROJECT_PATH
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware

from utils import setup_logs

logger = logging.getLogger("lykd.main")
setup_logs()
setproctitle.setproctitle("Lykd API")


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


@asynccontextmanager
async def app_lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI app"""
    logger.debug("Starting...")
    update_database()
    spotify = Spotify()
    app.state.spotify = spotify
    yield
    await spotify.close()
    logger.debug("Closing app")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application"""

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
        lifespan=app_lifespan,
    )

    # Mount routers
    api_router = APIRouter()
    api_router.include_router(auth_router)
    api_router.include_router(spotify_router)
    api_router.include_router(public_router)
    api_router.include_router(friendship_router, tags=["friendship"])
    api_router.include_router(recent_router)
    api_router.include_router(ignore_router)
    api_router.include_router(streaming_router)
    app.include_router(api_router, prefix=settings.API_PREFIX)
    return app
