"""Middleware: пользователь из БД, последовательная обработка, защита от повторных callback."""
from __future__ import annotations

import asyncio
import logging
import time
import weakref
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, TelegramObject, User as TgUser

from config import Settings
from services.user_service import get_or_create_user

logger = logging.getLogger(__name__)

Handler = Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]]


class UserMiddleware(BaseMiddleware):
    """Загружает (или создаёт) пользователя и кладёт в data: user, lang, is_admin, settings."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def __call__(self, handler: Handler, event: TelegramObject, data: dict[str, Any]) -> Any:
        tg_user: TgUser | None = data.get("event_from_user")
        data["settings"] = self.settings
        if tg_user is None or tg_user.is_bot:
            return await handler(event, data)
        session = data["session"]
        user, created = await get_or_create_user(session, tg_user.id, tg_user.username, tg_user.full_name)
        if created:
            logger.info("New user registered: %s (@%s)", tg_user.id, tg_user.username)
        data["user"] = user
        data["user_created"] = created
        data["lang"] = user.language.value if hasattr(user.language, "value") else str(user.language)
        data["is_admin"] = self.settings.is_admin(tg_user.id)
        return await handler(event, data)


class UserLockMiddleware(BaseMiddleware):
    """Обновления одного пользователя обрабатываются по очереди — нет гонок при двойных нажатиях."""

    def __init__(self) -> None:
        self._locks: weakref.WeakValueDictionary[int, asyncio.Lock] = weakref.WeakValueDictionary()

    async def __call__(self, handler: Handler, event: TelegramObject, data: dict[str, Any]) -> Any:
        tg_user: TgUser | None = data.get("event_from_user")
        if tg_user is None:
            return await handler(event, data)
        lock = self._locks.get(tg_user.id)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[tg_user.id] = lock
        async with lock:
            return await handler(event, data)


class CallbackDebounceMiddleware(BaseMiddleware):
    """Игнорирует повторное нажатие той же кнопки в течение короткого окна."""

    def __init__(self, window: float = 1.5) -> None:
        self.window = window
        self._recent: dict[tuple[int, int, str], float] = {}

    async def __call__(self, handler: Handler, event: TelegramObject, data: dict[str, Any]) -> Any:
        if not isinstance(event, CallbackQuery):
            return await handler(event, data)
        message_id = event.message.message_id if event.message else 0
        key = (event.from_user.id, message_id, event.data or "")
        now = time.monotonic()
        self._cleanup(now)
        if now - self._recent.get(key, -1e9) < self.window:
            logger.info("Duplicate callback ignored: user=%s data=%s", key[0], key[2])
            await event.answer()
            return None
        self._recent[key] = now
        return await handler(event, data)

    def _cleanup(self, now: float) -> None:
        if len(self._recent) > 5000:
            self._recent = {k: v for k, v in self._recent.items() if now - v < self.window}
