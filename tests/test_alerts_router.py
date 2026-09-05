import pytest
from app import models, schemas
import os
from datetime import datetime, timezone

# Mock data for testing alerts
ALERT_DATA = {
    "item_id": "T4_BAG",
    "display_name": "Bag",
    "city": "Lymhurst",
    "quality": 1,
    "target_price": 1000,
    "percent_below": 10,
    "cooldown_minutes": 60,
    "use_ai_expected": False,
    "expected_price": None,
    "ai_days": 7,
    "ai_resolution": "1h",
    "ai_stat": "median",
    "ai_min_points": 10,
}

@pytest.fixture
def auth_header(db):
    """
    Fixture to create a verified user and return auth headers.
    ✅ CORRIGIDO: Só recebe `db` (sem `client`)
    Usa a MESMA SessionLocal que o client
    """
    timestamp = datetime.now(timezone.utc).timestamp()
    username = f"alertuser_{int(timestamp)}"
    
    user_data = {
        "username": username,
        "email": f"alert_{timestamp}@example.com",
        "password": "senha123"
    }
    
    # Cleanup
    user = db.query(models.User).filter_by(username=username).first()
    if user:
        db.query(models.PriceAlert).filter_by(user_id=user.id).delete()
        db.query(models.UserNotification).filter_by(user_id=user.id).delete()
        db.delete(user)
        db.commit()
    
    # Criar usuário DIRETO no BD
    from app.core.security import get_password_hash
    from app.services.email_verify import token_expiration
    import secrets
    
    token = secrets.token_urlsafe(32)
    
    new_user = models.User(
        username=username,
        email=user_data["email"],
        hashed_password=get_password_hash(user_data["password"]),
        is_verified=True,
        verification_token=token,
        verification_token_expires_at=token_expiration(24),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Verificar que foi criado
    user = db.query(models.User).filter_by(username=username).first()
    if not user:
        raise Exception("Failed to create user in auth_header fixture")
    
    # ✅ Gera token JWT direto
    from app.core.security import create_access_token
    access_token = create_access_token({"sub": username})
    
    return {"Authorization": f"Bearer {access_token}"}


def test_create_alert(client, auth_header):
    """Testa a criação de um alerta."""
    response = client.post("/alerts/", json=ALERT_DATA, headers=auth_header)
    assert response.status_code == 200
    data = response.json()
    assert data["item_id"] == ALERT_DATA["item_id"]
    assert data["city"] == ALERT_DATA["city"]


def test_list_alerts(client, auth_header):
    """Testa a listagem de alertas."""
    # Create an alert first
    client.post("/alerts/", json=ALERT_DATA, headers=auth_header)
    
    response = client.get("/alerts/", headers=auth_header)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


def test_delete_alert(client, auth_header):
    """Testa a exclusão de um alerta."""
    # Create an alert first
    create_res = client.post("/alerts/", json=ALERT_DATA, headers=auth_header)
    alert_id = create_res.json()["id"]
    
    response = client.delete(f"/alerts/{alert_id}", headers=auth_header)
    assert response.status_code == 200
    assert response.json()["ok"] == True


def test_run_checker_manual(client):
    """Testa o disparo manual do verificador com secret."""
    os.environ["CRON_SECRET"] = "testsecret"
    headers = {"x-cron-secret": "testsecret"}
    
    response = client.post("/alerts/run-check", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "checked" in data
    assert "triggered" in data
    assert isinstance(data["checked"], int)
    assert isinstance(data["triggered"], int)


def test_run_checker_vercel_cron_creates_notification(client, auth_header, monkeypatch):
    """Vercel Cron usa GET com Authorization: Bearer CRON_SECRET."""
    monkeypatch.setenv("CRON_SECRET", "testsecret")
    monkeypatch.setattr(
        "app.routers.alerts.get_prices",
        lambda items, cities, qualities: [{"sell_price_min": 500}],
    )
    monkeypatch.setattr(
        "app.routers.alerts.send_price_alert_email",
        lambda **kwargs: None,
    )

    create_res = client.post("/alerts/", json=ALERT_DATA, headers=auth_header)
    assert create_res.status_code == 200

    run_res = client.get(
        "/alerts/run-check",
        headers={"Authorization": "Bearer testsecret"},
    )
    assert run_res.status_code == 200
    assert run_res.json()["triggered"] == 1

    notifications_res = client.get("/alerts/notifications", headers=auth_header)
    assert notifications_res.status_code == 200
    notifications = notifications_res.json()
    assert len(notifications) == 1
    assert notifications[0]["is_read"] is False
    assert "Bag chegou a 500" in notifications[0]["body"]

    read_res = client.post(
        f"/alerts/notifications/{notifications[0]['id']}/read",
        headers=auth_header,
    )
    assert read_res.status_code == 200

    unread_res = client.get(
        "/alerts/notifications",
        params={"unread": True},
        headers=auth_header,
    )
    assert unread_res.status_code == 200
    assert unread_res.json() == []


def test_run_checker_invalid_secret(client):
    """Testa o disparo manual com secret inválido."""
    os.environ["CRON_SECRET"] = "testsecret"
    headers = {"x-cron-secret": "wrongsecret"}
    
    response = client.post("/alerts/run-check", headers=headers)
    assert response.status_code == 401
    assert "Invalid secret" in response.json()["detail"]


def test_run_checker_without_configured_secret(client, monkeypatch):
    """Endpoint deve falhar se CRON_SECRET não estiver configurado."""
    monkeypatch.delenv("CRON_SECRET", raising=False)
    response = client.post("/alerts/run-check", headers={"x-cron-secret": "any"})
    assert response.status_code == 503
    assert "CRON_SECRET not configured" in response.json()["detail"]
