import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, inspect
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db
from app.models import UserItem
from app.schemas import ItemCreate, ItemOut, ItemReorder
from app.utils.albion_index import buscar_item_por_nome

router = APIRouter(prefix="/items", tags=["Itens do Usuario"])
logger = logging.getLogger("albion_market")


def _normalize_lang(lang: str) -> str:
    lang_norm = (lang or "").lower().replace("-", "_")
    return lang_norm if lang_norm in ("pt_br", "en_us") else "pt_br"


def _supports_sort_order(db: Session) -> bool:
    """
    Compatibilidade com bancos legados que ainda nao possuem user_items.sort_order.
    """
    try:
        bind = db.get_bind()
        if bind is None:
            return True
        columns = {col.get("name") for col in inspect(bind).get_columns("user_items")}
        return "sort_order" in columns
    except Exception:
        return True


def resolve_to_unique_name(raw_name: str, lang: str = "pt_br") -> str:
    """
    Recebe nome PT/EN/UniqueName parcial e resolve para UniqueName valido.
    """
    lang_key = _normalize_lang(lang)
    name = (raw_name or "").strip()
    if not name:
        raise HTTPException(400, "Nome do item e obrigatorio")

    if name.upper().startswith("T") and "_" in name:
        return name.upper()

    candidatos = buscar_item_por_nome(name, lang_key)
    if not candidatos and lang_key == "pt_br":
        candidatos = buscar_item_por_nome(name, "en_us")
    if not candidatos:
        raise HTTPException(404, "Item nao encontrado na base do Albion")

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
    unique_name = resolve_to_unique_name(item.item_name, lang)
    supports_sort_order = _supports_sort_order(db)

    item_kwargs = {
        "user_id": user.id,
        "item_name": unique_name,
        "display_name": item.display_name,
    }

    if supports_sort_order:
        max_sort_order = (
            db.query(func.max(UserItem.sort_order))
            .filter(UserItem.user_id == user.id)
            .scalar()
        )
        item_kwargs["sort_order"] = (max_sort_order or 0) + 1

    db_item = UserItem(**item_kwargs)
    db.add(db_item)

    try:
        db.commit()
        db.refresh(db_item)
        return db_item
    except SQLAlchemyError:
        db.rollback()

        # Fallback automatico para schema antigo sem sort_order
        if supports_sort_order:
            logger.warning("Fallback add_item sem sort_order para schema legado.")
            db_item = UserItem(
                user_id=user.id,
                item_name=unique_name,
                display_name=item.display_name,
            )
            db.add(db_item)
            db.commit()
            db.refresh(db_item)
            return db_item

        raise


@router.get("/", response_model=list[ItemOut])
def my_items(db: Session = Depends(get_db), user=Depends(get_current_user)):
    query = db.query(UserItem).filter(UserItem.user_id == user.id)
    if _supports_sort_order(db):
        items = query.order_by(UserItem.sort_order.asc().nullslast(), UserItem.id.asc()).all()
    else:
        items = query.order_by(UserItem.id.asc()).all()

    for item in items:
        if item.sort_order is None:
            item.sort_order = 0

    return items


@router.put("/reorder")
def reorder_items(
    items_reorder: list[ItemReorder],
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    item_ids = [payload.id for payload in items_reorder]
    if not item_ids:
        return {"message": "Nothing to reorder"}

    if not _supports_sort_order(db):
        return {"message": "Sort order unavailable in current database schema"}

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
        raise HTTPException(404, "Item nao encontrado")
    db.delete(item)
    db.commit()
    return {"message": "Item removido"}
