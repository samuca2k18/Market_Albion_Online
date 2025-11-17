# database.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

# Obtém a URL do banco de dados das variáveis de ambiente
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@localhost:5432/albion_market"
)

if not DATABASE_URL:
    raise ValueError("DATABASE_URL não configurada. Configure no arquivo .env")

# Configuração do engine com pool de conexões otimizado
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Verifica conexões antes de usar
    pool_size=5,  # Tamanho do pool de conexões
    max_overflow=10,  # Conexões adicionais permitidas
    pool_recycle=3600,  # Recicla conexões após 1 hora
    echo=False,  # Desabilita logs SQL (mude para True para debug)
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
