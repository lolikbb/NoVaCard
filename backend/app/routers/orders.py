from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..auth import get_current_user
from .. import models, schemas
from ..cryptobot import create_invoice, get_invoice
from ..config import WEBAPP_URL

router = APIRouter()


@router.post("/orders", response_model=schemas.OrderOut)
async def create_order(payload: schemas.OrderCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    product = db.query(models.Product).get(payload.product_id)
    if not product or not product.is_active:
        raise HTTPException(404, "Товар не найден")
    if product.type == "key" and product.stock <= 0:
        raise HTTPException(400, "Товар закончился, зайдите позже")

    order = models.Order(user_id=user.id, product_id=product.id, amount=product.price, asset=product.asset)
    db.add(order)
    db.commit()
    db.refresh(order)

    invoice = await create_invoice(
        amount=product.price,
        asset=product.asset,
        description=product.title,
        payload=str(order.id),
        paid_btn_url=WEBAPP_URL,
    )
    order.invoice_id = invoice["invoice_id"]
    order.pay_url = invoice["pay_url"]
    db.commit()
    db.refresh(order)
    return order


@router.get("/orders", response_model=list[schemas.OrderOut])
def my_orders(db: Session = Depends(get_db), user=Depends(get_current_user)):
    return (
        db.query(models.Order)
        .filter_by(user_id=user.id)
        .order_by(models.Order.created_at.desc())
        .all()
    )


@router.get("/orders/{order_id}", response_model=schemas.OrderOut)
async def get_order(order_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    order = db.query(models.Order).filter_by(id=order_id, user_id=user.id).first()
    if not order:
        raise HTTPException(404, "Не найдено")
    return order