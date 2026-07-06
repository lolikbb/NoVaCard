import json
import datetime
from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..cryptobot import verify_webhook_signature
from .. import models
from ..notify import notify_user_paid

router = APIRouter()


@router.post("/webhook/cryptobot")
async def cryptobot_webhook(request: Request, db: Session = Depends(get_db)):
    body = await request.body()
    signature = request.headers.get("crypto-pay-api-signature")

    if not signature or not verify_webhook_signature(body, signature):
        raise HTTPException(403, "Неверная подпись")

    data = json.loads(body)
    if data.get("update_type") != "invoice_paid":
        return {"ok": True}

    invoice = data["payload"]
    order_id = int(invoice["payload"])
    order = db.query(models.Order).get(order_id)

    if not order or order.status == "paid":
        return {"ok": True}

    order.status = "paid"
    order.paid_at = datetime.datetime.utcnow()

    product = order.product
    delivered = None

    if product.type == "key":
        key = db.query(models.ProductKey).filter_by(product_id=product.id, is_used=False).first()
        if key:
            key.is_used = True
            key.order_id = order.id
            delivered = key.value
    elif product.type == "subscription":
        delivered = f"Подписка «{product.title}» активирована на {product.duration_days} дней"

    order.delivered_content = delivered
    db.commit()

    await notify_user_paid(order)
    return {"ok": True}