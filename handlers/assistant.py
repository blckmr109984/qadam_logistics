"""AI-помощник: свободный текст → распознанная заявка → подтверждение пользователем.

AI ничего не подтверждает и не считает: данные переходят в обычную форму
оформления (с проверками), а цену считает pricing_service по тарифам из БД.
"""
from __future__ import annotations

import logging
import time
from html import escape

from aiogram import F, Router
from aiogram.enums import ChatAction
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User
from handlers.calculator import start_calculator
from handlers.common import show
from handlers.shipment import start_shipment
from i18n import t
from keyboards.inline import AssistantCB, home_keyboard
from keyboards.shipment import assistant_extracted_keyboard
from services.ai_service import MAX_INPUT_LENGTH, AssistantService
from states.shipment_states import AssistantForm
from utils.formatting import extracted_details

logger = logging.getLogger(__name__)
router = Router(name="assistant")

COOLDOWN_SECONDS = 2.0


async def start_assistant(target: Message | CallbackQuery, state: FSMContext, lang: str,
                          assistant: AssistantService) -> None:
    await state.clear()
    await state.set_state(AssistantForm.chatting)
    mode = t(lang, "ai_mode_ai" if assistant.ai_enabled else "ai_mode_fallback")
    await show(target, t(lang, "ai_intro", mode=mode), home_keyboard(lang))


@router.message(AssistantForm.chatting, F.text)
async def on_text(message: Message, state: FSMContext, lang: str, assistant: AssistantService) -> None:
    text = message.text.strip()
    if len(text) > MAX_INPUT_LENGTH:
        await message.answer(t(lang, "ai_too_long", max=MAX_INPUT_LENGTH))
        return
    data = await state.get_data()
    now = time.monotonic()
    if now - float(data.get("ai_ts", 0)) < COOLDOWN_SECONDS:
        await message.answer(t(lang, "ai_cooldown"))
        return
    await state.update_data(ai_ts=now)

    await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    reply = await assistant.handle(text, lang)
    logger.info("Assistant reply: user=%s intent=%s source=%s", message.from_user.id, reply.intent, reply.source)

    if reply.intent == "shipment" and reply.shipment and not reply.shipment.is_empty():
        form = reply.shipment.to_form_data()
        await state.update_data(ai_draft=form)
        can_calc = all(form.get(k) for k in ("origin", "destination", "weight", "volume"))
        body = (
            f"{t(lang, 'ai_extracted_title')}\n\n{extracted_details(form, lang)}\n\n"
            f"<i>{escape(reply.answer)}</i>\n\n{t(lang, 'ai_extracted_hint')}"
        )
        await message.answer(body, reply_markup=assistant_extracted_keyboard(lang, can_calc))
        return

    await message.answer(escape(reply.answer), reply_markup=home_keyboard(lang))


@router.message(AssistantForm.chatting)
async def on_non_text(message: Message, lang: str) -> None:
    await message.answer(t(lang, "ai_need_text"))


@router.callback_query(AssistantCB.filter())
async def on_action(callback: CallbackQuery, callback_data: AssistantCB, state: FSMContext,
                    session: AsyncSession, user: User, lang: str) -> None:
    await callback.answer()
    if callback_data.action == "manual":
        await start_shipment(callback, state, session, user, lang)
        return
    draft = (await state.get_data()).get("ai_draft")
    if not draft:
        await show(callback, t(lang, "ai_session_expired"), home_keyboard(lang))
        return
    if callback_data.action == "calc":
        await start_calculator(callback, state, session, lang, prefill=draft)
    else:
        await start_shipment(callback, state, session, user, lang, prefill=draft)
