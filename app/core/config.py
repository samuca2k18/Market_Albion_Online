# app/core/config.py
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # === JWT / Segurança ===
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60      # 1 hora (seguro)
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30        # refresh válido por 30 dias
    CRON_SECRET: str | None = None             # segredo para proteger /alerts/run-check

    # === Banco de Dados ===
    DATABASE_URL: str  # ← ESSA LINHA É OBRIGATÓRIA!

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
    # Estes campos existem apenas para que o Pydantic não acuse erro de "extra inputs"
    # quando estiverem definidos no .env. O serviço de e-mail hoje lê diretamente
    # via os.getenv, então aqui eles são opcionais.
    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USER: str | None = None
    SMTP_PASS: str | None = None
    SMTP_FROM: str | None = None

    RESEND_API_KEY: str | None = None
    RESEND_FROM_EMAIL: str | None = None
    RESEND_REPLY_TO: str | None = None

    # URLs auxiliares
    APP_BASE_URL: str | None = None
    FRONTEND_URL: str | None = None

    # === Cidades padrão ===
    DEFAULT_CITIES: List[str] = [
        "Bridgewatch", "Martlock", "Thetford", "Lymhurst",
        "FortSterling", "Caerleon"
    ]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Instância global
settings = Settings()