"""Клавиатуры административной панели (интерфейс администратора — на русском)."""
from __future__ import annotations

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.models import Shipment, ShipmentStatus, Tariff, TransportType
from services.admin_service import TARIFF_FIELDS
from services.tracking_service import allowed_next_statuses
from utils.catalog import STATUS_EMOJI, TRANSPORT_EMOJI, city_name
from i18n import t


class AdminCB(CallbackData, prefix="adm"):
    action: str
    id: int = 0
    page: int = 0
    value: str = ""
    old: str = ""  # ожидаемый текущий статус — защита от устаревших кнопок


def _btn(text: str, cb: AdminCB) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=cb.pack())


def panel_keyboard(pending: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [_btn(f"📥 Новые заявки ({pending})", AdminCB(action="list", value="new"))],
        [_btn("🚚 Активные", AdminCB(action="list", value="active")),
         _btn("📋 Все заявки", AdminCB(action="list", value="all"))],
        [_btn("📊 Статистика", AdminCB(action="stats")), _btn("💲 Тарифы", AdminCB(action="tariffs"))],
        [_btn("👥 Пользователи", AdminCB(action="users"))],
    ])


def back_to_panel() -> InlineKeyboardButton:
    return _btn("⬅️ Админ-панель", AdminCB(action="panel"))


def shipments_list_keyboard(shipments: list[Shipment], scope: str, page: int, total_pages: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for s in shipments:
        text = (f"{STATUS_EMOJI[ShipmentStatus(s.status)]} {s.tracking_number} · "
                f"{city_name(s.origin)}→{city_name(s.destination)}")
        builder.row(_btn(text, AdminCB(action="open", id=s.id, value=scope, page=page)))
    nav = []
    if page > 0:
        nav.append(_btn("◀️", AdminCB(action="list", value=scope, page=page - 1)))
    if page < total_pages - 1:
        nav.append(_btn("▶️", AdminCB(action="list", value=scope, page=page + 1)))
    if nav:
        builder.row(*nav)
    builder.row(back_to_panel())
    return builder.as_markup()


def shipment_admin_keyboard(shipment: Shipment, scope: str = "all", page: int = 0) -> InlineKeyboardMarkup:
    status = ShipmentStatus(shipment.status)
    rows: list[list[InlineKeyboardButton]] = []
    if status is ShipmentStatus.PENDING:
        rows.append([_btn("✅ Подтвердить заявку", AdminCB(action="confirm", id=shipment.id, old=status.value))])
    if any(s is not ShipmentStatus.CANCELLED for s in allowed_next_statuses(shipment)):
        rows.append([_btn("🔄 Изменить статус", AdminCB(action="status", id=shipment.id, value=scope, page=page))])
    if ShipmentStatus.CANCELLED in allowed_next_statuses(shipment):
        rows.append([_btn("❌ Отменить поставку", AdminCB(action="cancel", id=shipment.id, old=status.value))])
    rows.append([_btn("🔄 Обновить", AdminCB(action="open", id=shipment.id, value=scope, page=page)),
                 _btn("⬅️ К списку", AdminCB(action="list", value=scope, page=page))])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def status_choice_keyboard(shipment: Shipment, scope: str, page: int) -> InlineKeyboardMarkup:
    old = ShipmentStatus(shipment.status).value
    rows = [
        [_btn(f"{STATUS_EMOJI[s]} {t('ru', f'status_{s.value}')}",
              AdminCB(action="setst", id=shipment.id, value=s.value, old=old))]
        for s in allowed_next_statuses(shipment) if s is not ShipmentStatus.CANCELLED
    ]
    rows.append([_btn("⬅️ Назад", AdminCB(action="open", id=shipment.id, value=scope, page=page))])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def confirm_status_keyboard(shipment_id: int, new_status: str, old: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [_btn("✅ Да, применить", AdminCB(action="setok", id=shipment_id, value=new_status, old=old)),
         _btn("Нет", AdminCB(action="open", id=shipment_id))],
    ])


def confirm_cancel_keyboard(shipment_id: int, old: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [_btn("❌ Да, отменить поставку", AdminCB(action="setok", id=shipment_id,
                                                 value=ShipmentStatus.CANCELLED.value, old=old)),
         _btn("Нет", AdminCB(action="open", id=shipment_id))],
    ])


def tariffs_keyboard(tariffs: list[Tariff]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for tariff in tariffs:
        mark = "" if tariff.is_active else " ⛔"
        text = (f"{city_name(tariff.route.origin)}→{city_name(tariff.route.destination)} "
                f"{TRANSPORT_EMOJI[TransportType(tariff.transport_type)]}{mark}")
        builder.button(text=text, callback_data=AdminCB(action="tariff", id=tariff.id))
    builder.adjust(2)
    builder.row(back_to_panel())
    return builder.as_markup()


def tariff_keyboard(tariff: Tariff) -> InlineKeyboardMarkup:
    rows = [[_btn(f"✏️ {title}", AdminCB(action="tfield", id=tariff.id, value=field))]
            for field, title in TARIFF_FIELDS.items()]
    rows.append([_btn("⛔ Отключить тариф" if tariff.is_active else "✅ Включить тариф",
                      AdminCB(action="ttoggle", id=tariff.id))])
    rows.append([_btn("⬅️ К тарифам", AdminCB(action="tariffs"))])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def users_keyboard(page: int, total_pages: int) -> InlineKeyboardMarkup:
    nav = []
    if page > 0:
        nav.append(_btn("◀️", AdminCB(action="users", page=page - 1)))
    if page < total_pages - 1:
        nav.append(_btn("▶️", AdminCB(action="users", page=page + 1)))
    rows = [nav] if nav else []
    rows.append([back_to_panel()])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def new_shipment_admin_keyboard(shipment: Shipment) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [_btn("✅ Подтвердить", AdminCB(action="confirm", id=shipment.id, old=ShipmentStatus.PENDING.value)),
         _btn("🔎 Открыть", AdminCB(action="open", id=shipment.id, value="new"))],
    ])


def back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[back_to_panel()]])
