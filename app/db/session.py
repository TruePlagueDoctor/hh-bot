from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

_engine = None
_async_session_maker: async_sessionmaker[AsyncSession] | None = None


async def init_db(database_url: str):
    """Создаёт engine и фабрику сессий. Вызывается один раз при старте."""
    global _engine, _async_session_maker
    # Для asyncpg URL должен быть вида: postgres+asyncpg://user:pass@host/dbname
    _engine = create_async_engine(database_url, echo=False, future=True)
    _async_session_maker = async_sessionmaker(
        _engine, expire_on_commit=False, class_=AsyncSession
    )


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency-фабрика для сессий (можно использовать в сервисах/хендлерах)."""
    if _async_session_maker is None:
        raise RuntimeError("DB is not initialized. Call init_db() first.")
    async with _async_session_maker() as session:
        yield session
