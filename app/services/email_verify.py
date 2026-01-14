# app/services/email_verify.py
import secrets
from datetime import datetime, timedelta, timezone


def generate_verification_token() -> str:
    return secrets.token_urlsafe(32)


def token_expiration(hours: int = 24) -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=hours)

