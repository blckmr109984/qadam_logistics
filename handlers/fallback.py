"""Последний роутер: всё, что не обработали остальные."""
from __future__ import annotations

import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from handlers.common import send_main_menu
from i18n import t
from keyboards.admin import AdminCB

logger = logging.getLogger(__name__)
router = Router(name="fallback")


@router.message(Command("admin"))
async def admin_denied(message: Message, lang: str) -> None:
    logger.warning("Non-admin %s tried to open admin panel", message.from_user.id)
    await message.answer(t(lang, "access_denied"))


@router.callback_query(AdminCB.filter())
async def admin_callback_denied(callback: CallbackQuery, lang: str) -> None:
    logger.warning("Non-admin %s pressed admin button %s", callback.from_user.id, callback.data)
    await callback.answer(t(lang, "access_denied"), show_alert=True)


@router.callback_query()
async def unknown_callback(callback: CallbackQuery, lang: str) -> None:
    await callback.answer(t(lang, "callback_expired"))


@router.message()
async def unknown_message(message: Message, lang: str) -> None:
    await send_main_menu(message, lang, t(lang, "unknown"))
