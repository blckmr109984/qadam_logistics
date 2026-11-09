"""Сквозной сценарий через настоящий диспетчер aiogram.

Telegram API подменён фейковой сессией, которая запоминает все исходящие
запросы. Проверяется полный путь: /start → оформление заявки за 10 шагов →
уведомление админу → подтверждение и смена статуса админом → уведомление
клиенту → защита от чужого доступа и от не-админа.
"""
from __future__ import annotations

import itertools
from datetime import datetime
from typing import Any

import pytest
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.base import BaseSession
from aiogram.methods import (
    AnswerCallbackQuery, EditMessageReplyMarkup, EditMessageText, SendChatAction, SendMessage, TelegramMethod,
)
from aiogram.types import CallbackQuery, Chat, Contact, InlineKeyboardMarkup, Message, Update, User as TgUser
from sqlalchemy import select

from app import create_dispatcher
from config import Settings
from database.models import Shipment, ShipmentStatus
from services.ai_service import AssistantService

CLIENT_ID, ADMIN_ID, STRANGER_ID = 1001, 9000, 3003


class FakeSession(BaseSession):
    def __init__(self) -> None:
        super().__init__()
        self.requests: list[TelegramMethod] = []
        self._ids = itertools.count(500)

    async def close(self) -> None:
        pass

    async def stream_content(self, *args, **kwargs):  # pragma: no cover
        yield b""

    async def make_request(self, bot: Bot, method: TelegramMethod, timeout: int | None = None) -> Any:
        self.requests.append(method)
        if isinstance(method, (SendMessage, EditMessageText)):
            markup = method.reply_markup if isinstance(method.reply_markup, InlineKeyboardMarkup) else None
            message_id = method.message_id if isinstance(method, EditMessageText) else next(self._ids)
            return Message(message_id=message_id, date=datetime.now(), text=method.text,
                           chat=Chat(id=method.chat_id, type="private"), reply_markup=markup)
        if isinstance(method, (AnswerCallbackQuery, SendChatAction, EditMessageReplyMarkup)):
            return True
        return True

    # --- помощники для проверок
    def sent_to(self, chat_id: int) -> list[SendMessage | EditMessageText]:
        return [r for r in self.requests if isinstance(r, (SendMessage, EditMessageText)) and r.chat_id == chat_id]

    def last_to(self, chat_id: int) -> SendMessage | EditMessageText:
        return self.sent_to(chat_id)[-1]

    def alerts(self) -> list[str]:
        return [r.text or "" for r in self.requests if isinstance(r, AnswerCallbackQuery)]


class Harness:
    def __init__(self, dp, bot: Bot, session: FakeSession) -> None:
        self.dp, self.bot, self.session = dp, bot, session
        self._update_ids = itertools.count(1)
        self._msg_ids = itertools.count(1)
        self._cb_ids = itertools.count(1)

    def _user(self, uid: int) -> TgUser:
        return TgUser(id=uid, is_bot=False, first_name=f"User{uid}", username=f"user{uid}")

    async def text(self, uid: int, text: str | None = None, contact: Contact | None = None) -> None:
        message = Message(message_id=next(self._msg_ids), date=datetime.now(), chat=Chat(id=uid, type="private"),
                          from_user=self._user(uid), text=text, contact=contact)
        await self.dp.feed_update(self.bot, Update(update_id=next(self._update_ids), message=message))

    async def click(self, uid: int, data: str, message: SendMessage | EditMessageText | None = None) -> None:
        source = message or self.session.last_to(uid)
        msg = Message(message_id=getattr(source, "message_id", None) or 1, date=datetime.now(),
                      chat=Chat(id=uid, type="private"), from_user=TgUser(id=1, is_bot=True, first_name="Bot"),
                      text=source.text)
        cb = CallbackQuery(id=str(next(self._cb_ids)), from_user=self._user(uid), chat_instance="ci",
                           message=msg, data=data)
        await self.dp.feed_update(self.bot, Update(update_id=next(self._update_ids), callback_query=cb))


def buttons(method) -> list[tuple[str, str]]:
    markup = method.reply_markup
    if not isinstance(markup, InlineKeyboardMarkup):
        return []
    return [(b.text, b.callback_data) for row in markup.inline_keyboard for b in row]


def button(method, startswith: str) -> str:
    for _text, data in buttons(method):
        if data and data.startswith(startswith):
            return data
    raise AssertionError(f"No button {startswith!r} in {buttons(method)}")


@pytest.fixture
async def harness(session_maker):
    settings = Settings(bot_token="42:TEST", admin_ids=frozenset({ADMIN_ID}))
    fake = FakeSession()
    bot = Bot("42:TEST", session=fake, default=DefaultBotProperties(parse_mode="HTML"))
    dp = create_dispatcher(settings, session_maker, AssistantService(None), debounce_window=0)
    h = Harness(dp, bot, fake)
    h.session_maker = session_maker
    return h


async def test_full_user_and_admin_scenario(harness: Harness):
    h, s = harness, harness.session

    # /start: приветствие + выбор языка, пользователь сохранён
    await h.text(CLIENT_ID, "/start")
    assert "Qadam Logistics" in s.sent_to(CLIENT_ID)[0].text
    await h.click(CLIENT_ID, "lang:en")
    assert "Main menu" in s.last_to(CLIENT_ID).text

    # Оформление поставки (английский интерфейс)
    await h.text(CLIENT_ID, "🚚 Create shipment")
    assert "step 1/10" in s.last_to(CLIENT_ID).text
    await h.click(CLIENT_ID, "city:o:shymkent")
    await h.click(CLIENT_ID, "city:d:tashkent")
    assert "step 3/10" in s.last_to(CLIENT_ID).text
    await h.click(CLIENT_ID, "cat:clothing")
    await h.text(CLIENT_ID, "-5")  # отрицательный вес отклоняется
    assert "greater than zero" in s.last_to(CLIENT_ID).text
    await h.text(CLIENT_ID, "150")
    await h.text(CLIENT_ID, "1.2")
    await h.text(CLIENT_ID, "10")
    assert "step 7/10" in s.last_to(CLIENT_ID).text
    await h.click(CLIENT_ID, "tr:road")
    await h.click(CLIENT_ID, "dt:1")
    assert "step 9/10" in s.last_to(CLIENT_ID).text
    await h.text(CLIENT_ID, contact=Contact(phone_number="77011234567", first_name="C", user_id=CLIENT_ID))
    summary = s.last_to(CLIENT_ID)
    assert "step 10/10" in summary.text and "28 520" in summary.text and "TEST tariffs" in summary.text

    await h.click(CLIENT_ID, "cf:yes", summary)
    created = s.last_to(CLIENT_ID)
    assert "Request submitted" in created.text

    async with h.session_maker() as db:
        shipment = (await db.scalars(select(Shipment))).one()
    assert shipment.status == ShipmentStatus.PENDING and shipment.contact_phone == "+77011234567"
    assert shipment.tracking_number in created.text

    # Повторное нажатие «Подтвердить» не создаёт дубликат
    await h.click(CLIENT_ID, "cf:yes", summary)
    async with h.session_maker() as db:
        assert len((await db.scalars(select(Shipment))).all()) == 1

    # Администратор получил заявку с кнопками
    admin_note = s.last_to(ADMIN_ID)
    assert "Новая заявка" in admin_note.text and shipment.tracking_number in admin_note.text

    # Отслеживание по номеру
    await h.text(CLIENT_ID, "📦 Track cargo")
    await h.text(CLIENT_ID, shipment.tracking_number.lower())
    card = s.last_to(CLIENT_ID)
    assert "Awaiting confirmation" in card.text and "Delivery stages" in card.text

    # Чужой пользователь не видит поставку ни по номеру, ни по кнопке
    await h.text(STRANGER_ID, f"/track {shipment.tracking_number}")
    assert "not found" in s.last_to(STRANGER_ID).text or "не найдена" in s.last_to(STRANGER_ID).text
    await h.click(STRANGER_ID, f"sh:open:{shipment.id}", s.last_to(STRANGER_ID))
    assert "⛔" in s.alerts()[-1]

    # Не-админ не может открыть панель и нажать админскую кнопку
    await h.text(STRANGER_ID, "/admin")
    assert "⛔" in s.last_to(STRANGER_ID).text
    await h.click(STRANGER_ID, f"adm:confirm:{shipment.id}:0::pending", s.last_to(STRANGER_ID))
    async with h.session_maker() as db:
        assert (await db.get(Shipment, shipment.id)).status == ShipmentStatus.PENDING

    # Админ подтверждает заявку → клиент получает уведомление
    before = len(s.sent_to(CLIENT_ID))
    await h.click(ADMIN_ID, button(admin_note, "adm:confirm"), admin_note)
    note = s.sent_to(CLIENT_ID)[before]
    assert "Status update" in note.text and "Confirmed" in note.text
    assert "Клиент уведомлён" in s.last_to(ADMIN_ID).text

    # Админ меняет статус через меню: «Изменить статус» → выбор → подтверждение
    card_admin = s.last_to(ADMIN_ID)
    await h.click(ADMIN_ID, button(card_admin, "adm:status"), card_admin)
    choice = s.last_to(ADMIN_ID)
    await h.click(ADMIN_ID, button(choice, "adm:setst"), choice)
    confirm = s.last_to(ADMIN_ID)
    await h.click(ADMIN_ID, button(confirm, "adm:setok"), confirm)
    assert "Cargo preparation" in s.last_to(CLIENT_ID).text
    # Устаревшая кнопка подтверждения статуса не применяется повторно
    await h.click(ADMIN_ID, button(confirm, "adm:setok"), confirm)
    assert "уже был изменён" in s.alerts()[-1]

    async with h.session_maker() as db:
        assert (await db.get(Shipment, shipment.id)).status == ShipmentStatus.PREPARING

    # Статистика и тарифы в админке
    await h.text(ADMIN_ID, "/admin")
    panel = s.last_to(ADMIN_ID)
    await h.click(ADMIN_ID, button(panel, "adm:stats"), panel)
    assert "Всего поставок: <b>1</b>" in s.last_to(ADMIN_ID).text
    await h.click(ADMIN_ID, button(panel, "adm:tariffs"), panel)
    tariffs_msg = s.last_to(ADMIN_ID)
    await h.click(ADMIN_ID, button(tariffs_msg, "adm:tariff:"), tariffs_msg)
    tariff_msg = s.last_to(ADMIN_ID)
    await h.click(ADMIN_ID, button(tariff_msg, "adm:tfield"), tariff_msg)
    await h.text(ADMIN_ID, "-100")
    assert "⚠️" in s.last_to(ADMIN_ID).text
    await h.text(ADMIN_ID, "20000")
    assert "Тариф обновлён" in s.last_to(ADMIN_ID).text and "20 000" in s.last_to(ADMIN_ID).text


async def test_menu_button_works_in_the_middle_of_form(harness: Harness):
    h, s = harness, harness.session
    await h.text(CLIENT_ID, "/start")
    await h.text(CLIENT_ID, "🚚 Создать поставку")
    await h.click(CLIENT_ID, "city:o:shymkent")
    await h.text(CLIENT_ID, "📋 Мои поставки")  # выход из сценария кнопкой меню
    assert "пока нет поставок" in s.last_to(CLIENT_ID).text
    await h.text(CLIENT_ID, "150")  # состояние сброшено — число уже не воспринимается как вес
    assert "Не понял" in s.last_to(CLIENT_ID).text


async def test_assistant_prefills_form_and_calculator(harness: Harness):
    h, s = harness, harness.session
    await h.text(CLIENT_ID, "/start")
    await h.text(CLIENT_ID, "🤖 AI-помощник")
    assert "базовый" in s.last_to(CLIENT_ID).text  # без ключа — резервный режим
    await h.text(CLIENT_ID, "Мне нужно отправить 150 кг одежды из Шымкента в Ташкент, примерно 10 коробок")
    extracted = s.last_to(CLIENT_ID)
    assert "Распознанная заявка" in extracted.text and "150 кг" in extracted.text
    await h.click(CLIENT_ID, "ai:fill", extracted)
    # Маршрут, категория, вес и упаковки заполнены — бот сразу спрашивает объём (шаг 5)
    assert "шаг 5/10" in s.last_to(CLIENT_ID).text
    await h.text(CLIENT_ID, "1.2")
    assert "шаг 7/10" in s.last_to(CLIENT_ID).text

    # Калькулятор: сравнение двух видов транспорта, затем переход к оформлению
    await h.text(CLIENT_ID, "💰 Рассчитать стоимость")
    for step in ("city:o:shymkent", "city:d:tashkent"):
        await h.click(CLIENT_ID, step)
    await h.text(CLIENT_ID, "150")
    await h.text(CLIENT_ID, "1.2")
    result = s.last_to(CLIENT_ID)
    assert "Автомобильный" in result.text and "Железнодорожный" in result.text and "ТЕСТОВЫМ" in result.text
    await h.click(CLIENT_ID, button(result, "calc:order"), result)
    assert "шаг 3/10" in s.last_to(CLIENT_ID).text  # осталось выбрать категорию
