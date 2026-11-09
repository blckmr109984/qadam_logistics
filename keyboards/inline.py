"""Фабрики callback-данных и общие inline-кнопки."""
from __future__ import annotations

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from i18n import t


class MenuCB(CallbackData, prefix="m"):
    action: str  # home | cancel


class LangCB(CallbackData, prefix="lang"):
    code: str


class CityCB(CallbackData, prefix="city"):
    role: str  # o — откуда, d — куда
    code: str


class CategoryCB(CallbackData, prefix="cat"):
    code: str


class TransportCB(CallbackData, prefix="tr"):
    code: str


class DateCB(CallbackData, prefix="dt"):
    days: int


class ConfirmCB(CallbackData, prefix="cf"):
    action: str  # yes | no


class ShipmentCB(CallbackData, prefix="sh"):
    action: str  # open | hist | cancel | cancel_yes
    id: int


class PageCB(CallbackData, prefix="pg"):
    scope: str
    page: int


class CalcCB(CallbackData, prefix="calc"):
    action: str  # order | again
    transport: str = ""


class AssistantCB(CallbackData, prefix="ai"):
    action: str  # fill | calc | manual


def home_button(lang: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=t(lang, "btn_home"), callback_data=MenuCB(action="home").pack())


def cancel_button(lang: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=t(lang, "btn_cancel"), callback_data=MenuCB(action="cancel").pack())


def home_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[home_button(lang)]])


def cancel_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[cancel_button(lang)]])


def builder_with_footer(builder: InlineKeyboardBuilder, lang: str, *, cancel: bool = False) -> InlineKeyboardMarkup:
    builder.row(cancel_button(lang) if cancel else home_button(lang))
    return builder.as_markup()
