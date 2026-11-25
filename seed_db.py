import asyncio
from decimal import Decimal
from bot.database import async_session
from bot.models.models import Product

async def seed_products():
    async with async_session() as session:
        # Проверяем, есть ли уже товары
        from sqlalchemy import select
        result = await session.execute(select(Product))
        if result.scalars().first():
            print("Товары уже есть в базе. Пропускаем.")
            return

        print("Добавляем тестовые товары...")
        products = [
            Product(
                name="Торт «Наполеон»",
                description="Классический слоеный торт с заварным кремом.",
                price=Decimal("2500.00"),
                weight_grams=1200,
                image_url="https://images.unsplash.com/photo-1578985545062-69928b1d9587?q=80&w=600&auto=format&fit=crop"
            ),
            Product(
                name="Чизкейк «Нью-Йорк»",
                description="Нежный сливочный сыр, песочная основа, ягодный соус.",
                price=Decimal("1800.00"),
                weight_grams=900,
                image_url="https://images.unsplash.com/photo-1533134242443-d4fd215305ad?q=80&w=600&auto=format&fit=crop"
            ),
            Product(
                name="Круассан с миндалем",
                description="Свежая французская выпечка. Идеально к утреннему кофе.",
                price=Decimal("250.00"),
                weight_grams=150,
                image_url="https://images.unsplash.com/photo-1555507036-ab1f4038808a?q=80&w=600&auto=format&fit=crop"
            )
        ]
        session.add_all(products)
        await session.commit()
        print("Товары успешно добавлены!")

if __name__ == "__main__":
    asyncio.run(seed_products())