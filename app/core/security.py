# app/core/security.py
from datetime import datetime, timedelta
from typing import Optional

from passlib.context import CryptContext
from jose import jwt
from app.core.config import settings

# ==================== HASH DE SENHA ====================
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def get_password_hash(password: str) -> str:
    """Gera hash seguro da senha."""
    if len(password) < 6:
        raise ValueError("A senha deve ter pelo menos 6 caracteres")
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica se a senha corresponde ao hash."""
    return pwd_context.verify(plain_password, hashed_password)


# ==================== JWT TOKENS ====================
ALGORITHM = settings.ALGORITHM
SECRET_KEY = settings.SECRET_KEY
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Cria um token JWT de acesso.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),  # issued at
        "scope": "access_token"
    })
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """Token de refresh (opcional, para futuro)"""
    return create_access_token(data, expires_delta=timedelta(days=30))