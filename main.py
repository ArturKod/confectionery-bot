import asyncio
import logging

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

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        f"Привет, {message.from_user.full_name}! 👋\n"
        "Я бот кондитерской. Скоро здесь можно будет заказать торт!"
    )

async def main():
    print("Бот запускается...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())