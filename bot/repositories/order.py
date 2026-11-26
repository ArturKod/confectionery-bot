from datetime import datetime
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from bot.models.models import Order, OrderItem, Product, OrderStatus, User

class OrderRepository:
    @staticmethod
    async def create_order(
        session: AsyncSession, 
        user: User, 
        product: Product, 
        phone: str, 
        desired_date: datetime
    ) -> Order:
        
        # Обновляем телефон пользователя, если он изменился или отсутствует
        if user.phone != phone:
            user.phone = phone
            session.add(user)

        # 1. Создаем сам заказ
        order = Order(
            user_id=user.id,
            status=OrderStatus.NEW,
            delivery_type="pickup",
            desired_date=desired_date,
            total_price=product.price
        )
        session.add(order)
        await session.flush() # Получаем order.id до коммита

        # 2. Добавляем позицию в заказ
        order_item = OrderItem(
            order_id=order.id,
            product_id=product.id,
            quantity=1,
            price_at_order=product.price
        )
        session.add(order_item)
        await session.commit()
        
        # Загружаем заказ со всеми связями для дальнейшей работы
        return await OrderRepository.get_by_id(session, order.id)

    @staticmethod
    async def get_user_orders(session: AsyncSession, user_id: int) -> List[Order]:
        """Возвращает все активные заказы пользователя."""
        result = await session.execute(
            select(Order)
            .options(selectinload(Order.items).selectinload(OrderItem.product))
            .where(Order.user_id == user_id, Order.status != OrderStatus.CANCELLED)
            .order_by(Order.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_by_id(session: AsyncSession, order_id: int) -> Optional[Order]:
        """Находит заказ по ID со всеми связями (клиент, товары)."""
        result = await session.execute(
            select(Order)
            .options(
                selectinload(Order.user),
                selectinload(Order.items).selectinload(OrderItem.product)
            )
            .where(Order.id == order_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def update_status(session: AsyncSession, order: Order, new_status: OrderStatus) -> None:
        """Меняет статус заказа."""
        order.status = new_status
        await session.commit()

    @staticmethod
    async def get_all_active_orders(session: AsyncSession) -> List[Order]:
        """Возвращает все заказы, которые еще в работе."""
        active_statuses = [
            OrderStatus.NEW, OrderStatus.AGREED, OrderStatus.WAITING_FOR_PAYMENT,
            OrderStatus.PAID, OrderStatus.COOKING, OrderStatus.READY
        ]
        result = await session.execute(
            select(Order)
            .options(
                selectinload(Order.user),
                selectinload(Order.items).selectinload(OrderItem.product)
            )
            .where(Order.status.in_(active_statuses))
            .order_by(Order.created_at.asc())
        )
        return list(result.scalars().all())