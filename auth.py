# auth.py
import os
from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import jwt
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

# Configurações de segurança
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError(
        "SECRET_KEY não configurada. Configure no arquivo .env. "
        "Gere uma chave segura com: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
    )

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

# Contexto de criptografia usando pbkdf2_sha256 (sem limite de 72 bytes)
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def get_password_hash(password: str) -> str:
    """
    Gera hash seguro da senha usando PBKDF2-SHA256.
    
    Args:
        password: Senha em texto plano
        
    Returns:
        Hash da senha
    """
    if not password or len(password) < 6:
        raise ValueError("Senha deve ter pelo menos 6 caracteres")
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica se a senha em texto plano corresponde ao hash.
    
    Args:
        plain_password: Senha em texto plano
        hashed_password: Hash da senha armazenado
        
    Returns:
        True se a senha corresponder, False caso contrário
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    Cria um token JWT de acesso.
    
    Args:
        data: Dados a serem codificados no token
        expires_delta: Tempo de expiração personalizado (opcional)
        
    Returns:
        Token JWT codificado
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
