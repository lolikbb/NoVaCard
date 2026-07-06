import datetime
from typing import Optional, List
from pydantic import BaseModel


class CategoryOut(BaseModel):
    id: int
    title: str
    icon: str  # ← добавлено
    class Config: from_attributes = True


class CategoryCreate(BaseModel):
    title: str
    icon: str = "folder"  # ← добавлено
    sort_order: int = 0


class ProductOut(BaseModel):
    id: int
    category_id: int
    title: str
    description: str
    price: float
    asset: str
    type: str
    duration_days: Optional[int] = None
    icon: str  # ← добавлено
    is_active: bool
    stock: Optional[int] = None
    class Config: from_attributes = True


class ProductCreate(BaseModel):
    category_id: int
    title: str
    description: str = ""
    price: float
    asset: str = "USDT"
    type: str = "key"
    duration_days: Optional[int] = None
    icon: str = "package"  # ← добавлено
    is_active: bool = True


class OrderCreate(BaseModel):
    product_id: int


class OrderOut(BaseModel):
    id: int
    product_id: int
    amount: float
    asset: str
    status: str
    pay_url: Optional[str] = None
    delivered_content: Optional[str] = None
    created_at: datetime.datetime
    class Config: from_attributes = True


class KeysAdd(BaseModel):
    keys: List[str]