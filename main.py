import asyncio
import logging

from aiogram import Bot, Dispatcher, F  # <-- Добавлен F
from aiogram.filters import Command, or_f
from aiogram.types import Message
from aiogram.fsm.storage.redis import RedisStorage, DefaultKeyBuilder

# --- Импорты проекта ---
from bot.config import settings
from bot.database import async_session
from bot.middlewares.db import DbSessionMiddleware
from bot.repositories.user import UserRepository
from bot.repositories.product import ProductRepository
from bot.keyboards.inline import get_product_keyboard
from bot.keyboards.reply import get_main_menu  # <-- Импорт нижнего меню
from bot.handlers import order as order_handlers
from bot.handlers import client_orders, admin

# 1. Логирование
logging.basicConfig(level=logging.INFO)

# 2. Хранилище Redis
storage = RedisStorage.from_url(
    settings.REDIS_URL,
    key_builder=DefaultKeyBuilder(with_bot_id=True),
    state_ttl=60 * 60 * 24,
    data_ttl=60 * 60 * 24,
)

# 3. Бот и Диспетчер
bot = Bot(token=settings.BOT_TOKEN)
dp = Dispatcher(storage=storage)

# 4. Подключение Middleware и Роутеров
dp.update.middleware(DbSessionMiddleware(session_pool=async_session))
dp.include_router(order_handlers.router)
dp.include_router(client_orders.router)
dp.include_router(admin.router)

# 5. Базовые команды
@dp.message(Command("start"))
async def cmd_start(message: Message, session):
    tg_id = message.from_user.id
    full_name = message.from_user.full_name
    
    # Проверяем, админ ли это для отображения нужного меню
    is_admin = (tg_id == settings.ADMIN_ID)
    
    user = await UserRepository.get_by_tg_id(session, tg_id)
    if not user:
        await UserRepository.create(session, tg_id, full_name)
        await message.answer(
            f"Привет, {full_name}! 👋\nЯ вас зарегистрировал. Добро пожаловать!",
            reply_markup=get_main_menu(is_admin)
        )
    else:
        await message.answer(
            f"С возвращением, {full_name}! 👋",
            reply_markup=get_main_menu(is_admin)
        )

@dp.message(or_f(Command("catalog"), F.text == "🎂 Каталог"))
async def cmd_catalog(message: Message, session):
    products = await ProductRepository.get_all_active(session)
    if not products:
        await message.answer("К сожалению, каталог пока пуст.")
        return

    await message.answer("Вот что у нас есть в наличии:")
    
    # Проверяем, кто запрашивает каталог
    is_admin = (message.from_user.id == settings.ADMIN_ID)
    
    for product in products:
        price_formatted = int(product.price) if product.price % 1 == 0 else product.price
        text = (
            f"*{product.name}*\n\n"
            f"{product.description}\n\n"
            f"💰 Цена: {price_formatted} руб.\n"
            f"⚖️ Вес: {product.weight_grams} г."
        )
        try:
            await message.answer_photo(
                photo=product.image_url,
                caption=text,
                parse_mode="Markdown",
                # Передаем is_admin в клавиатуру
                reply_markup=get_product_keyboard(product.id, is_admin) 
            )
        except Exception as e:
            print(f"Ошибка при отправке фото: {e}")
            await message.answer(text, parse_mode="Markdown")
            
# 6. Точка входа
async def main():
    print("Бот запускается...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())