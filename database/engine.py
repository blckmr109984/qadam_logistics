"""Создание асинхронного движка и фабрики сессий."""
from __future__ import annotations

import logging

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from database.models import Base

logger = logging.getLogger(__name__)


def create_engine(database_url: str, echo: bool = False) -> AsyncEngine:
    engine = create_async_engine(database_url, echo=echo, pool_pre_ping=True)

    if engine.dialect.name == "sqlite":
        # В SQLite внешние ключи по умолчанию выключены — включаем для каждого соединения.
        @event.listens_for(engine.sync_engine, "connect")
        def _sqlite_pragmas(dbapi_connection, _record):  # pragma: no cover - инфраструктура
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def create_session_maker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


async def init_models(engine: AsyncEngine) -> None:
    """Создаёт таблицы, если их нет (режим быстрого локального запуска MVP)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database schema is ready")
