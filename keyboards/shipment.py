"""Клавиатуры оформления поставки, калькулятора, карточки поставки и списков."""
from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.models import CargoCategory, Shipment, ShipmentStatus, TransportType
from i18n import t
from keyboards.inline import (
    AssistantCB, CalcCB, CategoryCB, CityCB, ConfirmCB, DateCB, PageCB, ShipmentCB, TransportCB,
    builder_with_footer, home_button,
)
from services.pricing_service import PriceQuote
from services.tracking_service import USER_CANCELLABLE
from utils.catalog import CATEGORY_EMOJI, STATUS_EMOJI, TRANSPORT_EMOJI, city_label, city_name


def cities_keyboard(codes: list[str], role: str, lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for code in codes:
        builder.button(text=city_label(code, lang), callback_data=CityCB(role=role, code=code))
    builder.adjust(2)
    return builder_with_footer(builder, lang, cancel=True)


def categories_keyboard(lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for category in CargoCategory:
        builder.button(text=f"{CATEGORY_EMOJI[category]} {t(lang, f'cat_{category.value}')}",
                       callback_data=CategoryCB(code=category.value))
    builder.adjust(2)
    return builder_with_footer(builder, lang, cancel=True)


def transports_keyboard(transports: list[TransportType], lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for transport in transports:
        builder.button(text=f"{TRANSPORT_EMOJI[transport]} {t(lang, f'tr_{transport.value}')}",
                       callback_data=TransportCB(code=transport.value))
    builder.adjust(1)
    return builder_with_footer(builder, lang, cancel=True)


def dates_keyboard(lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=t(lang, "date_today"), callback_data=DateCB(days=0))
    builder.button(text=t(lang, "date_tomorrow"), callback_data=DateCB(days=1))
    builder.button(text=t(lang, "date_in_days", n=3), callback_data=DateCB(days=3))
    builder.button(text=t(lang, "date_in_days", n=7), callback_data=DateCB(days=7))
    builder.adjust(2)
    return builder_with_footer(builder, lang, cancel=True)


def phone_keyboard(lang: str, saved_phone: str | None = None) -> ReplyKeyboardMarkup:
    rows = [[KeyboardButton(text=t(lang, "btn_send_contact"), request_contact=True)]]
    if saved_phone:
        rows.append([KeyboardButton(text=saved_phone)])
    rows.append([KeyboardButton(text=t(lang, "btn_cancel"))])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True, one_time_keyboard=True)


def confirm_keyboard(lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=t(lang, "btn_confirm"), callback_data=ConfirmCB(action="yes"))
    builder.button(text=t(lang, "btn_cancel"), callback_data=ConfirmCB(action="no"))
    builder.adjust(1)
    return builder.as_markup()


def created_keyboard(shipment_id: int, lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=t(lang, "btn_open_shipment"), callback_data=ShipmentCB(action="open", id=shipment_id))
    builder.adjust(1)
    return builder_with_footer(builder, lang)


def shipment_card_keyboard(shipment: Shipment, lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=t(lang, "btn_refresh"), callback_data=ShipmentCB(action="open", id=shipment.id))
    builder.button(text=t(lang, "btn_history"), callback_data=ShipmentCB(action="hist", id=shipment.id))
    if ShipmentStatus(shipment.status) in USER_CANCELLABLE:
        builder.button(text=t(lang, "btn_cancel_shipment"), callback_data=ShipmentCB(action="cancel", id=shipment.id))
    builder.button(text=t(lang, "btn_back_list"), callback_data=PageCB(scope="my", page=0))
    builder.adjust(2, 1, 1)
    return builder_with_footer(builder, lang)


def history_keyboard(shipment_id: int, lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=t(lang, "btn_back_card"), callback_data=ShipmentCB(action="open", id=shipment_id))
    return builder_with_footer(builder, lang)


def cancel_confirm_keyboard(shipment_id: int, lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=t(lang, "btn_yes_cancel"), callback_data=ShipmentCB(action="cancel_yes", id=shipment_id))
    builder.button(text=t(lang, "btn_no"), callback_data=ShipmentCB(action="open", id=shipment_id))
    builder.adjust(2)
    return builder.as_markup()


def my_shipments_keyboard(shipments: list[Shipment], page: int, total_pages: int, lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for s in shipments:
        text = (f"{STATUS_EMOJI[ShipmentStatus(s.status)]} {s.tracking_number} · "
                f"{city_name(s.origin, lang)}→{city_name(s.destination, lang)}")
        builder.row(InlineKeyboardButton(text=text, callback_data=ShipmentCB(action="open", id=s.id).pack()))
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=PageCB(scope="my", page=page - 1).pack()))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=PageCB(scope="my", page=page + 1).pack()))
    if nav:
        builder.row(*nav)
    builder.row(home_button(lang))
    return builder.as_markup()


def calc_result_keyboard(quotes: list[PriceQuote], lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for quote in quotes:
        transport = quote.transport_type
        builder.button(
            text=t(lang, "btn_order_with", transport=f"{TRANSPORT_EMOJI[transport]} {t(lang, f'tr_{transport.value}')}"),
            callback_data=CalcCB(action="order", transport=transport.value),
        )
    builder.button(text=t(lang, "btn_new_calc"), callback_data=CalcCB(action="again"))
    builder.adjust(1)
    return builder_with_footer(builder, lang)


def assistant_extracted_keyboard(lang: str, can_calc: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=t(lang, "btn_ai_fill"), callback_data=AssistantCB(action="fill"))
    if can_calc:
        builder.button(text=t(lang, "btn_ai_calc"), callback_data=AssistantCB(action="calc"))
    builder.button(text=t(lang, "btn_ai_manual"), callback_data=AssistantCB(action="manual"))
    builder.adjust(1)
    return builder_with_footer(builder, lang)
