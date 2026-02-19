def test_health_ok(client):
    """Testa se o endpoint /health retorna status 200 e 'ok'."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_root(client):
    """Testa se a rota raiz retorna a mensagem da API."""
    response = client.get("/")
    assert response.status_code == 200
    assert "Albion Market API" in response.json()["message"]