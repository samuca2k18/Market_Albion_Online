# app/main.py
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text
from apscheduler.schedulers.background import BackgroundScheduler

from app.database import Base, engine, SessionLocal
from app.routers import alerts, auth, items, albion, health

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Cria / actualiza as tabelas no banco de dados
# ---------------------------------------------------------------------------
Base.metadata.create_all(bind=engine)

# Migração leve: garante colunas legadas (dev / banco antigo)
with engine.connect() as conn:
    inspector = inspect(conn)

    # user_items: display_name
    cols_user_items = {c["name"] for c in inspector.get_columns("user_items")}
    if "display_name" not in cols_user_items:
        conn.execute(text("ALTER TABLE user_items ADD COLUMN display_name VARCHAR"))
        conn.commit()

    # users: campos de verificação de e-mail
    cols_users = {c["name"] for c in inspector.get_columns("users")}
    if "is_verified" not in cols_users:
        conn.execute(
            text("ALTER TABLE users ADD COLUMN is_verified BOOLEAN NOT NULL DEFAULT FALSE")
        )
        conn.commit()

    if "verification_token" not in cols_users:
        conn.execute(text("ALTER TABLE users ADD COLUMN verification_token VARCHAR"))
        conn.commit()

    if "verification_token_expires_at" not in cols_users:
        conn.execute(
            text(
                "ALTER TABLE users ADD COLUMN verification_token_expires_at TIMESTAMPTZ"
            )
        )
        conn.commit()


# ---------------------------------------------------------------------------
# Scheduler — checa alertas de preço a cada 5 minutos
# ---------------------------------------------------------------------------
_scheduler = BackgroundScheduler(timezone="UTC")


def _scheduled_price_check() -> None:
    """Job executado pelo scheduler. Abre uma sessão própria e verifica alertas."""
    db = SessionLocal()
    try:
        from app.routers.alerts import run_checker_internal
        result = run_checker_internal(db)
        logger.info(
            "[Scheduler] Verificação concluída — checados=%d disparados=%d",
            result["checked"],
            result["triggered"],
        )
    except Exception as exc:  # nunca deixa o scheduler crashar
        logger.exception("[Scheduler] Erro durante verificação de alertas: %s", exc)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Lifespan (startup / shutdown)
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ---- startup ----
    _scheduler.add_job(
        _scheduled_price_check,
        trigger="interval",
        minutes=5,
        id="price_alert_check",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info("[Scheduler] Iniciado — verificação a cada 5 minutos.")
    yield
    # ---- shutdown ----
    _scheduler.shutdown(wait=False)
    logger.info("[Scheduler] Encerrado.")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Albion Market API",
    version="1.0.0",
    docs_url="/docs",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(items.router)
app.include_router(albion.router)
app.include_router(health.router)
app.include_router(alerts.router)


@app.get("/")
def root():
    return {"message": "Albion Market API rodando!"}
