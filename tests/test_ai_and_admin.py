import ast
from decimal import Decimal
from pathlib import Path

import pytest
from aiogram.types import Message

from config import Settings, _parse_admin_ids
from database.models import CargoCategory, TransportType
from i18n.texts import TEXTS
from services import admin_service
from services.ai_service import (
    AIUnavailableError, AssistantService, normalize_extracted, parse_json_text, rule_based_extract, sanitize_answer,
)
from utils.filters import AdminFilter

ROOT = Path(__file__).resolve().parent.parent


# 10. Проверка прав администратора
def test_admin_ids_parsing_and_check():
    assert _parse_admin_ids("123, 456;789, abc,") == frozenset({123, 456, 789})
    settings = Settings(bot_token="x", admin_ids=frozenset({123}))
    assert settings.is_admin(123)
    assert not settings.is_admin(999) and not settings.is_admin(None)


async def test_admin_filter():
    settings = Settings(bot_token="x", admin_ids=frozenset({123}))
    admin_msg = Message.model_validate({"message_id": 1, "date": 0, "chat": {"id": 123, "type": "private"},
                                        "from": {"id": 123, "is_bot": False, "first_name": "A"}, "text": "/admin"})
    user_msg = Message.model_validate({"message_id": 2, "date": 0, "chat": {"id": 5, "type": "private"},
                                       "from": {"id": 5, "is_bot": False, "first_name": "U"}, "text": "/admin"})
    assert await AdminFilter()(admin_msg, settings) is True
    assert await AdminFilter()(user_msg, settings) is False


async def test_admin_stats(session, user):
    from tests.test_shipments import make_payload
    from services.shipment_service import create_shipment
    from services.tracking_service import change_status
    from database.models import ShipmentStatus as S

    s1, _ = await create_shipment(session, user, make_payload())
    s2, _ = await create_shipment(session, user, make_payload())
    await change_status(session, s2.id, S.CANCELLED)
    stats = await admin_service.get_stats(session)
    assert (stats.users, stats.shipments, stats.pending, stats.active, stats.cancelled) == (1, 2, 1, 1, 1)
    assert await admin_service.count_shipments(session, "new") == 1


# AI: извлечение данных
def test_rule_based_extraction_example_from_spec():
    data = rule_based_extract("Мне нужно отправить 150 кг одежды из Шымкента в Ташкент, примерно 10 коробок")
    assert data.origin == "shymkent" and data.destination == "tashkent"
    assert data.cargo_category == CargoCategory.CLOTHING
    assert data.weight == Decimal("150.00") and data.packages == 10
    assert data.transport_type is None  # «одежды» не должно распознаваться как «ж/д»


def test_rule_based_extraction_kazakh_and_english():
    kk = rule_based_extract("Шымкенттен Ташкентке 2 тонна жиһаз, 3.5 м3")
    assert (kk.origin, kk.destination, kk.weight, kk.volume) == ("shymkent", "tashkent", Decimal("2000.00"), Decimal("3.500"))
    en = rule_based_extract("send 300 kg electronics to Almaty from Tashkent by train")
    assert (en.origin, en.destination, en.transport_type) == ("tashkent", "almaty", TransportType.RAIL)


def test_ai_output_is_validated():
    data = normalize_extracted({"origin": "Shymkent", "destination": "Mars", "cargo_category": "spaceships",
                                "weight_kg": -150, "volume_m3": "1.5", "packages": 2.5, "transport_type": "rail"})
    assert data.origin == "shymkent" and data.destination is None
    assert data.cargo_category is None and data.weight is None and data.packages is None
    assert data.volume == Decimal("1.500") and data.transport_type == TransportType.RAIL


def test_ai_cannot_state_prices():
    assert "Рассчитать стоимость" in sanitize_answer("Доставка будет стоить 50 000 тенге", "ru")
    assert sanitize_answer("Статус смотрите в разделе отслеживания", "ru").startswith("Статус")


def test_parse_json_text():
    assert parse_json_text('```json\n{"intent": "question"}\n```') == {"intent": "question"}
    with pytest.raises(AIUnavailableError):
        parse_json_text("not json")


class FakeGemini:
    def __init__(self, response=None, error=None):
        self.response, self.error, self.calls = response, error, 0

    async def generate_json(self, system_prompt, user_text):
        self.calls += 1
        if self.error:
            raise self.error
        return self.response


async def test_assistant_with_ai_response():
    client = FakeGemini({"intent": "shipment", "answer": "Заполнил форму",
                         "shipment": {"origin": "Shymkent", "destination": "Tashkent", "cargo_category": "clothing",
                                      "weight_kg": 150, "volume_m3": None, "packages": 10, "transport_type": None}})
    reply = await AssistantService(client).handle("150 кг одежды из Шымкента в Ташкент, 10 коробок", "ru")
    assert reply.source == "ai" and reply.intent == "shipment"
    assert reply.shipment.origin == "shymkent" and reply.shipment.packages == 10


async def test_assistant_falls_back_when_api_fails():
    client = FakeGemini(error=AIUnavailableError("HTTP 503"))
    reply = await AssistantService(client).handle("Отправить 150 кг одежды из Шымкента в Ташкент", "ru")
    assert client.calls == 1 and reply.source == "fallback" and reply.intent == "shipment"
    assert reply.shipment.weight == Decimal("150.00")
    question = await AssistantService(None).handle("Сколько стоит доставка?", "ru")
    assert question.intent == "question" and "Рассчитать стоимость" in question.answer


async def test_assistant_survives_unexpected_errors():
    reply = await AssistantService(FakeGemini(error=RuntimeError("boom"))).handle("где мой груз?", "en")
    assert reply.source == "fallback" and "Track cargo" in reply.answer


# Локализация: все ключи есть во всех языках, все ключи из кода существуют
def test_i18n_keys_complete():
    ru = set(TEXTS["ru"])
    for lang, texts in TEXTS.items():
        assert set(texts) == ru, f"{lang}: missing {ru - set(texts)}, extra {set(texts) - ru}"


def test_i18n_keys_used_in_code_exist():
    used: set[str] = set()
    for path in ROOT.rglob("*.py"):
        if "tests" in path.parts:
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if (isinstance(node, ast.Call) and getattr(node.func, "id", None) == "t" and len(node.args) >= 2
                    and isinstance(node.args[1], ast.Constant) and isinstance(node.args[1].value, str)):
                used.add(node.args[1].value)
    missing = used - set(TEXTS["ru"])
    assert not missing, missing


# Реальный HTTP-путь клиента Gemini — на локальном фейковом сервере
async def test_gemini_client_http_roundtrip(monkeypatch):
    import json as _json

    from aiohttp import web
    from aiohttp.test_utils import TestServer

    from services import ai_service

    monkeypatch.setenv("NO_PROXY", "127.0.0.1,localhost")
    seen: dict = {}

    async def generate(request: web.Request) -> web.Response:
        seen["key"] = request.headers.get("x-goog-api-key")
        seen["body"] = await request.json()
        if seen["key"] != "good":
            return web.json_response({"error": "bad key"}, status=403)
        payload = {"intent": "question", "answer": "Статус — в разделе «Отследить груз».", "shipment": None}
        return web.json_response({"candidates": [{"content": {"parts": [{"text": _json.dumps(payload)}]}}]})

    app = web.Application()
    app.router.add_post("/v1beta/models/{model}:generateContent", generate)
    server = TestServer(app)
    await server.start_server()
    try:
        monkeypatch.setattr(ai_service, "GEMINI_URL", f"http://{server.host}:{server.port}/v1beta/models/{{model}}:generateContent")
        ok = await AssistantService(ai_service.GeminiClient("good", "gemini-test", 5)).handle("где груз?", "ru")
        assert ok.source == "ai" and "Отследить груз" in ok.answer
        assert seen["body"]["generationConfig"]["responseMimeType"] == "application/json"
        assert "Never state" in seen["body"]["systemInstruction"]["parts"][0]["text"]

        bad = await AssistantService(ai_service.GeminiClient("bad", "gemini-test", 5)).handle("где груз?", "ru")
        assert bad.source == "fallback"  # 403 → резервный режим, бот продолжает работать
    finally:
        await server.close()


def test_i18n_placeholders_match_across_languages():
    import string

    def fields(template: str) -> set[str]:
        return {name for _, name, _, _ in string.Formatter().parse(template) if name}

    for key, ru_text in TEXTS["ru"].items():
        for lang in ("kk", "en"):
            assert fields(TEXTS[lang][key]) == fields(ru_text), f"{lang}.{key}"
