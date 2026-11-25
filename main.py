import asyncio
import logging
from bot.database import async_session
from bot.middlewares.db import DbSessionMiddleware
from bot.repositories.user import UserRepository

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.storage.redis import RedisStorage, DefaultKeyBuilder

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    BOT_TOKEN: str
    REDIS_URL: str = "redis://localhost:6379/0"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()

logging.basicConfig(level=logging.INFO)

storage = RedisStorage.from_url(
    settings.REDIS_URL,
    key_builder=DefaultKeyBuilder(with_bot_id=True),
    state_ttl=60 * 60 * 24,  # Состояния живут 1 день
    data_ttl=60 * 60 * 24,
)

bot = Bot(token=settings.BOT_TOKEN)
dp = Dispatcher(storage=storage)

# Регистрируем middleware для базы данных
dp.update.middleware(DbSessionMiddleware(session_pool=async_session))

@dp.message(Command("start"))
async def cmd_start(message: Message, session): # session добавляется автоматически из middleware
    tg_id = message.from_user.id
    full_name = message.from_user.full_name
    
    # Проверяем, есть ли пользователь в базе
    user = await UserRepository.get_by_tg_id(session, tg_id)
    
    if not user:
        # Если нет — создаем
        await UserRepository.create(session, tg_id, full_name)
        await message.answer(f"Привет, {full_name}! 👋\nЯ вас зарегистрировал в системе кондитерской.")
    else:
        await message.answer(f"С возвращением, {full_name}! 👋\nРад видеть вас снова.")

async def main():
    print("Бот запускается...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())