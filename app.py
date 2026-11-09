"""Сборка приложения: диспетчер, middleware, роутеры, обработчик ошибок.

Вынесено из bot.py, чтобы тот же диспетчер можно было собрать в тестах.
"""
from __future__ import annotations

import logging

from aiogram import Dispatcher
from aiogram.fsm.storage.base import BaseStorage
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import CallbackQuery, ErrorEvent, Message
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from config import Settings
from database.session import DbSessionMiddleware
from handlers import get_routers
from i18n import t
from middlewares import CallbackDebounceMiddleware, UserLockMiddleware, UserMiddleware
from services.ai_service import AssistantService, GeminiClient

logger = logging.getLogger(__name__)


def build_assistant(settings: Settings) -> AssistantService:
    if settings.ai_enabled:
        logger.info("AI assistant: Gemini (%s)", settings.gemini_model)
        return AssistantService(GeminiClient(settings.gemini_api_key, settings.gemini_model, settings.gemini_timeout))
    logger.info("AI assistant: GEMINI_API_KEY not set — fallback mode without AI")
    return AssistantService(None)


def create_dispatcher(
    settings: Settings,
    session_maker: async_sessionmaker[AsyncSession],
    assistant: AssistantService | None = None,
    storage: BaseStorage | None = None,
    debounce_window: float = 1.5,
) -> Dispatcher:
    dp = Dispatcher(storage=storage or MemoryStorage())
    dp["assistant"] = assistant or build_assistant(settings)

    # Порядок: блокировка пользователя → сессия БД → загрузка пользователя
    dp.update.outer_middleware(UserLockMiddleware())
    dp.update.outer_middleware(DbSessionMiddleware(session_maker))
    dp.update.outer_middleware(UserMiddleware(settings))
    dp.callback_query.outer_middleware(CallbackDebounceMiddleware(debounce_window))

    dp.include_routers(*get_routers())

    @dp.errors()
    async def on_error(event: ErrorEvent) -> bool:
        logger.exception("Unhandled error in update %s", event.update.update_id, exc_info=event.exception)
        target: Message | CallbackQuery | None = event.update.message or event.update.callback_query
        try:
            if isinstance(target, CallbackQuery):
                await target.answer(t("ru", "error_generic")[:190], show_alert=True)
            elif isinstance(target, Message):
                await target.answer(t("ru", "error_generic"))
        except Exception:  # noqa: BLE001
            logger.debug("Could not notify user about error")
        return True

    return dp
