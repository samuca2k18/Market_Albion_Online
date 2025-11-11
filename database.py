# database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# conexão direta com o banco Supabase
DATABASE_URL = "postgresql+psycopg2://postgres.odxnvwlqukeqpkaztyso:senha132@aws-1-sa-east-1.pooler.supabase.com:6543/postgres"

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
