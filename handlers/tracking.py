"""Отслеживание: поиск по номеру, карточка с временной шкалой, история, отмена клиентом."""
from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from config import Settings
from database.models import User
from handlers.common import show
from i18n import t
from keyboards.inline import ShipmentCB, home_keyboard
from keyboards.shipment import cancel_confirm_keyboard, history_keyboard, shipment_card_keyboard
from services import shipment_service, tracking_service
from states.shipment_states import TrackingForm
from utils.filters import is_menu_text
from utils.formatting import admin_shipment_text, history_text, shipment_card
from utils.notifications import notify_admins
from utils.tracking_id import is_valid_tracking_number, normalize_tracking_number

logger = logging.getLogger(__name__)
router = Router(name="tracking")


async def start_tracking(target: Message | CallbackQuery, state: FSMContext, lang: str) -> None:
    await state.clear()
    await state.set_state(TrackingForm.number)
    await show(target, t(lang, "ask_tracking"), home_keyboard(lang))


async def _lookup_and_show(message: Message, state: FSMContext, session: AsyncSession, user: User,
                           lang: str, is_admin: bool, raw: str) -> None:
    number = normalize_tracking_number(raw)
    if not is_valid_tracking_number(number):
        await message.answer(t(lang, "tracking_invalid"), reply_markup=home_keyboard(lang))
        return
    try:
        shipment = await shipment_service.get_shipment_for_user(
            session, user, tracking_number=number, is_admin=is_admin
        )
    except (shipment_service.ShipmentNotFoundError, shipment_service.AccessDeniedError):
        # Одинаковый ответ для «нет такой» и «чужая» — не раскрываем существование чужих поставок.
        logger.info("Tracking lookup failed: user=%s number=%s", user.telegram_id, number)
        await message.answer(t(lang, "tracking_not_found", tracking=number), reply_markup=home_keyboard(lang))
        return
    await state.clear()
    await message.answer(shipment_card(shipment, lang), reply_markup=shipment_card_keyboard(shipment, lang))


@router.message(Command("track"))
async def cmd_track(message: Message, command: CommandObject, state: FSMContext, session: AsyncSession,
                    user: User, lang: str, is_admin: bool) -> None:
    if command.args:
        await _lookup_and_show(message, state, session, user, lang, is_admin, command.args)
    else:
        await start_tracking(message, state, lang)


@router.message(TrackingForm.number, F.text)
async def on_tracking_number(message: Message, state: FSMContext, session: AsyncSession, user: User,
                             lang: str, is_admin: bool) -> None:
    if is_menu_text(message.text):  # страховка: кнопки меню обрабатываются раньше
        return
    await _lookup_and_show(message, state, session, user, lang, is_admin, message.text)


async def _get_own(callback: CallbackQuery, session: AsyncSession, user: User, lang: str, shipment_id: int,
                   is_admin: bool = False):
    try:
        return await shipment_service.get_shipment_for_user(session, user, shipment_id=shipment_id, is_admin=is_admin)
    except shipment_service.AccessDeniedError:
        logger.warning("User %s tried to open foreign shipment %s", user.telegram_id, shipment_id)
        await callback.answer(t(lang, "access_denied"), show_alert=True)
    except shipment_service.ShipmentNotFoundError:
        await callback.answer(t(lang, "callback_expired"), show_alert=True)
    return None


@router.callback_query(ShipmentCB.filter(F.action == "open"))
async def on_open(callback: CallbackQuery, callback_data: ShipmentCB, state: FSMContext, session: AsyncSession,
                  user: User, lang: str, is_admin: bool) -> None:
    shipment = await _get_own(callback, session, user, lang, callback_data.id, is_admin)
    if shipment is None:
        return
    await state.clear()
    await callback.answer()
    await show(callback, shipment_card(shipment, lang), shipment_card_keyboard(shipment, lang))


@router.callback_query(ShipmentCB.filter(F.action == "hist"))
async def on_history(callback: CallbackQuery, callback_data: ShipmentCB, session: AsyncSession,
                     user: User, lang: str, is_admin: bool) -> None:
    shipment = await _get_own(callback, session, user, lang, callback_data.id, is_admin)
    if shipment is None:
        return
    history = await tracking_service.get_history(session, shipment.id)
    await callback.answer()
    await show(callback, history_text(shipment, history, lang), history_keyboard(shipment.id, lang))


@router.callback_query(ShipmentCB.filter(F.action == "cancel"))
async def on_cancel_request(callback: CallbackQuery, callback_data: ShipmentCB, session: AsyncSession,
                            user: User, lang: str) -> None:
    shipment = await _get_own(callback, session, user, lang, callback_data.id)
    if shipment is None:
        return
    await callback.answer()
    await show(callback, t(lang, "sh_cancel_confirm", tracking=shipment.tracking_number),
               cancel_confirm_keyboard(shipment.id, lang))


@router.callback_query(ShipmentCB.filter(F.action == "cancel_yes"))
async def on_cancel_confirmed(callback: CallbackQuery, callback_data: ShipmentCB, session: AsyncSession,
                              user: User, lang: str, settings: Settings) -> None:
    try:
        change = await shipment_service.cancel_by_user(session, user, callback_data.id)
    except shipment_service.AccessDeniedError:
        await callback.answer(t(lang, "access_denied"), show_alert=True)
        return
    except shipment_service.ShipmentNotFoundError:
        await callback.answer(t(lang, "callback_expired"), show_alert=True)
        return
    except (shipment_service.CannotCancelError, tracking_service.TrackingError):
        await callback.answer(t(lang, "sh_cannot_cancel"), show_alert=True)
        return

    shipment = change.shipment
    await callback.answer("✅")
    await show(callback, t(lang, "sh_cancelled_by_user", tracking=shipment.tracking_number) + "\n\n"
               + shipment_card(shipment, lang), shipment_card_keyboard(shipment, lang))
    await notify_admins(callback.bot, settings.admin_ids,
                        admin_shipment_text(shipment, user, title="🚫 <b>Клиент отменил заявку</b>"))
