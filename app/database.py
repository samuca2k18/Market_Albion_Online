# app/database.py
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import settings


# On serverless environments (e.g. Vercel), each function invocation is
# short-lived and cannot reuse connections across requests. SQLAlchemy's
# internal pool would hold connections open indefinitely, quickly hitting
# Supabase's "Max client connections reached" limit.
# NullPool disables the internal pool entirely — connections are opened and
# closed on every request. Supabase PgBouncer (port 6543) handles actual
# connection reuse on its side, which is the correct approach here.
engine = create_engine(
    settings.DATABASE_URL,
    poolclass=NullPool,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Dependência de sessão de banco de dados para o FastAPI.

    Uso:
        db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()