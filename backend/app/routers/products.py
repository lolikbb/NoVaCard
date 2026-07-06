from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..auth import get_current_user
from .. import models, schemas

router = APIRouter()


@router.get("/categories", response_model=list[schemas.CategoryOut])
def list_categories(db: Session = Depends(get_db), user=Depends(get_current_user)):
    return db.query(models.Category).order_by(models.Category.sort_order).all()


@router.get("/products", response_model=list[schemas.ProductOut])
def list_products(category_id: Optional[int] = None, db: Session = Depends(get_db), user=Depends(get_current_user)):
    q = db.query(models.Product).filter_by(is_active=True)
    if category_id:
        q = q.filter_by(category_id=category_id)
    return q.all()


@router.get("/products/{product_id}", response_model=schemas.ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    p = db.query(models.Product).get(product_id)
    if not p:
        raise HTTPException(404, "Не найдено")
    return p