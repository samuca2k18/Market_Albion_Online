import pytest
from app import models

# Dados de teste reutilizáveis
USER_DATA = {
    "username": "testuser",
    "email": "test@example.com",
    "password": "senha123"
}


def test_signup_success(client, db):
    """Testa criação de usuário com sucesso."""
    # Cleanup para garantir que o usuário não exista
    user = db.query(models.User).filter_by(username=USER_DATA["username"]).first()
    if user:
        # Deleta dependências primeiro
        db.query(models.PriceAlert).filter_by(user_id=user.id).delete()
        db.query(models.UserNotification).filter_by(user_id=user.id).delete()
        db.delete(user)
        db.commit()

    response = client.post("/signup", json=USER_DATA)
    if response.status_code != 201:
        print(f"Error: {response.json()}")
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"
    # Nunca deve retornar a senha!
    assert "hashed_password" not in data


def test_signup_duplicate_username(client, db):
    """Testa que não é possível criar dois usuários com mesmo username."""
    # Cleanup inicial
    user = db.query(models.User).filter_by(username=USER_DATA["username"]).first()
    if user:
        db.query(models.PriceAlert).filter_by(user_id=user.id).delete()
        db.query(models.UserNotification).filter_by(user_id=user.id).delete()
        db.delete(user)
        db.commit()

    client.post("/signup", json=USER_DATA)  # Primeiro cadastro

    response = client.post("/signup", json=USER_DATA)  # Segundo (duplicado)
    assert response.status_code == 400
    assert "já cadastrado" in response.json()["detail"]


def test_login_unverified_email(client, db):
    """Testa que login é bloqueado se e-mail não foi verificado."""
    unverified_user = {
        "username": "unverified_user",
        "email": "unverified@example.com",
        "password": "senha123"
    }
    
    # Cleanup
    user = db.query(models.User).filter_by(username=unverified_user["username"]).first()
    if user:
        db.query(models.PriceAlert).filter_by(user_id=user.id).delete()
        db.query(models.UserNotification).filter_by(user_id=user.id).delete()
        db.delete(user)
        db.commit()

    client.post("/signup", json=unverified_user)

    response = client.post("/login", data={
        "username": "unverified_user",
        "password": "senha123"
    })
    # Seu código retorna 403 para e-mail não verificado
    assert response.status_code == 403
    assert "não verificado" in response.json()["detail"]


def test_login_wrong_password(client):
    """Testa login com senha errada."""
    response = client.post("/login", data={
        "username": "testuser",
        "password": "senhaerrada"
    })
    assert response.status_code == 401