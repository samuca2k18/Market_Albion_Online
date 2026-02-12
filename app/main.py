# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text
from app.database import Base, engine
from app.routers import alerts
from app.routers import auth, items, albion, health

Base.metadata.create_all(bind=engine)

# Migração leve: cria colunas se não existirem (dev)
with engine.connect() as conn:
    inspector = inspect(conn)

    # user_items: display_name
    cols_user_items = {c["name"] for c in inspector.get_columns("user_items")}
    if "display_name" not in cols_user_items:
        conn.execute(text("ALTER TABLE user_items ADD COLUMN display_name VARCHAR"))
        conn.commit()

    # users: campos de verificação
    cols_users = {c["name"] for c in inspector.get_columns("users")}
    if "is_verified" not in cols_users:
        conn.execute(text("ALTER TABLE users ADD COLUMN is_verified BOOLEAN NOT NULL DEFAULT FALSE"))
        conn.commit()

    if "verification_token" not in cols_users:
        conn.execute(text("ALTER TABLE users ADD COLUMN verification_token VARCHAR"))
        conn.commit()

    if "verification_token_expires_at" not in cols_users:
        conn.execute(text("ALTER TABLE users ADD COLUMN verification_token_expires_at TIMESTAMPTZ"))
        conn.commit()

app = FastAPI(
    title="Albion Market API",
    version="1.0.0",
    docs_url="/docs"
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
