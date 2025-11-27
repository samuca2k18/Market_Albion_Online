# app/core/config.py
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # === JWT / Segurança ===
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # === Banco de Dados ===
    DATABASE_URL: str  # ← ESSA LINHA É OBRIGATÓRIA!

    # === Albion API ===
    ALBION_REGION: str = "europe"
    ALBION_BASE_URLS: dict = {
        "europe": "https://europe.albion-online-data.com/api/v2/stats/prices",
        "us": "https://us.albion-online-data.com/api/v2/stats/prices",
        "asia": "https://asia.albion-online-data.com/api/v2/stats/prices",
    }
    ALBION_API_TIMEOUT: int = 15

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