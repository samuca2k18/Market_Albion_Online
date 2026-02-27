# app/main.py
import logging
import sys
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.limiter import limiter
from app.database import Base, engine, SessionLocal
from app.routers import alerts, auth, items, albion, health

# ── Logging ────────────────────────────────────────────────────────────────
logger = logging.getLogger("albion_market")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        '{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","msg":"%(message)s"}',
        datefmt="%Y-%m-%dT%H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# Cria tabelas que ainda não existem (DEV); em produção use `alembic upgrade head`
if os.getenv("TESTING") != "true":
    Base.metadata.create_all(bind=engine)


# ── Lifespan (startup / shutdown) ──────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("API iniciada.")
    yield
    logger.info("API encerrada.")


# ── App ────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Albion Market API",
    version="1.0.0",
    docs_url="/docs",
    lifespan=lifespan,
)

# Registra rate limiter e handler de 429
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://www.marketalbionbr.com.br",
        "https://marketalbionbr.com.br",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
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