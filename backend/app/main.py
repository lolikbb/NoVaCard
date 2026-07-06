from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, engine
from .routers import products, orders, admin, webhook
from .auth import get_current_user

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Crypto Digital Shop API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(products.router, prefix="/api")
app.include_router(orders.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(webhook.router, prefix="/api")


@app.get("/api/me")
def me(user=Depends(get_current_user)):
    return {
        "id": user.id,
        "tg_id": user.tg_id,
        "username": user.username,
        "first_name": user.first_name,
        "is_admin": user.is_admin,
    }


@app.get("/")
def root():
    return {"status": "ok"}