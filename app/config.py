"""Centralised settings loaded from environment / .env file."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root if present
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


class Settings:
    DISCOGS_TOKEN: str = os.environ.get("DISCOGS_TOKEN", "")
    DISCOGS_USER_AGENT: str = os.environ.get(
        "DISCOGS_USER_AGENT", "VinylCollector/0.1"
    )
    DISCOGS_CACHE_TTL: int = int(os.environ.get("DISCOGS_CACHE_TTL", "86400"))

    DATA_DIR: Path = PROJECT_ROOT / "data"
    DB_PATH: Path = DATA_DIR / "vinyl.db"

    def validate(self) -> None:
        if not self.DISCOGS_TOKEN:
            raise RuntimeError(
                "DISCOGS_TOKEN is not set. Copy .env.example to .env and fill it in."
            )
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)


settings = Settings()
