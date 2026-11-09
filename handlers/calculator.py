"""Калькулятор предварительной стоимости: маршрут → вес → объём → сравнение видов транспорта."""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User
from handlers.common import show
from handlers.shipment import start_shipment
from i18n import t
from keyboards.inline import CalcCB, CityCB, cancel_keyboard, home_keyboard
from keyboards.shipment import calc_result_keyboard, cities_keyboard
from services import pricing_service as pricing
from states.shipment_states import CalcForm
from utils.formatting import compact_quote_line, draft_summary, price_breakdown, transport_label
from utils.validators import InputError, parse_volume, parse_weight

router = Router(name="calculator")

CALC_KEYS = ("origin", "destination", "weight", "volume")


async def start_calculator(target: Message | CallbackQuery, state: FSMContext, session: AsyncSession, lang: str,
                           prefill: dict[str, Any] | None = None) -> None:
    await state.clear()
    await state.set_data({k: v for k, v in (prefill or {}).items() if k in CALC_KEYS and v})
    await ask_calc_next(target, state, session, lang)


async def ask_calc_next(target: Message | CallbackQuery, state: FSMContext, session: AsyncSession, lang: str) -> None:
    data = await state.get_data()
    origins = await pricing.list_origins(session)
    if not origins:
        await state.clear()
        await show(target, t(lang, "no_routes"), home_keyboard(lang))
        return
    if data.get("origin") not in origins:
        data.update(origin=None, destination=None)
    elif data.get("destination") and data["destination"] not in await pricing.list_destinations(session, data["origin"]):
        data["destination"] = None
    await state.set_data(data)

    step = next((k for k in CALC_KEYS if not data.get(k)), "result")
    if step == "result":
        await _show_result(target, state, session, lang, data)
        return
    number = CALC_KEYS.index(step) + 1
    head = "\n".join(filter(None, [t(lang, "calc_header", step=number), draft_summary(data, lang)])) + "\n\n"
    await state.set_state(getattr(CalcForm, step))
    if step == "origin":
        await show(target, head + t(lang, "ask_origin"), cities_keyboard(origins, "o", lang))
    elif step == "destination":
        destinations = await pricing.list_destinations(session, data["origin"])
        await show(target, head + t(lang, "ask_destination"), cities_keyboard(destinations, "d", lang))
    else:
        await show(target, head + t(lang, f"ask_{step}"), cancel_keyboard(lang))


async def _show_result(target, state: FSMContext, session: AsyncSession, lang: str, data: dict[str, Any]) -> None:
    try:
        quotes = await pricing.get_all_quotes(
            session, data["origin"], data["destination"], Decimal(data["weight"]), Decimal(data["volume"])
        )
    except pricing.PricingError:
        await state.clear()
        await show(target, t(lang, "no_transport"), home_keyboard(lang))
        return
    await state.set_state(CalcForm.result)

    parts = [t(lang, "calc_result_title"), ""]
    if len(quotes) > 1:
        parts += [compact_quote_line(q, lang) for q in quotes]
        parts += [t(lang, "calc_best", transport=transport_label(quotes[0].transport_type, lang)), ""]
    parts.append("\n\n".join(price_breakdown(q, lang, footer=(i == len(quotes) - 1)) for i, q in enumerate(quotes)))
    await show(target, "\n".join(parts), calc_result_keyboard(quotes, lang))


@router.callback_query(CalcForm.origin, CityCB.filter(F.role == "o"))
async def on_origin(callback: CallbackQuery, callback_data: CityCB, state: FSMContext,
                    session: AsyncSession, lang: str) -> None:
    await callback.answer()
    await state.update_data(origin=callback_data.code, destination=None)
    await ask_calc_next(callback, state, session, lang)


@router.callback_query(CalcForm.destination, CityCB.filter(F.role == "d"))
async def on_destination(callback: CallbackQuery, callback_data: CityCB, state: FSMContext,
                         session: AsyncSession, lang: str) -> None:
    await callback.answer()
    await state.update_data(destination=callback_data.code)
    await ask_calc_next(callback, state, session, lang)


@router.message(CalcForm.weight, F.text)
async def on_weight(message: Message, state: FSMContext, session: AsyncSession, lang: str) -> None:
    try:
        await state.update_data(weight=str(parse_weight(message.text)))
    except InputError as err:
        await message.answer(f"⚠️ {t(lang, err.key, **err.params)}", reply_markup=cancel_keyboard(lang))
        return
    await ask_calc_next(message, state, session, lang)


@router.message(CalcForm.volume, F.text)
async def on_volume(message: Message, state: FSMContext, session: AsyncSession, lang: str) -> None:
    try:
        await state.update_data(volume=str(parse_volume(message.text)))
    except InputError as err:
        await message.answer(f"⚠️ {t(lang, err.key, **err.params)}", reply_markup=cancel_keyboard(lang))
        return
    await ask_calc_next(message, state, session, lang)


@router.callback_query(CalcForm.result, CalcCB.filter(F.action == "order"))
async def on_order(callback: CallbackQuery, callback_data: CalcCB, state: FSMContext,
                   session: AsyncSession, user: User, lang: str) -> None:
    """Переход к оформлению с уже введёнными данными расчёта."""
    await callback.answer()
    data = await state.get_data()
    prefill = {k: data.get(k) for k in CALC_KEYS} | {"transport": callback_data.transport}
    await start_shipment(callback, state, session, user, lang, prefill=prefill)


@router.callback_query(CalcCB.filter(F.action == "again"))
async def on_again(callback: CallbackQuery, state: FSMContext, session: AsyncSession, lang: str) -> None:
    await callback.answer()
    await start_calculator(callback, state, session, lang)


@router.callback_query(CalcCB.filter(F.action == "order"))
async def on_order_outdated(callback: CallbackQuery, lang: str) -> None:
    await callback.answer(t(lang, "callback_expired"), show_alert=True)


@router.message(StateFilter(CalcForm))
async def on_unexpected(message: Message, state: FSMContext, session: AsyncSession, lang: str) -> None:
    await message.answer(f"⚠️ {t(lang, 'err_use_buttons')}")
    await ask_calc_next(message, state, session, lang)
