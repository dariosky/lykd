import os
from pathlib import Path

from dotenv import load_dotenv

from models.common import parse_bool

# Load environment variables from .env file in the backend folder
backend_dir = Path(__file__).parent
env_path = backend_dir / ".env"
load_dotenv(env_path)

SESSION_SECRET_KEY = os.getenv("SESSION_SECRET_KEY")
if not SESSION_SECRET_KEY:  # pragma: no cover
    raise ValueError("SESSION_SECRET_KEY must be set")
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")


BACKEND_DIR = Path(__file__).parent
DATABASE_PATH = BACKEND_DIR / "lykd.sqlite"
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATABASE_PATH}")

PROJECT_PATH = BACKEND_DIR.parent
DEBUG_MODE = parse_bool(os.getenv("DEBUG_MODE", False))

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:3000")
API_URL = os.getenv("API_URL", f"{BASE_URL}/api")

SLACK_TOKEN = os.getenv("SLACK_TOKEN") or None
