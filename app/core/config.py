# app/core/config.py
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # === JWT / Security ===
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    CRON_SECRET: str | None = None

    # === Database ===
    DATABASE_URL: str

    # === Albion API ===
    ALBION_REGION: str = "europe"
    ALBION_BASE_URLS: dict = {
        "europe": "https://europe.albion-online-data.com/api/v2/stats/prices",
        "west": "https://west.albion-online-data.com/api/v2/stats/prices",
        "east": "https://east.albion-online-data.com/api/v2/stats/prices",
    }
    ALBION_VALID_REGIONS: list = ["europe", "west", "east"]
    ALBION_API_TIMEOUT: int = 15

    # === E-mail / SMTP / Resend ===
    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USER: str | None = None
    SMTP_PASS: str | None = None
    SMTP_FROM: str | None = None

    RESEND_API_KEY: str | None = None
    RESEND_FROM_EMAIL: str | None = None
    RESEND_REPLY_TO: str | None = None

    # === URLs ===
    APP_BASE_URL: str | None = None
    FRONTEND_URL: str | None = None

    # === Refresh token cookie ===
    REFRESH_COOKIE_NAME: str = "refresh_token"
    REFRESH_COOKIE_PATH: str = "/"
    REFRESH_COOKIE_DOMAIN: str | None = None
    REFRESH_COOKIE_SECURE: bool = False
    REFRESH_COOKIE_SAMESITE: str = "lax"  # lax | strict | none

    # === Default cities ===
    DEFAULT_CITIES: List[str] = [
        "Bridgewatch",
        "Martlock",
        "Thetford",
        "Lymhurst",
        "Fort Sterling",
        "Caerleon",
        "Brecilien",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


settings = Settings()
