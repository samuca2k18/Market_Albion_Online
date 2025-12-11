# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, items, albion, health
from app.database import Base, engine
from sqlalchemy import inspect, text

Base.metadata.create_all(bind=engine)

# Migração leve: adiciona display_name se não existir (SQLite/Postgres)
with engine.connect() as conn:
    inspector = inspect(conn)
    cols = {c["name"] for c in inspector.get_columns("user_items")}
    if "display_name" not in cols:
        conn.execute(text("ALTER TABLE user_items ADD COLUMN display_name VARCHAR"))
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

@app.get("/")
def root():
    return {"message": "Albion Market API rodando!"}