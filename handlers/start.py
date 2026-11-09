"""/start, выбор языка, /help."""
from __future__ import annotations

from html import escape

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User
from handlers.common import send_main_menu
from i18n import LANGUAGES, t
from keyboards.inline import LangCB, home_keyboard
from keyboards.main_menu import language_keyboard, main_menu_keyboard
from services import user_service

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, lang: str) -> None:
    await state.clear()
    name = escape(message.from_user.first_name or message.from_user.full_name or "")
    await message.answer(t(lang, "welcome", name=name), reply_markup=main_menu_keyboard(lang))
    await message.answer(t(lang, "choose_language"), reply_markup=language_keyboard())


@router.message(Command("language"))
async def cmd_language(message: Message) -> None:
    await message.answer(t("ru", "choose_language"), reply_markup=language_keyboard())


@router.message(Command("help"))
async def cmd_help(message: Message, lang: str) -> None:
    await message.answer(t(lang, "help"), reply_markup=home_keyboard(lang))


@router.callback_query(LangCB.filter())
async def on_language(callback: CallbackQuery, callback_data: LangCB, session: AsyncSession, user: User) -> None:
    if callback_data.code not in LANGUAGES:
        await callback.answer()
        return
    await user_service.set_language(session, user, callback_data.code)
    lang = callback_data.code
    await callback.answer(t(lang, "language_saved"))
    if callback.message:
        await callback.message.edit_text(t(lang, "language_saved"))
    await send_main_menu(callback, lang)
