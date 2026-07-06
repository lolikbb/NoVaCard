import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from .database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    tg_id = Column(Integer, unique=True, index=True)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    orders = relationship("Order", back_populates="user")


class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True)
    title = Column(String)
    icon = Column(String, default="folder")  # ← добавлено поле icon
    sort_order = Column(Integer, default=0)
    products = relationship("Product", back_populates="category")


class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    category_id = Column(Integer, ForeignKey("categories.id"))
    title = Column(String)
    description = Column(Text, default="")
    price = Column(Float)
    asset = Column(String, default="USDT")
    type = Column(String, default="key")  # key | subscription
    duration_days = Column(Integer, nullable=True)
    icon = Column(String, default="package")  # ← добавлено поле icon (SVG иконка из Lucide)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    category = relationship("Category", back_populates="products")
    keys = relationship("ProductKey", back_populates="product")

    @property
    def stock(self):
        if self.type != "key":
            return None
        return len([k for k in self.keys if not k.is_used])


class ProductKey(Base):
    __tablename__ = "product_keys"
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    value = Column(Text)
    is_used = Column(Boolean, default=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    product = relationship("Product", back_populates="keys")


class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    amount = Column(Float)
    asset = Column(String)
    status = Column(String, default="pending")  # pending|paid|expired|failed
    invoice_id = Column(Integer, nullable=True)
    pay_url = Column(String, nullable=True)
    delivered_content = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    paid_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="orders")
    product = relationship("Product")