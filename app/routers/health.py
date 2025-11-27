# app/routers/health.py
from fastapi import APIRouter

router = APIRouter(tags=["Sistema"])

@router.get("/health")
def health():
    return {"status": "ok", "service": "Albion Market API"}