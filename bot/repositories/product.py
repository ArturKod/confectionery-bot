from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from bot.models.models import Product

class ProductRepository:
    @staticmethod
    async def get_all_active(session: AsyncSession) -> List[Product]:
        """Возвращает все активные товары из каталога."""
        result = await session.execute(
            select(Product).where(Product.is_active == True)
        )
        return list(result.scalars().all())