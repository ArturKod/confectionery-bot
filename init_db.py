import asyncio
from bot.database import engine
from bot.models.models import Base

async def init_db():
    print("Создаем таблицы в базе данных...")
    async with engine.begin() as conn:
        # Создаем все таблицы, которые описаны в моделях
        await conn.run_sync(Base.metadata.create_all)
    print("Таблицы успешно созданы!")

if __name__ == "__main__":
    asyncio.run(init_db())