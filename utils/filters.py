"""Фильтры aiogram."""
from __future__ import annotations

from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message

from config import Settings, get_settings
from i18n import all_translations


class AdminFilter(BaseFilter):
    """Пропускает только Telegram ID из ADMIN_IDS."""

    async def __call__(self, event: Message | CallbackQuery, settings: Settings | None = None) -> bool:
        settings = settings or get_settings()
        user = event.from_user
        return user is not None and settings.is_admin(user.id)


class MenuButton(BaseFilter):
    """Совпадение текста с кнопкой меню на любом из языков."""

    def __init__(self, key: str) -> None:
        self.key = key
        self.variants = all_translations(key)

    async def __call__(self, message: Message) -> bool:
        return bool(message.text) and message.text.strip() in self.variants


def is_menu_text(text: str | None) -> bool:
    from keyboards.main_menu import MENU_KEYS

    if not text:
        return False
    return any(text.strip() in all_translations(key) for key in (*MENU_KEYS, "btn_cancel", "btn_home"))
