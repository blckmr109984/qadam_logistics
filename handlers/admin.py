"""Административная панель внутри бота.

Доступ: только Telegram ID из ADMIN_IDS. Фильтр AdminFilter стоит на уровне
роутера (каждый хендлер), а изменяющие действия дополнительно перепроверяют
права через _ensure_admin — защита в глубину.
"""
from __future__ import annotations

import logging
import math
from html import escape

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from config import Settings
from database.models import ShipmentStatus, Tariff, TransportType, User
from handlers.common import show
from i18n import t
from keyboards.admin import (
    AdminCB, back_keyboard, confirm_cancel_keyboard, confirm_status_keyboard, panel_keyboard,
    shipment_admin_keyboard, shipments_list_keyboard, status_choice_keyboard, tariff_keyboard, tariffs_keyboard,
    users_keyboard,
)
from keyboards.inline import ShipmentCB
from services import admin_service, shipment_service, tracking_service, user_service
from states.shipment_states import AdminTariffForm
from utils.catalog import TRANSPORT_EMOJI
from utils.filters import AdminFilter
from utils.formatting import DIVIDER, admin_shipment_text, local_dt, money, number, route_label, status_label, status_notification
from utils.notifications import safe_send
from utils.validators import InputError, parse_price

logger = logging.getLogger(__name__)
router = Router(name="admin")
router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())

PER_PAGE = 8
SCOPE_TITLES = {"new": "📥 Новые заявки", "active": "🚚 Активные поставки", "all": "📋 Все заявки"}


def _ensure_admin(event: Message | CallbackQuery, settings: Settings) -> bool:
    ok = settings.is_admin(event.from_user.id if event.from_user else None)
    if not ok:
        logger.error("Admin check failed for %s", event.from_user.id if event.from_user else None)
    return ok


# ------------------------------------------------------------------ панель

async def _panel_text(session: AsyncSession) -> tuple[str, int]:
    stats = await admin_service.get_stats(session)
    text = (
        "🛠 <b>Админ-панель Qadam Logistics</b>\n"
        f"{DIVIDER}\n"
        f"Новых заявок: <b>{stats.pending}</b>\n"
        f"Активных поставок: <b>{stats.active}</b>\n"
        f"Пользователей: <b>{stats.users}</b>"
    )
    return text, stats.pending


@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext, session: AsyncSession) -> None:
    await state.clear()
    text, pending = await _panel_text(session)
    await message.answer(text, reply_markup=panel_keyboard(pending))


@router.callback_query(AdminCB.filter(F.action == "panel"))
async def on_panel(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    await state.clear()
    await callback.answer()
    text, pending = await _panel_text(session)
    await show(callback, text, panel_keyboard(pending))


# ------------------------------------------------------------------ заявки

@router.callback_query(AdminCB.filter(F.action == "list"))
async def on_list(callback: CallbackQuery, callback_data: AdminCB, session: AsyncSession) -> None:
    scope = callback_data.value if callback_data.value in SCOPE_TITLES else "all"
    total = await admin_service.count_shipments(session, scope)
    pages = max(1, math.ceil(total / PER_PAGE))
    page = min(max(callback_data.page, 0), pages - 1)
    shipments = await admin_service.list_shipments(session, scope, PER_PAGE, page * PER_PAGE)
    await callback.answer()
    text = f"<b>{SCOPE_TITLES[scope]}</b> · {total}\nСтраница {page + 1}/{pages}"
    if not shipments:
        text += "\n\nЗаявок нет."
    await show(callback, text, shipments_list_keyboard(shipments, scope, page, pages))


async def _render_shipment(callback: CallbackQuery, session: AsyncSession, shipment_id: int,
                           scope: str = "all", page: int = 0, notice: str | None = None) -> None:
    try:
        shipment = await shipment_service.get_shipment(session, shipment_id)
    except shipment_service.ShipmentNotFoundError:
        await show(callback, "Поставка не найдена.", back_keyboard())
        return
    owner = await session.get(User, shipment.user_id)
    history = await tracking_service.get_history(session, shipment.id)
    text = admin_shipment_text(shipment, owner, history)
    if notice:
        text = f"{notice}\n\n{text}"
    await show(callback, text, shipment_admin_keyboard(shipment, scope, page))


@router.callback_query(AdminCB.filter(F.action == "open"))
async def on_open(callback: CallbackQuery, callback_data: AdminCB, state: FSMContext, session: AsyncSession) -> None:
    await state.clear()
    await callback.answer()
    await _render_shipment(callback, session, callback_data.id, callback_data.value or "all", callback_data.page)


@router.callback_query(AdminCB.filter(F.action == "status"))
async def on_status_menu(callback: CallbackQuery, callback_data: AdminCB, session: AsyncSession) -> None:
    try:
        shipment = await shipment_service.get_shipment(session, callback_data.id)
    except shipment_service.ShipmentNotFoundError:
        await callback.answer("Поставка не найдена", show_alert=True)
        return
    await callback.answer()
    await show(
        callback,
        f"🔄 <b>Новый статус для {shipment.tracking_number}</b>\n"
        f"Сейчас: {status_label(shipment.status, 'ru')}\n\nДоступны только допустимые переходы:",
        status_choice_keyboard(shipment, callback_data.value or "all", callback_data.page),
    )


@router.callback_query(AdminCB.filter(F.action == "setst"))
async def on_status_pick(callback: CallbackQuery, callback_data: AdminCB, session: AsyncSession) -> None:
    try:
        new_status = ShipmentStatus(callback_data.value)
        shipment = await shipment_service.get_shipment(session, callback_data.id)
    except (ValueError, shipment_service.ShipmentNotFoundError):
        await callback.answer("Некорректные данные", show_alert=True)
        return
    await callback.answer()
    await show(
        callback,
        f"Подтвердите изменение статуса <code>{shipment.tracking_number}</code>:\n\n"
        f"{status_label(callback_data.old or shipment.status, 'ru')} → <b>{status_label(new_status, 'ru')}</b>\n\n"
        "Клиент получит уведомление.",
        confirm_status_keyboard(shipment.id, new_status.value, callback_data.old),
    )


@router.callback_query(AdminCB.filter(F.action == "cancel"))
async def on_cancel_pick(callback: CallbackQuery, callback_data: AdminCB, session: AsyncSession) -> None:
    try:
        shipment = await shipment_service.get_shipment(session, callback_data.id)
    except shipment_service.ShipmentNotFoundError:
        await callback.answer("Поставка не найдена", show_alert=True)
        return
    await callback.answer()
    await show(callback, f"❌ Отменить поставку <code>{shipment.tracking_number}</code>?\nКлиент получит уведомление.",
               confirm_cancel_keyboard(shipment.id, callback_data.old or ShipmentStatus(shipment.status).value))


async def _apply_status(callback: CallbackQuery, session: AsyncSession, settings: Settings,
                        shipment_id: int, new_value: str, old_value: str) -> None:
    if not _ensure_admin(callback, settings):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    try:
        new_status = ShipmentStatus(new_value)
        expected = ShipmentStatus(old_value) if old_value else None
    except ValueError:
        await callback.answer("Некорректный статус", show_alert=True)
        return

    comment = "Отменена администратором" if new_status is ShipmentStatus.CANCELLED else "Статус обновлён менеджером"
    try:
        change = await tracking_service.change_status(
            session, shipment_id, new_status, comment=comment,
            changed_by=callback.from_user.id, expected_old=expected,
        )
    except shipment_service.ShipmentNotFoundError:
        await callback.answer("Поставка не найдена", show_alert=True)
        return
    except tracking_service.StaleStatusError:
        await callback.answer("Статус уже был изменён. Карточка обновлена.", show_alert=True)
        await _render_shipment(callback, session, shipment_id)
        return
    except tracking_service.InvalidTransitionError:
        await callback.answer("Такой переход статуса недопустим.", show_alert=True)
        await _render_shipment(callback, session, shipment_id)
        return

    logger.info("Admin %s: %s %s -> %s", callback.from_user.id, change.shipment.tracking_number,
                change.old_status, change.new_status)
    owner = await session.get(User, change.shipment.user_id)
    delivered = False
    if owner is not None:
        lang = owner.language.value if hasattr(owner.language, "value") else str(owner.language)
        markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(
            text=t(lang, "btn_open_shipment"),
            callback_data=ShipmentCB(action="open", id=change.shipment.id).pack(),
        )]])
        delivered = await safe_send(
            callback.bot, owner.telegram_id,
            status_notification(change.shipment, change.old_status, change.new_status, lang),
            markup,
        )
    await callback.answer("✅ Статус обновлён")
    notice = "✅ Статус обновлён. " + ("Клиент уведомлён." if delivered else "⚠️ Уведомление клиенту не доставлено.")
    await _render_shipment(callback, session, shipment_id, notice=notice)


@router.callback_query(AdminCB.filter(F.action == "confirm"))
async def on_confirm(callback: CallbackQuery, callback_data: AdminCB, session: AsyncSession, settings: Settings) -> None:
    await _apply_status(callback, session, settings, callback_data.id,
                        ShipmentStatus.CONFIRMED.value, callback_data.old or ShipmentStatus.PENDING.value)


@router.callback_query(AdminCB.filter(F.action == "setok"))
async def on_status_apply(callback: CallbackQuery, callback_data: AdminCB, session: AsyncSession,
                          settings: Settings) -> None:
    await _apply_status(callback, session, settings, callback_data.id, callback_data.value, callback_data.old)


# ------------------------------------------------------------------ статистика и пользователи

@router.callback_query(AdminCB.filter(F.action == "stats"))
async def on_stats(callback: CallbackQuery, session: AsyncSession) -> None:
    s = await admin_service.get_stats(session)
    await callback.answer()
    text = (
        "📊 <b>Статистика</b>\n"
        f"{DIVIDER}\n"
        f"👥 Пользователей: <b>{s.users}</b>\n"
        f"📦 Всего поставок: <b>{s.shipments}</b>\n"
        f"⏳ Ожидают подтверждения: <b>{s.pending}</b>\n"
        f"🚚 Активных: <b>{s.active}</b>\n"
        f"🎉 Доставлено: <b>{s.delivered}</b>\n"
        f"❌ Отменено: <b>{s.cancelled}</b>"
    )
    await show(callback, text, back_keyboard())


@router.callback_query(AdminCB.filter(F.action == "users"))
async def on_users(callback: CallbackQuery, callback_data: AdminCB, session: AsyncSession) -> None:
    total = await user_service.count_users(session)
    pages = max(1, math.ceil(total / 10))
    page = min(max(callback_data.page, 0), pages - 1)
    users = await user_service.list_users(session, limit=10, offset=page * 10)
    lines = [f"👥 <b>Пользователи</b> · {total} · стр. {page + 1}/{pages}", DIVIDER]
    for u in users:
        username = f" @{escape(u.username)}" if u.username else ""
        lang = u.language.value if hasattr(u.language, "value") else u.language
        lines.append(
            f"• {escape(u.full_name or '—')}{username}\n"
            f"   ID <code>{u.telegram_id}</code> · {lang} · {escape(u.phone or 'нет телефона')} · {local_dt(u.created_at)}"
        )
    await callback.answer()
    await show(callback, "\n".join(lines), users_keyboard(page, pages))


# ------------------------------------------------------------------ тарифы

def _tariff_text(tariff: Tariff) -> str:
    status = "✅ активен" if tariff.is_active else "⛔ отключён"
    transport = TransportType(tariff.transport_type)
    return (
        f"💲 <b>Тариф #{tariff.id}</b> · {status}\n"
        f"{route_label(tariff.route.origin, tariff.route.destination, 'ru')} · {tariff.route.distance_km} км\n"
        f"{TRANSPORT_EMOJI[transport]} {t('ru', f'tr_{transport.value}')}\n"
        f"{DIVIDER}\n"
        f"Базовая стоимость маршрута: <b>{money(tariff.base_price)}</b>\n"
        f"Цена за 1 кг: <b>{money(tariff.price_per_kg)}</b>\n"
        f"Цена за 1 м³: <b>{money(tariff.price_per_m3)}</b>\n"
        f"Дополнительные расходы: <b>{money(tariff.additional_cost)}</b>\n\n"
        "<i>Тестовый тариф для демонстрации. Изменения применяются к новым расчётам сразу.</i>"
    )


@router.callback_query(AdminCB.filter(F.action == "tariffs"))
async def on_tariffs(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    await state.clear()
    tariffs = await admin_service.list_tariffs(session)
    await callback.answer()
    await show(callback, f"💲 <b>Тарифы</b> · {len(tariffs)}\nВыберите тариф для редактирования:",
               tariffs_keyboard(tariffs))


@router.callback_query(AdminCB.filter(F.action == "tariff"))
async def on_tariff(callback: CallbackQuery, callback_data: AdminCB, state: FSMContext, session: AsyncSession) -> None:
    await state.clear()
    tariff = await admin_service.get_tariff(session, callback_data.id)
    await callback.answer()
    if tariff is None:
        await show(callback, "Тариф не найден.", back_keyboard())
        return
    await show(callback, _tariff_text(tariff), tariff_keyboard(tariff))


@router.callback_query(AdminCB.filter(F.action == "tfield"))
async def on_tariff_field(callback: CallbackQuery, callback_data: AdminCB, state: FSMContext,
                          session: AsyncSession) -> None:
    field = callback_data.value
    tariff = await admin_service.get_tariff(session, callback_data.id)
    if tariff is None or field not in admin_service.TARIFF_FIELDS:
        await callback.answer("Некорректные данные", show_alert=True)
        return
    await state.set_state(AdminTariffForm.value)
    await state.update_data(tariff_id=tariff.id, field=field)
    await callback.answer()
    cancel = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(
        text="✖️ Отмена", callback_data=AdminCB(action="tariff", id=tariff.id).pack())]])
    await show(
        callback,
        f"✏️ <b>{admin_service.TARIFF_FIELDS[field]}</b>\n"
        f"Текущее значение: <b>{number(getattr(tariff, field))}</b>\n\n"
        "Введите новое значение (неотрицательное число), например <code>15000</code>:",
        cancel,
    )


@router.message(AdminTariffForm.value, F.text)
async def on_tariff_value(message: Message, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    if not _ensure_admin(message, settings):
        await state.clear()
        return
    data = await state.get_data()
    try:
        value = parse_price(message.text)
    except InputError as err:
        await message.answer(f"⚠️ {t('ru', err.key, **err.params)} Значение должно быть ≥ 0.")
        return
    try:
        tariff = await admin_service.update_tariff_field(
            session, int(data["tariff_id"]), data["field"], value, message.from_user.id
        )
    except (KeyError, LookupError, ValueError):
        await state.clear()
        await message.answer("Не удалось обновить тариф.", reply_markup=back_keyboard())
        return
    await state.clear()
    await message.answer("✅ Тариф обновлён\n\n" + _tariff_text(tariff), reply_markup=tariff_keyboard(tariff))


@router.callback_query(AdminCB.filter(F.action == "ttoggle"))
async def on_tariff_toggle(callback: CallbackQuery, callback_data: AdminCB, session: AsyncSession,
                           settings: Settings) -> None:
    if not _ensure_admin(callback, settings):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    try:
        tariff = await admin_service.toggle_tariff(session, callback_data.id, callback.from_user.id)
    except LookupError:
        await callback.answer("Тариф не найден", show_alert=True)
        return
    await callback.answer("Готово")
    await show(callback, _tariff_text(tariff), tariff_keyboard(tariff))
