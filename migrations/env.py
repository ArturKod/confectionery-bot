import os
import sys
from logging.config import fileConfig
from alembic import context
from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool

# 1. Вычисляем абсолютный путь к корню проекта
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(base_dir)

from bot.models.models import Base

# 2. Принудительно загружаем .env из корня и перезаписываем системные переменные
env_path = os.path.join(base_dir, '.env')
load_dotenv(dotenv_path=env_path, override=True)

config = context.config

# 3. Берем URL и меняем драйвер (psycopg2 для миграций)
database_url = os.getenv("DATABASE_URL")
if database_url:
    database_url = database_url.strip()
    if "postgresql+asyncpg://" in database_url:
        database_url = database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")

print("ALEMBIC ПОДКЛЮЧАЕТСЯ СЮДА:", database_url)

config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata
print("ВНУТРИ ALEMBIC НАЙДЕНЫ ТАБЛИЦЫ:", list(target_metadata.tables.keys()))