import enum
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import BigInteger, String, Text, ForeignKey, Numeric, DateTime, Enum, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Базовый класс для всех моделей."""
    pass


class OrderStatus(str, enum.Enum):
    NEW = "Новый"                 # Только создан
    AGREED = "Согласован"         # Цена и детали утверждены
    WAITING_FOR_PAYMENT = "Ждет оплаты" # Реквизиты отправлены
    COOKING = "Готовится"         # Оплата подтверждена
    READY = "Готов"               # Можно забирать
    COMPLETED = "Завершен"        # Выдан
    CANCELLED = "Отменен"         # Отменен
    PAID = "Оплачен (проверка)" 
    
class User(Base):
    """Пользователь (клиент) бота."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Telegram ID может быть очень большим, поэтому используем BigInteger
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    phone: Mapped[Optional[str]] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Связь с заказами (у одного пользователя много заказов)
    orders: Mapped[List["Order"]] = relationship(back_populates="user")


class Product(Base):
    """Товар в каталоге (торт, пирожное и т.д.)."""
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))  # 10 цифр, 2 после запятой
    weight_grams: Mapped[Optional[int]] = mapped_column()
    image_url: Mapped[Optional[str]] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(default=True)  # Можно скрывать товары без удаления


class Order(Base):
    """Заказ клиента."""
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus), default=OrderStatus.NEW)
    
    # Данные по доставке/самовывозу
    delivery_type: Mapped[str] = mapped_column(String(50)) # "pickup" или "delivery"
    address: Mapped[Optional[str]] = mapped_column(Text)
    desired_date: Mapped[Optional[datetime]] = mapped_column(DateTime) # Когда нужен заказ
    comment: Mapped[Optional[str]] = mapped_column(Text)
    
    total_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Связи
    user: Mapped["User"] = relationship(back_populates="orders")
    items: Mapped[List["OrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    """Позиция внутри заказа (какой товар и в каком количестве)."""
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    quantity: Mapped[int] = mapped_column(default=1)
    
    # ВАЖНО: фиксируем цену на момент заказа, чтобы если товар подорожает, 
    # история старых заказов не изменилась
    price_at_order: Mapped[Decimal] = mapped_column(Numeric(10, 2))

    # Связи
    order: Mapped["Order"] = relationship(back_populates="items")
    product: Mapped["Product"] = relationship()