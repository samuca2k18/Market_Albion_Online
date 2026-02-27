import pytest
from datetime import datetime, timedelta, timezone
from app import models

def test_alert_checker_http_endpoint(client, db):
    """
    Testa se o endpoint /alerts/run-check funciona sem erros de datetime.
    """
    try:
        # 1. Limpa e cria um usuário (Deleta alertas primeiro para evitar ForeignKeyViolation)
        user = db.query(models.User).filter_by(username="checkeruser").first()
        if user:
            db.query(models.PriceAlert).filter_by(user_id=user.id).delete()
            db.delete(user)
            db.commit()

        user = models.User(
            username="checkeruser",
            email="checker@example.com",
            hashed_password="...",
            is_verified=True
        )
        db.add(user)
        db.commit()

        # 2. Cria um alerta com last_triggered_at AWARE
        last_triggered = datetime.now(timezone.utc) - timedelta(hours=2)
        alert = models.PriceAlert(
            user_id=user.id,
            item_id="T4_BAG",
            city="Caerleon",
            is_active=True,
            last_triggered_at=last_triggered,
            cooldown_minutes=60,
            target_price=1000
        )
        db.add(alert)
        db.commit()

        # 3. Chama o endpoint via client
        headers = {"X-Cron-Secret": "teste"} 
        response = client.post("/alerts/run-check", headers=headers)
        
        # O objetivo principal é garantir que não haja erro 500 (naive vs aware error)
        assert response.status_code != 500
        print(f"Status do Checker: {response.status_code}")
    finally:
        pass # A transação será revertida pela fixture 'db' se necessário
