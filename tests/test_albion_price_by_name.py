from datetime import datetime, timezone
from unittest.mock import patch

from app import models
from app.core.security import create_access_token, get_password_hash


def _auth_headers(db):
    timestamp = datetime.now(timezone.utc).timestamp()
    username = f"albionprice_{int(timestamp)}"

    user = models.User(
        username=username,
        email=f"{username}@example.com",
        hashed_password=get_password_hash("senha123"),
        is_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": username})
    return {"Authorization": f"Bearer {token}"}


@patch("app.routers.albion.get_prices")
@patch("app.routers.albion.buscar_item_por_nome")
def test_price_by_name_legacy_route_uses_helper_without_request(
    mock_search,
    mock_get_prices,
    client,
    db,
):
    """
    Regressão: /albion/price-by-name não pode quebrar por chamar outra rota decorada.
    """
    mock_search.return_value = [
        {
            "UniqueName": "T4_BAG",
            "PT-BR": "Bolsa do Adepto",
            "EN-US": "Adept's Bag",
        }
    ]
    mock_get_prices.return_value = [
        {
            "item_id": "T4_BAG",
            "city": "Caerleon",
            "sell_price_min": 1000,
            "quality": 1,
            "sell_price_min_date": "2026-04-16T00:00:00Z",
        }
    ]

    response = client.get(
        "/albion/price-by-name",
        params={"name": "Bolsa", "region": "europe"},
        headers=_auth_headers(db),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["item_found"] == "T4_BAG"
    assert payload["cheapest_city"] == "Caerleon"
    assert payload["price"] == 1000
