"""Главное меню (Reply-клавиатура) и выбор языка."""
from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from i18n import LANGUAGES, t
from keyboards.inline import LangCB

MENU_KEYS = ("btn_create", "btn_calc", "btn_track", "btn_my", "btn_ai", "btn_about")


def main_menu_keyboard(lang: str) -> ReplyKeyboardMarkup:
    b = {key: KeyboardButton(text=t(lang, key)) for key in MENU_KEYS}
    return ReplyKeyboardMarkup(
        keyboard=[
            [b["btn_create"]],
            [b["btn_calc"], b["btn_track"]],
            [b["btn_my"], b["btn_ai"]],
            [b["btn_about"]],
        ],
        resize_keyboard=True,
        input_field_placeholder=t(lang, "input_placeholder"),
    )


def language_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for code, title in LANGUAGES.items():
        builder.button(text=title, callback_data=LangCB(code=code))
    builder.adjust(3)
    return builder.as_markup()
