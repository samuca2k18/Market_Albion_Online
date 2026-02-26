import pytest

# Dados de teste reutilizáveis
USER_DATA = {
    "username": "testuser",
    "email": "test@example.com",
    "password": "senha123"
}


def test_signup_success(client):
    """Testa criação de usuário com sucesso."""
    response = client.post("/signup", json=USER_DATA)
    if response.status_code != 201:
        print(f"Error: {response.json()}")
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"
    # Nunca deve retornar a senha!
    assert "hashed_password" not in data


def test_signup_duplicate_username(client):
    """Testa que não é possível criar dois usuários com mesmo username."""
    client.post("/signup", json=USER_DATA)  # Primeiro cadastro

    response = client.post("/signup", json=USER_DATA)  # Segundo (duplicado)
    assert response.status_code == 400
    assert "já cadastrado" in response.json()["detail"]


def test_login_unverified_email(client):
    """Testa que login é bloqueado se e-mail não foi verificado."""
    client.post("/signup", json={
        "username": "unverified_user",
        "email": "unverified@example.com",
        "password": "senha123"
    })

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