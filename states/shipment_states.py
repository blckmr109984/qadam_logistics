"""FSM-состояния пользовательских сценариев."""
from aiogram.fsm.state import State, StatesGroup


class ShipmentForm(StatesGroup):
    origin = State()
    destination = State()
    category = State()
    weight = State()
    volume = State()
    packages = State()
    transport = State()
    date = State()
    phone = State()
    confirm = State()


class CalcForm(StatesGroup):
    origin = State()
    destination = State()
    weight = State()
    volume = State()
    result = State()


class TrackingForm(StatesGroup):
    number = State()


class AssistantForm(StatesGroup):
    chatting = State()


class AdminTariffForm(StatesGroup):
    value = State()
