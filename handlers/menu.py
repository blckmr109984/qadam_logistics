"""Главное меню: кнопки Reply-клавиатуры, /menu, /cancel, возврат «домой» из любого раздела.

Этот роутер подключается раньше роутеров со сценариями, поэтому кнопки меню
работают в любом состоянии FSM (например, посреди оформления заявки).
"""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User
from handlers.assistant import start_assistant
from handlers.calculator import start_calculator
from handlers.common import drop_inline_keyboard, send_main_menu, show
from handlers.history import show_my_shipments
from handlers.shipment import start_shipment
from handlers.tracking import start_tracking
from i18n import t
from keyboards.inline import MenuCB
from keyboards.main_menu import main_menu_keyboard
from services.ai_service import AssistantService
from utils.filters import MenuButton

router = Router(name="menu")


@router.message(Command("menu"))
@router.message(MenuButton("btn_home"))
async def cmd_menu(message: Message, state: FSMContext, lang: str) -> None:
    await state.clear()
    await send_main_menu(message, lang)


@router.message(Command("cancel"))
@router.message(MenuButton("btn_cancel"))
async def cmd_cancel(message: Message, state: FSMContext, lang: str) -> None:
    await state.clear()
    await send_main_menu(message, lang, t(lang, "action_cancelled"))


@router.callback_query(MenuCB.filter(F.action == "home"))
async def on_home(callback: CallbackQuery, state: FSMContext, lang: str) -> None:
    await state.clear()
    await callback.answer()
    await drop_inline_keyboard(callback)
    await send_main_menu(callback, lang)


@router.callback_query(MenuCB.filter(F.action == "cancel"))
async def on_cancel(callback: CallbackQuery, state: FSMContext, lang: str) -> None:
    await state.clear()
    await callback.answer()
    await show(callback, t(lang, "action_cancelled"))
    await send_main_menu(callback, lang)


@router.message(MenuButton("btn_create"))
async def menu_create(message: Message, state: FSMContext, session: AsyncSession, user: User, lang: str) -> None:
    await start_shipment(message, state, session, user, lang)


@router.message(MenuButton("btn_calc"))
async def menu_calc(message: Message, state: FSMContext, session: AsyncSession, lang: str) -> None:
    await start_calculator(message, state, session, lang)


@router.message(MenuButton("btn_track"))
async def menu_track(message: Message, state: FSMContext, lang: str) -> None:
    await start_tracking(message, state, lang)


@router.message(MenuButton("btn_my"))
async def menu_my(message: Message, state: FSMContext, session: AsyncSession, user: User, lang: str) -> None:
    await show_my_shipments(message, state, session, user, lang)


@router.message(MenuButton("btn_ai"))
async def menu_ai(message: Message, state: FSMContext, lang: str, assistant: AssistantService) -> None:
    await start_assistant(message, state, lang, assistant)


@router.message(MenuButton("btn_about"))
async def menu_about(message: Message, state: FSMContext, lang: str) -> None:
    await state.clear()
    await message.answer(t(lang, "about"), reply_markup=main_menu_keyboard(lang))
