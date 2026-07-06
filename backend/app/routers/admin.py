from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..auth import get_admin_user
from .. import models, schemas

router = APIRouter()


@router.get("/admin/stats")
def stats(db: Session = Depends(get_db), admin=Depends(get_admin_user)):
    total_orders = db.query(models.Order).count()
    paid_orders = db.query(models.Order).filter_by(status="paid").all()
    revenue = sum(o.amount for o in paid_orders)
    total_users = db.query(models.User).count()
    total_products = db.query(models.Product).count()
    return {
        "revenue": round(revenue, 2),
        "paid_orders": len(paid_orders),
        "total_orders": total_orders,
        "total_users": total_users,
        "total_products": total_products,
    }


@router.get("/admin/orders", response_model=list[schemas.OrderOut])
def all_orders(db: Session = Depends(get_db), admin=Depends(get_admin_user)):
    return db.query(models.Order).order_by(models.Order.created_at.desc()).limit(300).all()


@router.get("/admin/products", response_model=list[schemas.ProductOut])
def admin_products(db: Session = Depends(get_db), admin=Depends(get_admin_user)):
    return db.query(models.Product).all()


@router.post("/admin/products", response_model=schemas.ProductOut)
def create_product(payload: schemas.ProductCreate, db: Session = Depends(get_db), admin=Depends(get_admin_user)):
    product = models.Product(**payload.dict())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.put("/admin/products/{product_id}", response_model=schemas.ProductOut)
def update_product(product_id: int, payload: schemas.ProductCreate, db: Session = Depends(get_db), admin=Depends(get_admin_user)):
    product = db.query(models.Product).get(product_id)
    if not product:
        raise HTTPException(404, "Не найдено")
    for k, v in payload.dict().items():
        setattr(product, k, v)
    db.commit()
    db.refresh(product)
    return product


@router.delete("/admin/products/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db), admin=Depends(get_admin_user)):
    product = db.query(models.Product).get(product_id)
    if product:
        db.delete(product)
        db.commit()
    return {"ok": True}


@router.post("/admin/products/{product_id}/keys")
def add_keys(product_id: int, payload: schemas.KeysAdd, db: Session = Depends(get_db), admin=Depends(get_admin_user)):
    for val in payload.keys:
        if val.strip():
            db.add(models.ProductKey(product_id=product_id, value=val.strip()))
    db.commit()
    return {"ok": True}


@router.get("/admin/categories", response_model=list[schemas.CategoryOut])
def admin_categories(db: Session = Depends(get_db), admin=Depends(get_admin_user)):
    return db.query(models.Category).all()


@router.post("/admin/categories", response_model=schemas.CategoryOut)
def create_category(payload: schemas.CategoryCreate, db: Session = Depends(get_db), admin=Depends(get_admin_user)):
    cat = models.Category(**payload.dict())
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


@router.delete("/admin/categories/{category_id}")
def delete_category(category_id: int, db: Session = Depends(get_db), admin=Depends(get_admin_user)):
    cat = db.query(models.Category).get(category_id)
    if cat:
        db.delete(cat)
        db.commit()
    return {"ok": True}