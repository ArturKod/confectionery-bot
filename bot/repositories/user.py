from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from bot.models.models import User

class UserRepository:
    @staticmethod
    async def get_by_tg_id(session: AsyncSession, tg_id: int) -> Optional[User]:
        """Ищет пользователя в БД по его Telegram ID."""
        result = await session.execute(select(User).where(User.tg_id == tg_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def create(session: AsyncSession, tg_id: int, full_name: str) -> User:
        """Создает нового пользователя в БД."""
        new_user = User(tg_id=tg_id, full_name=full_name)
        session.add(new_user)
        await session.commit()
        await session.refresh(new_user)
        return new_user