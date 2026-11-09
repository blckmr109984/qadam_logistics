"""Безопасная отправка уведомлений: ошибки Telegram логируются и не роняют бота."""
from __future__ import annotations

import logging
from collections.abc import Iterable

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramForbiddenError
from aiogram.types import InlineKeyboardMarkup

logger = logging.getLogger(__name__)


async def safe_send(
    bot: Bot,
    chat_id: int,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> bool:
    try:
        await bot.send_message(chat_id, text, reply_markup=reply_markup)
        return True
    except TelegramForbiddenError:
        logger.warning("User %s blocked the bot — notification skipped", chat_id)
    except TelegramAPIError as exc:
        logger.error("Failed to send notification to %s: %s", chat_id, exc)
    return False


async def notify_admins(
    bot: Bot,
    admin_ids: Iterable[int],
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> int:
    delivered = 0
    for admin_id in admin_ids:
        if await safe_send(bot, admin_id, text, reply_markup):
            delivered += 1
    return delivered
