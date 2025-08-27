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
SPOTIFY_CLIENT_ID = os.getenv("LYKD_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("LYKD_CLIENT_SECRET")

API_PREFIX = os.getenv("API_PREFIX", "")
BACKEND_DIR = Path(__file__).parent
DATABASE_PATH = BACKEND_DIR / "lykd.sqlite"
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATABASE_PATH}")
PROJECT_PATH = BACKEND_DIR.parent

TESTING_MODE = parse_bool(os.getenv("TESTING_MODE", False))  # don't wait on retries
CACHE_ENABLED = parse_bool(os.getenv("CACHE_ENABLED", False))
HTTPS_VERIFY = parse_bool(os.getenv("HTTPS_VERIFY", True))

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:3000")
API_URL = os.getenv("API_URL", f"{BASE_URL}/api")

SLACK_TOKEN = os.getenv("SLACK_TOKEN") or None

# --- Email / SMTP configuration ---
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_USE_TLS = parse_bool(os.getenv("SMTP_USE_TLS", True))
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", "no-reply@lykd.app")
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "LYKD")
