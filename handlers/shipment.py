"""Пошаговое оформление поставки (FSM, 10 шагов).

Ключевая идея: после каждого ответа вызывается ask_next(), которая находит
первое незаполненное поле и задаёт следующий вопрос. Благодаря этому одна и
та же логика работает и при ручном вводе, и при предзаполнении данными из
калькулятора или AI-помощника.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from config import Settings
from database.models import CargoCategory, TransportType, User
from i18n import t
from keyboards.admin import new_shipment_admin_keyboard
from keyboards.inline import CategoryCB, CityCB, ConfirmCB, DateCB, TransportCB, cancel_keyboard, home_keyboard
from keyboards.main_menu import main_menu_keyboard
from keyboards.shipment import (
    categories_keyboard, cities_keyboard, confirm_keyboard, created_keyboard, dates_keyboard,
    phone_keyboard, transports_keyboard,
)
from handlers.common import show
from services import pricing_service as pricing
from services import user_service
from services.shipment_service import ShipmentCreate, ShipmentError, create_shipment
from states.shipment_states import ShipmentForm
from utils.formatting import DIVIDER, admin_shipment_text, draft_details, draft_summary, local_today, price_breakdown
from utils.notifications import notify_admins
from utils.validators import InputError, normalize_phone, parse_date, parse_packages, parse_volume, parse_weight, validate_date

logger = logging.getLogger(__name__)
router = Router(name="shipment")

STEPS = ["origin", "destination", "category", "weight", "volume", "packages", "transport", "date", "phone", "confirm"]
STATES = {
    "origin": ShipmentForm.origin, "destination": ShipmentForm.destination, "category": ShipmentForm.category,
    "weight": ShipmentForm.weight, "volume": ShipmentForm.volume, "packages": ShipmentForm.packages,
    "transport": ShipmentForm.transport, "date": ShipmentForm.date, "phone": ShipmentForm.phone,
    "confirm": ShipmentForm.confirm,
}
FORM_KEYS = ("origin", "destination", "category", "weight", "volume", "packages", "transport", "date", "phone")


async def start_shipment(
    target: Message | CallbackQuery, state: FSMContext, session: AsyncSession, user: User, lang: str,
    prefill: dict[str, Any] | None = None,
) -> None:
    await state.clear()
    clean = {k: v for k, v in (prefill or {}).items() if k in FORM_KEYS and v not in (None, "")}
    await state.set_data(clean)
    await ask_next(target, state, session, user, lang)


async def _sanitize(data: dict[str, Any], session: AsyncSession) -> tuple[dict[str, Any], list[str]]:
    """Проверяет согласованность маршрута и транспорта с актуальными данными в БД."""
    origins = await pricing.list_origins(session)
    if data.get("origin") not in origins:
        data.update(origin=None, destination=None, transport=None)
    elif data.get("destination"):
        if data["destination"] not in await pricing.list_destinations(session, data["origin"]):
            data.update(destination=None, transport=None)
    if data.get("origin") and data.get("destination") and data.get("transport"):
        transports = await pricing.list_transports(session, data["origin"], data["destination"])
        if TransportType(data["transport"]) not in transports:
            data["transport"] = None
    if data.get("category"):
        try:
            CargoCategory(data["category"])
        except ValueError:
            data["category"] = None
    return data, origins


async def ask_next(target: Message | CallbackQuery, state: FSMContext, session: AsyncSession, user: User,
                   lang: str, *, prefix: str = "") -> None:
    data, origins = await _sanitize(await state.get_data(), session)
    await state.set_data(data)
    if not origins:
        await state.clear()
        await show(target, t(lang, "no_routes"), home_keyboard(lang))
        return

    step = next(s for s in STEPS if s == "confirm" or not data.get(s))
    await state.set_state(STATES[step])
    header = t(lang, "sh_header", step=STEPS.index(step) + 1)
    summary = draft_summary(data, lang)
    head = "\n".join(filter(None, [prefix, header, summary])) + "\n\n"

    if step == "origin":
        await show(target, head + t(lang, "ask_origin"), cities_keyboard(origins, "o", lang))
    elif step == "destination":
        destinations = await pricing.list_destinations(session, data["origin"])
        await show(target, head + t(lang, "ask_destination"), cities_keyboard(destinations, "d", lang))
    elif step == "category":
        await show(target, head + t(lang, "ask_category"), categories_keyboard(lang))
    elif step in ("weight", "volume", "packages"):
        await show(target, head + t(lang, f"ask_{step}"), cancel_keyboard(lang))
    elif step == "transport":
        transports = await pricing.list_transports(session, data["origin"], data["destination"])
        await show(target, head + t(lang, "ask_transport"), transports_keyboard(transports, lang))
    elif step == "date":
        await show(target, head + t(lang, "ask_date"), dates_keyboard(lang))
    elif step == "phone":
        await show(target, head + t(lang, "ask_phone"), phone_keyboard(lang, user.phone), edit=False)
    else:
        await _show_confirmation(target, state, session, lang, data, head)


async def _show_confirmation(target, state: FSMContext, session: AsyncSession, lang: str,
                             data: dict[str, Any], head: str) -> None:
    try:
        quote = await pricing.get_quote(
            session, data["origin"], data["destination"], TransportType(data["transport"]),
            Decimal(data["weight"]), Decimal(data["volume"]),
        )
    except pricing.PricingError:
        await state.update_data(destination=None, transport=None)
        await show(target, t(lang, "route_unavailable"), cancel_keyboard(lang))
        return
    text = (
        f"{head}{t(lang, 'sh_summary_title')}\n{DIVIDER}\n{draft_details(data, lang)}\n\n"
        f"{price_breakdown(quote, lang)}\n\n{t(lang, 'sh_confirm_hint')}"
    )
    await show(target, text, confirm_keyboard(lang))


# ------------------------------------------------------------------ шаги 1–3

@router.callback_query(ShipmentForm.origin, CityCB.filter(F.role == "o"))
async def on_origin(callback: CallbackQuery, callback_data: CityCB, state: FSMContext,
                    session: AsyncSession, user: User, lang: str) -> None:
    await callback.answer()
    await state.update_data(origin=callback_data.code, destination=None, transport=None)
    await ask_next(callback, state, session, user, lang)


@router.callback_query(ShipmentForm.destination, CityCB.filter(F.role == "d"))
async def on_destination(callback: CallbackQuery, callback_data: CityCB, state: FSMContext,
                         session: AsyncSession, user: User, lang: str) -> None:
    await callback.answer()
    await state.update_data(destination=callback_data.code, transport=None)
    await ask_next(callback, state, session, user, lang)


@router.callback_query(ShipmentForm.category, CategoryCB.filter())
async def on_category(callback: CallbackQuery, callback_data: CategoryCB, state: FSMContext,
                      session: AsyncSession, user: User, lang: str) -> None:
    await callback.answer()
    await state.update_data(category=callback_data.code)
    await ask_next(callback, state, session, user, lang)


# ------------------------------------------------------------------ шаги 4–6 (текстовый ввод)

async def _numeric_step(message: Message, state: FSMContext, session: AsyncSession, user: User, lang: str,
                        key: str, parser) -> None:
    try:
        value = parser(message.text)
    except InputError as err:
        await message.answer(f"⚠️ {t(lang, err.key, **err.params)}", reply_markup=cancel_keyboard(lang))
        return
    await state.update_data(**{key: value if isinstance(value, int) else str(value)})
    await ask_next(message, state, session, user, lang)


@router.message(ShipmentForm.weight, F.text)
async def on_weight(message: Message, state: FSMContext, session: AsyncSession, user: User, lang: str) -> None:
    await _numeric_step(message, state, session, user, lang, "weight", parse_weight)


@router.message(ShipmentForm.volume, F.text)
async def on_volume(message: Message, state: FSMContext, session: AsyncSession, user: User, lang: str) -> None:
    await _numeric_step(message, state, session, user, lang, "volume", parse_volume)


@router.message(ShipmentForm.packages, F.text)
async def on_packages(message: Message, state: FSMContext, session: AsyncSession, user: User, lang: str) -> None:
    await _numeric_step(message, state, session, user, lang, "packages", parse_packages)


# ------------------------------------------------------------------ шаги 7–8

@router.callback_query(ShipmentForm.transport, TransportCB.filter())
async def on_transport(callback: CallbackQuery, callback_data: TransportCB, state: FSMContext,
                       session: AsyncSession, user: User, lang: str) -> None:
    await callback.answer()
    try:
        transport = TransportType(callback_data.code)
    except ValueError:
        return
    await state.update_data(transport=transport.value)
    await ask_next(callback, state, session, user, lang)


@router.callback_query(ShipmentForm.date, DateCB.filter())
async def on_date_button(callback: CallbackQuery, callback_data: DateCB, state: FSMContext,
                         session: AsyncSession, user: User, lang: str) -> None:
    today = local_today()
    try:
        chosen = validate_date(today + timedelta(days=callback_data.days), today)
    except InputError as err:
        await callback.answer(t(lang, err.key, **err.params), show_alert=True)
        return
    await callback.answer()
    await state.update_data(date=chosen.isoformat())
    await ask_next(callback, state, session, user, lang)


@router.message(ShipmentForm.date, F.text)
async def on_date_text(message: Message, state: FSMContext, session: AsyncSession, user: User, lang: str) -> None:
    try:
        chosen = parse_date(message.text, local_today())
    except InputError as err:
        await message.answer(f"⚠️ {t(lang, err.key, **err.params)}", reply_markup=dates_keyboard(lang))
        return
    await state.update_data(date=chosen.isoformat())
    await ask_next(message, state, session, user, lang)


# ------------------------------------------------------------------ шаг 9: телефон

@router.message(ShipmentForm.phone, F.contact | F.text)
async def on_phone(message: Message, state: FSMContext, session: AsyncSession, user: User, lang: str) -> None:
    raw = message.contact.phone_number if message.contact else message.text
    try:
        phone = normalize_phone(raw)
    except InputError as err:
        await message.answer(f"⚠️ {t(lang, err.key)}", reply_markup=phone_keyboard(lang, user.phone))
        return
    await state.update_data(phone=phone)
    if user.phone != phone:
        await user_service.set_phone(session, user, phone)
    await message.answer(t(lang, "phone_saved", phone=phone), reply_markup=main_menu_keyboard(lang))
    await ask_next(message, state, session, user, lang)


# ------------------------------------------------------------------ шаг 10: подтверждение

@router.callback_query(ShipmentForm.confirm, ConfirmCB.filter(F.action == "yes"))
async def on_confirm(callback: CallbackQuery, state: FSMContext, session: AsyncSession, user: User,
                     lang: str, settings: Settings) -> None:
    data = await state.get_data()
    await state.clear()  # сразу очищаем — повторное нажатие уже не создаст вторую заявку
    try:
        payload = ShipmentCreate(
            origin=data["origin"], destination=data["destination"],
            cargo_category=CargoCategory(data["category"]),
            weight=Decimal(data["weight"]), volume=Decimal(data["volume"]),
            packages=int(data["packages"]), transport_type=TransportType(data["transport"]),
            desired_date=date.fromisoformat(data["date"]) if data.get("date") else None,
            contact_phone=data.get("phone"),
        )
    except (KeyError, ValueError, ValidationError):
        logger.exception("Invalid shipment draft: %s", data)
        await callback.answer()
        await show(callback, t(lang, "error_generic"), home_keyboard(lang))
        return

    try:
        shipment, _quote = await create_shipment(session, user, payload)
    except (pricing.PricingError, ShipmentError):
        logger.exception("Failed to create shipment")
        await callback.answer()
        await show(callback, t(lang, "route_unavailable"), home_keyboard(lang))
        return

    await callback.answer("✅")
    await show(callback, t(lang, "sh_created", tracking=shipment.tracking_number), created_keyboard(shipment.id, lang))
    await notify_admins(
        callback.bot, settings.admin_ids,
        admin_shipment_text(shipment, user, title="🆕 <b>Новая заявка</b>"),
        new_shipment_admin_keyboard(shipment),
    )


@router.callback_query(ShipmentForm.confirm, ConfirmCB.filter(F.action == "no"))
async def on_decline(callback: CallbackQuery, state: FSMContext, lang: str) -> None:
    await state.clear()
    await callback.answer()
    await show(callback, t(lang, "sh_cancelled"), home_keyboard(lang))


@router.callback_query(ConfirmCB.filter())
async def on_confirm_outdated(callback: CallbackQuery, lang: str) -> None:
    """Кнопка подтверждения нажата повторно, когда заявка уже создана/отменена."""
    await callback.answer(t(lang, "sh_already_processed"), show_alert=True)


# ------------------------------------------------------------------ неожиданный ввод на любом шаге

@router.message(StateFilter(ShipmentForm))
async def on_unexpected_input(message: Message, state: FSMContext, session: AsyncSession, user: User, lang: str) -> None:
    await ask_next(message, state, session, user, lang, prefix=f"⚠️ {t(lang, 'err_use_buttons')}")
