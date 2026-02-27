import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app.core.limiter import limiter

# Desativa o rate limiter durante os testes para evitar 429
limiter.enabled = False
os.environ["TESTING"] = "true"


@pytest.fixture(scope="function")
def test_engine():
    """
    ✅ CORRIGIDO: Usa SQLite :memory: com StaticPool para compartilhar conexão
    Múltiplas sessions usam a MESMA conexão (sem isolamento)
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # ← Compartilha a mesma conexão!
        echo=False
    )
    
    # Cria todas as tabelas
    Base.metadata.create_all(bind=engine)
    
    yield engine
    
    # Cleanup
    engine.dispose()


@pytest.fixture(scope="function")
def session_local(test_engine):
    """
    ✅ CORRIGIDO: SessionLocal que usa a mesma conexão compartilhada
    """
    return sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_engine
    )


@pytest.fixture(scope="function")
def db(session_local):
    """
    Fixture para acessar o banco de dados de teste diretamente.
    ✅ Usa a mesma SessionLocal que o client
    """
    session = session_local()
    yield session
    session.close()


@pytest.fixture(scope="function")
def client(session_local):
    """
    Cliente HTTP para fazer requisições nos testes.
    ✅ CORRIGIDO: Override get_db usa a mesma session_local
    """
    def override_get_db():
        db = session_local()
        try:
            yield db
        finally:
            db.close()
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    # Cleanup
    app.dependency_overrides.clear()


# ============================================================================
# FIXTURES AUXILIARES
# ============================================================================

@pytest.fixture(autouse=True)
def reset_limiter():
    """Garante que o limiter está sempre desativado em cada teste."""
    limiter.enabled = False
    yield
    limiter.enabled = False


@pytest.fixture(scope="session")
def anyio_backend():
    """Config para async tests (se usar pytest-asyncio)."""
    return "asyncio"