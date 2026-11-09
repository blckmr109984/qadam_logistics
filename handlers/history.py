"""Раздел «Мои поставки» — список собственных поставок с пагинацией."""
from __future__ import annotations

import math

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User
from handlers.common import show
from i18n import t
from keyboards.inline import PageCB, home_keyboard
from keyboards.shipment import my_shipments_keyboard
from services import shipment_service

router = Router(name="history")
PER_PAGE = 5


async def show_my_shipments(target: Message | CallbackQuery, state: FSMContext, session: AsyncSession,
                            user: User, lang: str, page: int = 0) -> None:
    await state.clear()
    total = await shipment_service.count_user_shipments(session, user)
    if total == 0:
        await show(target, t(lang, "my_empty"), home_keyboard(lang))
        return
    pages = max(1, math.ceil(total / PER_PAGE))
    page = min(max(page, 0), pages - 1)
    shipments = await shipment_service.list_user_shipments(session, user, limit=PER_PAGE, offset=page * PER_PAGE)
    await show(target, t(lang, "my_title", count=total), my_shipments_keyboard(shipments, page, pages, lang))


@router.callback_query(PageCB.filter(F.scope == "my"))
async def on_page(callback: CallbackQuery, callback_data: PageCB, state: FSMContext, session: AsyncSession,
                  user: User, lang: str) -> None:
    await callback.answer()
    await show_my_shipments(callback, state, session, user, lang, callback_data.page)
