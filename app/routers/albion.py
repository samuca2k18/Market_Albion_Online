from fastapi import APIRouter, Depends, Query, HTTPException
from typing import List
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db
from app.utils.albion_client import get_prices, get_price_history
from app.utils.albion_index import buscar_item_por_nome
from app.core.config import settings
from app.models import UserItem

router = APIRouter(prefix="/albion", tags=["Albion Online"])


LANG_SLUG_TO_KEY = {"pt-br": "pt_br", "en-us": "en_us"}


def _validate_lang_slug(lang: str) -> str:
    key = LANG_SLUG_TO_KEY.get(lang.lower())
    if not key:
        raise HTTPException(400, "Idioma inválido, use pt-br ou en-us")
    return key


def _serialize_resultados(resultados: List[dict]):
    return [
        {
            "unique_name": r["UniqueName"],
            "name_pt": r.get("PT-BR", ""),
            "name_en": r.get("EN-US", ""),
            "matched": r.get("__matched", ""),
        }
        for r in resultados
    ]


def _normalize_lang(lang: str) -> str:
    lang_norm = (lang or "").lower().replace("-", "_")
    return lang_norm if lang_norm in ("pt_br", "en_us") else "pt_br"


@router.get("/search/pt-br")
def search_item_pt(q: str = Query(..., min_length=2)):
    """
    Busca itens por nome em PT-BR usando o índice nomes_pt_br.json.
    """
    resultados = buscar_item_por_nome(q, "pt_br")
    return _serialize_resultados(resultados)


@router.get("/search/en-us")
def search_item_en(q: str = Query(..., min_length=2)):
    """
    Busca itens por nome em EN-US usando o índice nomes_en_us.json.
    """
    resultados = buscar_item_por_nome(q, "en_us")
    return _serialize_resultados(resultados)


# Rota legada mantida para compatibilidade (usa PT-BR por padrão)
@router.get("/search")
def search_item(q: str = Query(..., min_length=2)):
    # Mantém compatibilidade aceitando PT-BR e, em fallback, EN-US
    resultados = buscar_item_por_nome(q, "pt_br")
    if not resultados:
        resultados = buscar_item_por_nome(q, "en_us")
    return _serialize_resultados(resultados)


def _resolver_lista_itens(
    raw_items: List[str], lang_key: str, permitir_fallback_en: bool = False
) -> List[str]:
    """
    Resolve nomes humanos para UniqueName respeitando o idioma.
    """
    resolved: List[str] = []
    for it in raw_items:
        if it.upper().startswith("T") and "_" in it:
            resolved.append(it.upper())
            continue

        candidatos = buscar_item_por_nome(it, lang_key)
        if not candidatos and permitir_fallback_en and lang_key == "pt_br":
            candidatos = buscar_item_por_nome(it, "en_us")
        if candidatos:
            resolved.append(candidatos[0]["UniqueName"])
    return resolved


def _buscar_precos_por_idioma(
    items: str,
    cities: str,
    qualities: str,
    lang_key: str,
    current_user,
    permitir_fallback_en: bool = False,
):
    raw_items = [i.strip() for i in items.split(",") if i.strip()]
    item_list = _resolver_lista_itens(
        raw_items, lang_key, permitir_fallback_en=permitir_fallback_en
    )

    if not item_list:
        raise HTTPException(404, "Nenhum item válido encontrado")

    city_list = [c.strip() for c in cities.split(",") if c.strip()]
    quality_list = [int(q) for q in qualities.split(",") if q.strip()]

    data = get_prices(item_list, city_list, quality_list)
    if not data:
        raise HTTPException(404, "Nenhum preço encontrado")

    # Retorna o mais barato por item
    cheapest_by_item = {}
    for d in data:
        item_id = d["item_id"]
        if (
            item_id not in cheapest_by_item
            or d["sell_price_min"] < cheapest_by_item[item_id]["price"]
        ):
            cheapest_by_item[item_id] = {
                "city": d["city"],
                "price": d["sell_price_min"],
                "quality": d["quality"],
                "enchantment": d.get("enchantment", 0),
                "updated": d["sell_price_min_date"],
            }

    return {"items": cheapest_by_item, "all_data": data}


@router.get("/prices/pt-br")
def get_prices_pt(
    items: str = Query(
        ...,
        description="Itens separados por vírgula (UniqueNames OU nomes PT-BR)",
    ),
    cities: str = Query(",".join(settings.DEFAULT_CITIES)),
    qualities: str = Query("1,2,3,4,5"),
    current_user=Depends(get_current_user),
):
    """
    Preços para múltiplos itens resolvendo nomes PT-BR.
    """
    return _buscar_precos_por_idioma(items, cities, qualities, "pt_br", current_user)


@router.get("/prices/en-us")
def get_prices_en(
    items: str = Query(
        ...,
        description="Itens separados por vírgula (UniqueNames OU nomes EN-US)",
    ),
    cities: str = Query(",".join(settings.DEFAULT_CITIES)),
    qualities: str = Query("1,2,3,4,5"),
    current_user=Depends(get_current_user),
):
    """
    Preços para múltiplos itens resolvendo nomes EN-US.
    """
    return _buscar_precos_por_idioma(items, cities, qualities, "en_us", current_user)


@router.get("/prices")
def get_prices_endpoint(
    items: str = Query(
        ...,
        description="Itens separados por vírgula (UniqueNames OU nomes PT/EN)",
    ),
    cities: str = Query(",".join(settings.DEFAULT_CITIES)),
    qualities: str = Query("1,2,3,4,5"),
    current_user=Depends(get_current_user),
):
    """
    Preços para múltiplos itens (legado, usa PT-BR como padrão).

    Aceita:
      - UniqueNames: T4_BAG,T4_BAG@1
      - Nomes humanos: 'bolsa do adepto, capa letal'
    Faz a resolução de nomes PT/EN -> UniqueName automaticamente.
    """
    return _buscar_precos_por_idioma(
        items, cities, qualities, "pt_br", current_user, permitir_fallback_en=True
    )


@router.get("/price-by-name")
def price_by_name(
    name: str = Query(..., description="Nome em PT-BR ou EN"),
    cities: str = Query(",".join(settings.DEFAULT_CITIES)),
    current_user=Depends(get_current_user),
):
    """
    Preço para um único item a partir de nome humano (PT/EN).
    """
    return price_by_name_pt(name=name, cities=cities, current_user=current_user)


def _preco_por_nome(
    name: str, cities: str, lang_key: str, permitir_fallback_en: bool = False
):
    itens = buscar_item_por_nome(name, lang_key)
    if not itens and permitir_fallback_en and lang_key == "pt_br":
        itens = buscar_item_por_nome(name, "en_us")
    if not itens:
        raise HTTPException(404, "Item não encontrado")

    unique = itens[0]["UniqueName"]
    city_list = [c.strip() for c in cities.split(",") if c.strip()]
    data = get_prices([unique], city_list)

    if not data:
        raise HTTPException(404, "Sem preços disponíveis no momento")

    cheapest = min(data, key=lambda x: x["sell_price_min"])

    return {
        "searched": name,
        "item_found": unique,
        "name_pt": itens[0].get("PT-BR", ""),
        "name_en": itens[0].get("EN-US", ""),
        "cheapest_city": cheapest["city"],
        "price": cheapest["sell_price_min"],
        "quality": cheapest["quality"],
        "updated_at": cheapest["sell_price_min_date"],
        "all_prices": data[:10],
    }


@router.get("/price-by-name/pt-br")
def price_by_name_pt(
    name: str = Query(..., description="Nome em PT-BR"),
    cities: str = Query(",".join(settings.DEFAULT_CITIES)),
    current_user=Depends(get_current_user),
):
    return _preco_por_nome(name, cities, "pt_br", permitir_fallback_en=True)


@router.get("/price-by-name/en-us")
def price_by_name_en(
    name: str = Query(..., description="Nome em EN-US"),
    cities: str = Query(",".join(settings.DEFAULT_CITIES)),
    current_user=Depends(get_current_user),
):
    return _preco_por_nome(name, cities, "en_us")


@router.get("/history/{item_id}")
def price_history(
    item_id: str,
    days: int = Query(7, ge=1, le=30, description="Quantos dias de histórico"),
    cities: str = Query("Caerleon", description="Cidades separadas por vírgula"),
    resolution: str = Query("6h", description="1h, 6h ou 24h"),
    current_user=Depends(get_current_user),
):
    """
    Histórico de preços para uso no gráfico do frontend.
    """
    city_list = [c.strip() for c in cities.split(",") if c.strip()]

    history = get_price_history(
        item_id=item_id.upper(),
        locations=city_list,
        days=days,
        time_resolution=resolution,
    )

    # Se a API não devolver nada, não é erro de servidor, só "sem dados"
    if not history:
        return {
            "item": item_id,
            "cities": city_list,
            "resolution": resolution,
            "days": days,
            "data": [],
        }

    return {
        "item": item_id,
        "cities": city_list,
        "resolution": resolution,
        "days": days,
        "data": history,
    }


@router.get("/my-items-prices")
def my_items_prices(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    lang: str = Query(
        "pt_br",
        description="Idioma para resolver nomes não únicos (pt_br ou en_us)",
    ),
):
    """
    Retorna os preços dos itens salvos pelo usuário.

    Se houver itens antigos salvos com nomes humanos (BOLSA, BAG),
    tenta resolver para UniqueName antes de chamar a API.
    """
    user_items = db.query(UserItem).filter(UserItem.user_id == current_user.id).all()
    raw_names = [item.item_name for item in user_items]
    display_map = {item.item_name.upper(): item.display_name for item in user_items}

    if not raw_names:
        return []

    lang_key = _normalize_lang(lang)
    resolved_names: List[str] = []
    for name in raw_names:
        if name.upper().startswith("T") and "_" in name:
            resolved_names.append(name.upper())
        else:
            candidatos = buscar_item_por_nome(name, lang_key)
            if not candidatos and lang_key == "pt_br":
                candidatos = buscar_item_por_nome(name, "en_us")
            if candidatos:
                resolved_names.append(candidatos[0]["UniqueName"])

    if not resolved_names:
        return []

    raw_data = get_prices(resolved_names)

    result = []
    for entry in raw_data:
        if entry.get("sell_price_min", 0) <= 0:
            continue
        display_name = display_map.get(entry["item_id"].upper())
        result.append(
            {
                "item_name": entry["item_id"],  # sempre UniqueName aqui
                "display_name": display_name,
                "city": entry["city"],
                "price": entry["sell_price_min"],
                "quality": entry["quality"],
                "enchantment": entry.get("enchantment", 0),
            }
        )

    # Ordena do mais barato pro mais caro
    result.sort(key=lambda x: x["price"])
    return result
