"""Centralised settings loaded from environment / .env file."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root if present
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


def _bool(s: str) -> bool:
    return s.strip().lower() in ("1", "true", "yes", "on")


class Settings:
    DISCOGS_TOKEN: str = os.environ.get("DISCOGS_TOKEN", "")
    DISCOGS_USER_AGENT: str = os.environ.get(
        "DISCOGS_USER_AGENT", "VinylCollector/0.1"
    )
    DISCOGS_CACHE_TTL: int = int(os.environ.get("DISCOGS_CACHE_TTL", "86400"))

    APP_PASSWORD: str = os.environ.get("APP_PASSWORD", "")
    SESSION_SECRET: str = os.environ.get("SESSION_SECRET", "")
    COOKIE_SECURE: bool = _bool(os.environ.get("COOKIE_SECURE", "false"))

    DATA_DIR: Path = PROJECT_ROOT / "data"
    DB_PATH: Path = DATA_DIR / "vinyl.db"

    def validate(self) -> None:
        if not self.DISCOGS_TOKEN:
            raise RuntimeError(
                "DISCOGS_TOKEN is not set. Copy .env.example to .env and fill it in."
            )
        if not self.APP_PASSWORD:
            raise RuntimeError("APP_PASSWORD is not set in .env.")
        if not self.SESSION_SECRET or len(self.SESSION_SECRET) < 32:
            raise RuntimeError(
                "SESSION_SECRET must be set in .env and at least 32 chars. "
                "Generate one with: "
                "python -c \"import secrets; print(secrets.token_urlsafe(32))\""
            )
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)


settings = Settings()
