"""Пользователи: регистрация, язык, телефон."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Language, User


async def get_or_create_user(
    session: AsyncSession,
    telegram_id: int,
    username: str | None = None,
    full_name: str | None = None,
) -> tuple[User, bool]:
    """Возвращает (пользователь, создан_ли_сейчас). Обновляет username/имя при изменении."""
    user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
    if user is None:
        user = User(telegram_id=telegram_id, username=username, full_name=(full_name or "")[:256])
        session.add(user)
        await session.commit()
        return user, True

    changed = False
    if username != user.username:
        user.username = username
        changed = True
    if full_name and full_name[:256] != user.full_name:
        user.full_name = full_name[:256]
        changed = True
    if changed:
        await session.commit()
    return user, False


async def set_language(session: AsyncSession, user: User, language: str) -> User:
    user.language = Language(language)
    await session.commit()
    return user


async def set_phone(session: AsyncSession, user: User, phone: str) -> User:
    user.phone = phone
    await session.commit()
    return user


async def count_users(session: AsyncSession) -> int:
    return int(await session.scalar(select(func.count()).select_from(User)) or 0)


async def list_users(session: AsyncSession, limit: int = 10, offset: int = 0) -> list[User]:
    rows = await session.scalars(select(User).order_by(User.created_at.desc(), User.id.desc()).limit(limit).offset(offset))
    return list(rows)
