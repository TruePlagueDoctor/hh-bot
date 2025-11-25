import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from dotenv import load_dotenv

# --- Настройка путей, чтобы можно было импортировать app.* ---
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(BASE_DIR)

# --- Загружаем .env ---
load_dotenv()

# --- Alembic config ---
config = context.config

# Интерпретация логгера из файла alembic.ini.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# --- Импортируем metadata из нашего проекта ---
from app.db.models import Base  # noqa: E402

target_metadata = Base.metadata

# --- URL базы из .env ---
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL is None:
    raise RuntimeError("DATABASE_URL is not set in .env")

# Alembic обычно работает с синхронным драйвером, поэтому убираем +asyncpg
SYNC_DATABASE_URL = DATABASE_URL.replace("+asyncpg", "")


def run_migrations_offline() -> None:
    """Запуск миграций в оффлайн-режиме (генерация SQL без подключения к БД)."""
    context.configure(
        url=SYNC_DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Запуск миграций в онлайне (прямое применение к БД)."""
    config_section = config.get_section(config.config_ini_section)
    if config_section is None:
        raise RuntimeError("Config section is None")

    config_section["sqlalchemy.url"] = SYNC_DATABASE_URL

    connectable = engine_from_config(
        config_section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
