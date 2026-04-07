from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import UserItem
from app.schemas import ItemCreate, ItemOut, ItemReorder
from app.dependencies import get_db, get_current_user
from app.utils.albion_index import buscar_item_por_nome

router = APIRouter(prefix="/items", tags=["Itens do Usuário"])


def _normalize_lang(lang: str) -> str:
    lang_norm = (lang or "").lower().replace("-", "_")
    return lang_norm if lang_norm in ("pt_br", "en_us") else "pt_br"


def resolve_to_unique_name(raw_name: str, lang: str = "pt_br") -> str:
    """
    Recebe um nome qualquer (PT/EN/UniqueName parcial) e tenta resolver
    para um UniqueName válido (ex: T4_BAG, T4_BAG@1).
    """
    lang_key = _normalize_lang(lang)
    name = (raw_name or "").strip()
    if not name:
        raise HTTPException(400, "Nome do item é obrigatório")

    # Se já parece um UniqueName (T4_BAG, T5_CAPE@1, etc.), aceita direto
    if name.upper().startswith("T") and "_" in name:
        return name.upper()

    # Tenta resolver pelo índice PT/EN
    candidatos = buscar_item_por_nome(name, lang_key)
    if not candidatos and lang_key == "pt_br":
        candidatos = buscar_item_por_nome(name, "en_us")
    if not candidatos:
        raise HTTPException(404, "Item não encontrado na base do Albion")

    return candidatos[0]["UniqueName"]


@router.post("/", response_model=ItemOut)
def add_item(
    item: ItemCreate,
    lang: str = Query(
        "pt_br",
        description="Idioma usado para nomes humanos (pt_br ou en_us)",
    ),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Adiciona um item para o usuário.

    Aceita:
    - UniqueName direto: "T4_BAG", "T4_BAG@1"
    - Nome PT-BR: "Bolsa do Adepto"
    - Nome EN: "Adept's Bag"
    """
    unique_name = resolve_to_unique_name(item.item_name, lang)

    max_sort_order = (
        db.query(func.max(UserItem.sort_order))
        .filter(UserItem.user_id == user.id)
        .scalar()
    )
    next_sort_order = (max_sort_order or 0) + 1

    db_item = UserItem(
        user_id=user.id,
        item_name=unique_name,
        display_name=item.display_name,
        sort_order=next_sort_order,
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


@router.get("/", response_model=list[ItemOut])
def my_items(db: Session = Depends(get_db), user=Depends(get_current_user)):
    return db.query(UserItem).filter(UserItem.user_id == user.id).order_by(UserItem.sort_order.asc(), UserItem.id.asc()).all()


@router.put("/reorder")
def reorder_items(
    items_reorder: list[ItemReorder],
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Atualiza a ordem dos itens (drag & drop).
    Recebe um array com id e a nova ordem.
    """
    item_ids = [payload.id for payload in items_reorder]
    if not item_ids:
        return {"message": "Nothing to reorder"}

    db_items = (
        db.query(UserItem)
        .filter(UserItem.user_id == user.id, UserItem.id.in_(item_ids))
        .all()
    )
    by_id = {item.id: item for item in db_items}
    for payload in items_reorder:
        db_item = by_id.get(payload.id)
        if db_item:
            db_item.sort_order = payload.sort_order

    db.commit()
    return {"message": "D&D Reorder applied successfully"}


@router.delete("/{item_id}")
def delete_item(
    item_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    item = (
        db.query(UserItem)
        .filter(UserItem.id == item_id, UserItem.user_id == user.id)
        .first()
    )
    if not item:
        raise HTTPException(404, "Item não encontrado")
    db.delete(item)
    db.commit()
    return {"message": "Item removido"}
