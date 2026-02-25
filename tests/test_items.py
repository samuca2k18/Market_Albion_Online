def test_search_item_pt_br(client):
    """Testa busca de item em PT-BR."""
    response = client.get("/albion/search/pt-br?q=Bolsa")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_search_item_en_us(client):
    """Testa busca de item em EN-US."""
    response = client.get("/albion/search/en-us?q=Bag")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_search_query_muito_curta(client):
    """Testa que busca com menos de 2 caracteres retorna erro."""
    response = client.get("/albion/search/pt-br?q=a")
    assert response.status_code == 422  # FastAPI valida min_length=2