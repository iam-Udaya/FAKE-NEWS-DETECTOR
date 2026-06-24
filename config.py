"""
config.py - Centralized Configuration Management
=================================================
Uses @property on a class instance so every attribute access reads
from os.environ at call-time (not baked-in at class-definition time).
This means Streamlit's module cache never freezes stale empty values.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Resolve the .env file relative to THIS file so it works regardless of CWD
_ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH, override=True)


class _Config:
    """
    Configuration class using @property so each access reads live from
    os.environ. This avoids the Streamlit module-cache issue where
    class-level os.getenv() calls return empty strings on first import
    and never update.
    """

    # ─── Google Gemini ───────────────────────────────────────────────────────
    @property
    def GEMINI_API_KEY(self) -> str:
        return os.getenv("GEMINI_API_KEY", "").strip()

    GEMINI_MODEL: str = "gemini-2.5-flash"

    # ─── MongoDB ─────────────────────────────────────────────────────────────
    @property
    def MONGODB_URI(self) -> str:
        return os.getenv("MONGODB_URI", "").strip()

    @property
    def MONGODB_DB_NAME(self) -> str:
        return os.getenv("MONGODB_DB_NAME", "fake_news_detector").strip()

    MONGODB_COLLECTION: str = "analyses"

    # ─── App ──────────────────────────────────────────────────────────────────
    @property
    def APP_NAME(self) -> str:
        return os.getenv("APP_NAME", "Fake News Detector")

    @property
    def APP_VERSION(self) -> str:
        return os.getenv("APP_VERSION", "1.0.0")

    @property
    def DEBUG(self) -> bool:
        return os.getenv("DEBUG", "False").lower() == "true"

    # ─── Scraper ─────────────────────────────────────────────────────────────
    REQUEST_TIMEOUT: int = 15          # seconds
    MAX_ARTICLE_LENGTH: int = 10_000   # character cap sent to Gemini

    # ─── Verdict Thresholds ───────────────────────────────────────────────────
    VERDICT_REAL_MIN: int = 70
    VERDICT_SUSPICIOUS_MIN: int = 40

    def validate(self) -> list:
        """
        Validate required configuration keys.
        Reads live from os.environ so always reflects current .env state.

        Returns:
            List of missing key names (empty list = all configured).
        """
        missing = []
        if not self.GEMINI_API_KEY:
            missing.append("GEMINI_API_KEY")
        if not self.MONGODB_URI:
            missing.append("MONGODB_URI")
        return missing


# Singleton instance used throughout the project
config = _Config()
