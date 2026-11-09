"""Общие помощники для хендлеров."""
from __future__ import annotations

import logging

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message, ReplyKeyboardMarkup, ReplyKeyboardRemove

from i18n import t
from keyboards.main_menu import main_menu_keyboard

logger = logging.getLogger(__name__)

Markup = InlineKeyboardMarkup | ReplyKeyboardMarkup | ReplyKeyboardRemove | None


async def show(target: Message | CallbackQuery, text: str, markup: Markup = None, *, edit: bool = True) -> Message | None:
    """Показывает экран: на callback — редактирует сообщение с кнопкой, иначе отправляет новое.

    Reply-клавиатуру нельзя прикрепить при редактировании, поэтому в этом случае
    всегда отправляется новое сообщение.
    """
    if isinstance(target, CallbackQuery):
        message = target.message
        can_edit = edit and isinstance(message, Message) and not isinstance(markup, (ReplyKeyboardMarkup, ReplyKeyboardRemove))
        if can_edit:
            try:
                await message.edit_text(text, reply_markup=markup)
                return message
            except TelegramBadRequest as exc:
                if "message is not modified" in str(exc):
                    return message
                logger.debug("Edit failed, sending new message: %s", exc)
        if isinstance(message, Message):
            return await message.answer(text, reply_markup=markup)
        return await target.bot.send_message(target.from_user.id, text, reply_markup=markup)
    return await target.answer(text, reply_markup=markup)


async def send_main_menu(target: Message | CallbackQuery, lang: str, text: str | None = None) -> None:
    message = target.message if isinstance(target, CallbackQuery) else target
    body = text or t(lang, "main_menu")
    if isinstance(message, Message):
        await message.answer(body, reply_markup=main_menu_keyboard(lang))
    else:
        await target.bot.send_message(target.from_user.id, body, reply_markup=main_menu_keyboard(lang))


async def drop_inline_keyboard(callback: CallbackQuery) -> None:
    if isinstance(callback.message, Message) and callback.message.reply_markup:
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except TelegramBadRequest:
            pass
