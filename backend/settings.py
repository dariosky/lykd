import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file in the backend folder
backend_dir = Path(__file__).parent
env_path = backend_dir / ".env"
load_dotenv(env_path)

SESSION_SECRET_KEY = os.getenv("SESSION_SECRET_KEY")
if not SESSION_SECRET_KEY:  # pragma: no cover
    raise ValueError("SESSION_SECRET_KEY must be set")
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
SELF_URL = os.getenv("SELF_URL", "http://localhost:8000")

BACKEND_DIR = Path(__file__).parent
DATABASE_PATH = BACKEND_DIR / "lykd.sqlite"
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATABASE_PATH}")

PROJECT_PATH = BACKEND_DIR.parent
