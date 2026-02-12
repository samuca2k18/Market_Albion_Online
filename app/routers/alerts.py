from fastapi import APIRouter, Depends, HTTPException, Header, Query
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional, List
import os
import statistics

from app.database import get_db
from app.dependencies import get_current_user
from app import models, schemas
from app.utils.albion_client import get_prices, get_price_history
from app.services.mailer import send_price_alert_email

router = APIRouter(prefix="/alerts", tags=["alerts"])

CRON_SECRET = os.getenv("CRON_SECRET")


def _now_utc() -> datetime:
    return datetime.utcnow()


def _extract_history_prices(history: list) -> list[float]:
    """
    Tenta extrair preços do histórico da Albion API de forma robusta,
    porque o formato pode variar (sell_price_min / avg / etc).
    """
    candidates = []
    for row in history or []:
        if not isinstance(row, dict):
            continue

        # chaves mais comuns
        for k in (
            "sell_price_min",
            "sell_price_min_avg",
            "avg_sell_price",
            "sell_price_avg",
            "price",
            "value",
        ):
            v = row.get(k)
            if isinstance(v, (int, float)) and v > 0:
                candidates.append(float(v))
                break
    return candidates


def _compute_expected_price_from_history(
    item_id: str,
    cities: list[str],
    days: int,
    resolution: str,
    stat: str = "median",
    min_points: int = 10,
) -> Optional[float]:
    history = get_price_history(
        item_id=item_id.upper(),
        locations=cities,
        days=days,
        time_resolution=resolution,
    )

    values = _extract_history_prices(history)
    if len(values) < min_points:
        return None

    if stat == "mean":
        return float(sum(values) / len(values))

    # padrão: mediana (melhor contra picos/manipulação)
    return float(statistics.median(values))


@router.post("/", response_model=schemas.PriceAlertOut)
def create_alert(
    payload: schemas.PriceAlertCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    alert = models.PriceAlert(
        user_id=user.id,
        item_id=payload.item_id.upper(),
        display_name=payload.display_name,
        city=payload.city,
        quality=payload.quality,
        # regra manual
        target_price=payload.target_price,
        expected_price=payload.expected_price,
        percent_below=payload.percent_below,
        # IA
        use_ai_expected=payload.use_ai_expected,
        ai_days=payload.ai_days,
        ai_resolution=payload.ai_resolution,
        ai_stat=payload.ai_stat,
        ai_min_points=payload.ai_min_points,
        # anti-spam
        cooldown_minutes=payload.cooldown_minutes,
        is_active=True,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


@router.get("/", response_model=List[schemas.PriceAlertOut])
def list_alerts(
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    return db.query(models.PriceAlert).filter_by(user_id=user.id).all()


@router.delete("/{alert_id}")
def delete_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    alert = db.query(models.PriceAlert).filter_by(id=alert_id, user_id=user.id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    db.delete(alert)
    db.commit()
    return {"ok": True}


@router.get("/notifications", response_model=List[schemas.NotificationOut])
def list_notifications(
    unread: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    q = db.query(models.UserNotification).filter_by(user_id=user.id)
    if unread is True:
        q = q.filter_by(is_read=False)
    return q.order_by(models.UserNotification.created_at.desc()).all()


@router.post("/notifications/{nid}/read")
def mark_read(
    nid: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    notif = db.query(models.UserNotification).filter_by(id=nid, user_id=user.id).first()
    if not notif:
        raise HTTPException(status_code=404)
    notif.is_read = True
    db.commit()
    return {"ok": True}


@router.post("/run-check")
def run_checker(
    x_cron_secret: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    # protege cron
    if CRON_SECRET and x_cron_secret != CRON_SECRET:
        raise HTTPException(status_code=401, detail="Invalid secret")

    alerts: list[models.PriceAlert] = (
        db.query(models.PriceAlert).filter_by(is_active=True).all()
    )

    checked = 0
    triggered = 0

    for alert in alerts:
        checked += 1

        cities = [alert.city] if alert.city else None
        qualities = [alert.quality] if alert.quality else None

        data = get_prices([alert.item_id], cities, qualities)
        valid = [
            d.get("sell_price_min")
            for d in (data or [])
            if isinstance(d.get("sell_price_min"), (int, float)) and d["sell_price_min"] > 0
        ]
        if not valid:
            continue

        current_price = float(min(valid))

        # cooldown anti-spam
        if alert.last_triggered_at:
            if (_now_utc() - alert.last_triggered_at) < timedelta(
                minutes=alert.cooldown_minutes
            ):
                continue

        item_label = alert.display_name or alert.item_id

        # ---------------------
        # Regra 1: target_price manual
        # ---------------------
        if alert.target_price and current_price <= float(alert.target_price):
            _fire_alert(db, alert, item_label, current_price, expected_price=None)
            triggered += 1
            continue

        # ---------------------
        # Regra 2: % abaixo do esperado (manual OU IA)
        # ---------------------
        if not alert.percent_below:
            continue

        expected = None

        # manual
        if alert.expected_price:
            expected = float(alert.expected_price)

        # IA: calcula baseline pelo histórico
        if expected is None and alert.use_ai_expected:
            city_list = [alert.city] if alert.city else ["Caerleon"]
            expected = _compute_expected_price_from_history(
                item_id=alert.item_id,
                cities=city_list,
                days=alert.ai_days,
                resolution=alert.ai_resolution,
                stat=alert.ai_stat,
                min_points=alert.ai_min_points,
            )

            # fallback: se não tiver histórico suficiente, usa o “preço atual” como baseline
            if expected is None:
                expected = current_price

            alert.last_expected_price = expected
            alert.last_expected_at = _now_utc()

        if expected is None:
            continue

        threshold = expected * (1 - float(alert.percent_below) / 100.0)

        if current_price <= threshold:
            _fire_alert(db, alert, item_label, current_price, expected_price=expected)
            triggered += 1

    db.commit()
    return {"checked": checked, "triggered": triggered}


def _fire_alert(
    db: Session,
    alert: models.PriceAlert,
    item_label: str,
    current_price: float,
    expected_price: Optional[float],
):
    # notificação no site
    if expected_price:
        body = (
            f"{item_label} chegou a {current_price:.0f} "
            f"(esperado ~{expected_price:.0f}, -{alert.percent_below:.0f}%)."
        )
    else:
        body = f"{item_label} chegou a {current_price:.0f}."

    notif = models.UserNotification(
        user_id=alert.user_id,
        title="🚨 Oportunidade detectada!",
        body=body,
    )
    db.add(notif)

    # e-mail
    user = db.query(models.User).filter_by(id=alert.user_id).first()
    if user and user.email:
        send_price_alert_email(
            to_email=user.email,
            item=item_label,
            current_price=current_price,
            city=alert.city,
            expected_price=expected_price,
            percent_below=float(alert.percent_below or 0),
        )

    alert.last_triggered_at = _now_utc()
