from datetime import datetime, timezone
import secrets
import pytest

from app import models
from app.core.security import create_access_token, get_password_hash
from app.schemas import ItemOut
from app.services.email_verify import token_expiration


@pytest.fixture
def auth_header(db):
    timestamp = datetime.now(timezone.utc).timestamp()
    username = f"itemuser_{int(timestamp)}"

    new_user = models.User(
        username=username,
        email=f"item_{timestamp}@example.com",
        hashed_password=get_password_hash("senha123"),
        is_verified=True,
        verification_token=secrets.token_urlsafe(32),
        verification_token_expires_at=token_expiration(24),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    access_token = create_access_token({"sub": username})
    return {"Authorization": f"Bearer {access_token}"}

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


def test_item_out_normaliza_sort_order_null():
    item = ItemOut.model_validate(
        {
            "id": 1,
            "item_name": "T4_BAG",
            "display_name": "Bolsa do Adepto",
            "created_at": "2026-04-14T14:00:00Z",
            "sort_order": None,
        }
    )
    assert item.sort_order == 0


def test_add_item_duplicate_returns_400(client, auth_header):
    payload = {"item_name": "T4_BAG", "display_name": "Bolsa do Adepto"}

    first = client.post("/items/", json=payload, headers=auth_header)
    assert first.status_code == 200

    second = client.post("/items/", json=payload, headers=auth_header)
    assert second.status_code == 400
    assert "lista de monitoramento" in second.json()["detail"]
