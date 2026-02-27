import pytest
from app import models
from datetime import datetime, timezone

# Dados de teste reutilizáveis - mas com cleanup
def get_unique_user_data():
    """Gera dados de usuário únicos baseado em timestamp."""
    timestamp = datetime.now(timezone.utc).timestamp()
    return {
        "username": f"testuser_{int(timestamp)}",
        "email": f"test_{timestamp}@example.com",
        "password": "senha123"
    }


def test_signup_success(client, db):
    """Testa criação de usuário com sucesso."""
    user_data = get_unique_user_data()
    
    # Cleanup (redundante mas seguro)
    user = db.query(models.User).filter_by(username=user_data["username"]).first()
    if user:
        db.query(models.PriceAlert).filter_by(user_id=user.id).delete()
        db.query(models.UserNotification).filter_by(user_id=user.id).delete()
        db.delete(user)
        db.commit()

    response = client.post("/signup", json=user_data)
    if response.status_code != 201:
        print(f"Error: {response.json()}")
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == user_data["username"]
    assert data["email"] == user_data["email"]
    # Nunca deve retornar a senha!
    assert "hashed_password" not in data


def test_signup_duplicate_username(client, db):
    """Testa que não é possível criar dois usuários com mesmo username."""
    user_data = get_unique_user_data()
    
    # Cleanup inicial
    user = db.query(models.User).filter_by(username=user_data["username"]).first()
    if user:
        db.query(models.PriceAlert).filter_by(user_id=user.id).delete()
        db.query(models.UserNotification).filter_by(user_id=user.id).delete()
        db.delete(user)
        db.commit()

    client.post("/signup", json=user_data)  # Primeiro cadastro

    response = client.post("/signup", json=user_data)  # Segundo (duplicado)
    assert response.status_code == 400
    assert "já cadastrado" in response.json()["detail"]


def test_login_unverified_email(client, db):
    """Testa que login é bloqueado se e-mail não foi verificado."""
    unverified_user = get_unique_user_data()
    
    # Cleanup
    user = db.query(models.User).filter_by(username=unverified_user["username"]).first()
    if user:
        db.query(models.PriceAlert).filter_by(user_id=user.id).delete()
        db.query(models.UserNotification).filter_by(user_id=user.id).delete()
        db.delete(user)
        db.commit()

    client.post("/signup", json=unverified_user)

    response = client.post("/login", data={
        "username": unverified_user["username"],
        "password": unverified_user["password"]
    })
    # Seu código retorna 403 para e-mail não verificado
    assert response.status_code == 403
    assert "não verificado" in response.json()["detail"]


def test_login_wrong_password(client, db):
    """Testa login com senha errada."""
    test_user = get_unique_user_data()
    
    # Cleanup
    user = db.query(models.User).filter_by(username=test_user["username"]).first()
    if user:
        db.query(models.PriceAlert).filter_by(user_id=user.id).delete()
        db.query(models.UserNotification).filter_by(user_id=user.id).delete()
        db.delete(user)
        db.commit()
    
    # Cria o usuário
    client.post("/signup", json=test_user)
    
    # Verifica a conta para poder fazer login
    user = db.query(models.User).filter_by(username=test_user["username"]).first()
    if user:
        user.is_verified = True
        db.commit()
    
    response = client.post("/login", data={
        "username": test_user["username"],
        "password": "senhaerrada"
    })
    assert response.status_code == 401