"""AI-помощник на базе Gemini API с резервным режимом без ИИ.

Принципы:
- AI только извлекает данные из текста и отвечает на вопросы о сервисе.
- AI не подтверждает заявки, не называет цены и не придумывает статусы:
  цены считает backend по тарифам из БД, статусы берутся из БД.
- Любой ответ модели валидируется (Pydantic + справочники); всё, что не прошло
  проверку, отбрасывается.
- Если ключа нет или API недоступен, работает rule-based парсер и FAQ —
  основные функции бота не зависят от AI.
"""
from __future__ import annotations

import json
import logging
import re
from decimal import Decimal
from typing import Any, Literal

import aiohttp
from pydantic import BaseModel

from database.models import CargoCategory, TransportType
from i18n import t
from utils.catalog import CITIES, find_category, find_cities_in_text, find_city, find_transport
from utils.validators import InputError, parse_packages, parse_volume, parse_weight

logger = logging.getLogger(__name__)

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
MAX_INPUT_LENGTH = 1000

LANG_NAMES = {"ru": "Russian", "kk": "Kazakh", "en": "English"}

SYSTEM_PROMPT = """You are the AI assistant of "Qadam Logistics" — a Telegram bot that helps small and medium
businesses in Kazakhstan arrange international cargo shipments (main corridor: Shymkent, Kazakhstan — Tashkent,
Uzbekistan), get a preliminary cost estimate and track delivery stages.

What the bot can do (menu buttons): "Create shipment" (10-step form), "Calculate cost", "Track cargo"
(by tracking number like QDM-261106-7KX4P), "My shipments", "AI assistant", "About".
Delivery stages: request created -> awaiting confirmation -> confirmed -> cargo preparation -> accepted by carrier ->
in transit -> arrived at customs -> customs cleared -> arrived in destination city -> delivered (or cancelled).
Customs stages apply only to international routes. Statuses are updated manually by the Qadam operator.
Transport types: road ("road") and rail ("rail").
Supported cities: {cities}.
Cargo categories: clothing, electronics, food, construction, furniture, other.

STRICT RULES:
1. Never state, guess or estimate any price, tariff or amount of money. For cost questions tell the user to press
   "Calculate cost" — the system calculates it from tariffs.
2. Never invent shipment statuses, locations or delivery dates. Tell the user to use "Track cargo".
3. Never confirm, accept or promise a shipment. Only a Qadam operator confirms requests.
4. If the user describes cargo they want to send, set intent to "shipment" and extract only what is explicitly
   stated. Use null for anything not stated. Do not guess.
5. Answer in {language}. Plain text without markdown, at most 600 characters.

Return ONLY a JSON object of this exact shape:
{{"intent": "shipment" | "question",
  "answer": "<short reply to the user>",
  "shipment": {{"origin": <city name or null>, "destination": <city name or null>,
               "cargo_category": <one of clothing|electronics|food|construction|furniture|other or null>,
               "weight_kg": <number or null>, "volume_m3": <number or null>,
               "packages": <integer or null>, "transport_type": <"road"|"rail"|null>}}}}"""


class AIUnavailableError(Exception):
    pass


class ExtractedShipment(BaseModel):
    origin: str | None = None
    destination: str | None = None
    cargo_category: CargoCategory | None = None
    weight: Decimal | None = None
    volume: Decimal | None = None
    packages: int | None = None
    transport_type: TransportType | None = None

    def filled_fields(self) -> int:
        return sum(v is not None for v in self.model_dump().values())

    def is_empty(self) -> bool:
        return self.filled_fields() == 0

    def merge(self, other: ExtractedShipment) -> ExtractedShipment:
        """Заполняет пустые поля значениями из другого результата."""
        data = self.model_dump()
        for key, value in other.model_dump().items():
            if data.get(key) is None and value is not None:
                data[key] = value
        if data["origin"] and data["origin"] == data["destination"]:
            data["destination"] = None
        return ExtractedShipment(**data)

    def to_form_data(self) -> dict[str, Any]:
        """Данные в формате FSM-хранилища (строки/числа, JSON-совместимо)."""
        result: dict[str, Any] = {}
        if self.origin:
            result["origin"] = self.origin
        if self.destination:
            result["destination"] = self.destination
        if self.cargo_category:
            result["category"] = self.cargo_category.value
        if self.weight is not None:
            result["weight"] = str(self.weight)
        if self.volume is not None:
            result["volume"] = str(self.volume)
        if self.packages is not None:
            result["packages"] = self.packages
        if self.transport_type:
            result["transport"] = self.transport_type.value
        return result


class AssistantReply(BaseModel):
    intent: Literal["shipment", "question"]
    answer: str
    shipment: ExtractedShipment | None = None
    source: Literal["ai", "fallback"]


# ---------------------------------------------------------------- нормализация

def _safe(parser, value):
    if value is None or value == "":
        return None
    try:
        return parser(value)
    except (InputError, ValueError, TypeError):
        return None


def normalize_extracted(raw: dict[str, Any] | None) -> ExtractedShipment:
    """Проверяет данные от модели по справочникам и валидаторам — всё сомнительное отбрасывается."""
    raw = raw or {}
    origin = find_city(str(raw.get("origin") or "")) if raw.get("origin") else None
    destination = find_city(str(raw.get("destination") or "")) if raw.get("destination") else None
    if origin and origin == destination:
        destination = None
    return ExtractedShipment(
        origin=origin,
        destination=destination,
        cargo_category=find_category(str(raw["cargo_category"])) if raw.get("cargo_category") else None,
        weight=_safe(parse_weight, raw.get("weight_kg", raw.get("weight"))),
        volume=_safe(parse_volume, raw.get("volume_m3", raw.get("volume"))),
        packages=_safe(parse_packages, raw.get("packages")),
        transport_type=find_transport(str(raw["transport_type"])) if raw.get("transport_type") else None,
    )


_NUM = r"(\d+(?:[.,]\d+)?)"
_WEIGHT_KG_RE = re.compile(_NUM + r"\s*(?:кг|kg|килограмм\w*|кило\b)", re.IGNORECASE)
_WEIGHT_T_RE = re.compile(_NUM + r"\s*(?:т\b|тонн\w*|tons?\b|t\b)", re.IGNORECASE)
_VOLUME_RE = re.compile(_NUM + r"\s*(?:м3|м³|m3|m³|куб\w*|cbm\b)", re.IGNORECASE)
_PACKAGES_RE = re.compile(
    r"(\d+)\s*(?:коробк\w*|короб\w*|упаков\w*|мест\w*|ящик\w*|паллет\w*|паллет|мешк\w*|мешок|"
    r"box\w*|package\w*|pallet\w*|parcel\w*|pcs|шт\w*|қорап\w*|дана)",
    re.IGNORECASE,
)
_SHIPMENT_WORDS = ("отправ", "перевез", "доставить", "доставк", "груз", "send", "ship", "deliver",
                   "жібер", "тасымал", "жүк")


def rule_based_extract(text: str) -> ExtractedShipment:
    """Извлечение данных без ИИ (регулярные выражения + справочники)."""
    origin, destination = find_cities_in_text(text)
    weight = None
    if m := _WEIGHT_KG_RE.search(text):
        weight = _safe(parse_weight, m.group(1))
    elif m := _WEIGHT_T_RE.search(text):
        tons = _safe(parse_weight, m.group(1))
        weight = _safe(parse_weight, tons * 1000) if tons is not None else None
    volume = _safe(parse_volume, m.group(1)) if (m := _VOLUME_RE.search(text)) else None
    packages = _safe(parse_packages, m.group(1)) if (m := _PACKAGES_RE.search(text)) else None
    return ExtractedShipment(
        origin=origin,
        destination=destination,
        cargo_category=find_category(text),
        weight=weight,
        volume=volume,
        packages=packages,
        transport_type=find_transport(text),
    )


def looks_like_shipment(text: str, extracted: ExtractedShipment) -> bool:
    lowered = text.lower()
    has_cargo_data = any(v is not None for v in (extracted.weight, extracted.volume, extracted.packages))
    has_route = extracted.origin is not None or extracted.destination is not None
    return has_cargo_data or (has_route and any(w in lowered for w in _SHIPMENT_WORDS))


_FAQ_RULES: list[tuple[tuple[str, ...], str]] = [
    (("цен", "стоим", "сколько", "тариф", "price", "cost", "how much", "баға", "қанша"), "faq_price"),
    (("статус", "где ", "где мой", "отслед", "трек", "track", "where", "қайда", "бақыла"), "faq_tracking"),
    (("тамож", "customs", "кеден"), "faq_customs"),
    (("документ", "document", "құжат"), "faq_docs"),
    (("оформ", "заявк", "как отправ", "how to", "create", "рәсімде", "өтінім"), "faq_create"),
    (("срок", "долго", "дней", "how long", "time", "мерзім", "күн"), "faq_time"),
]


def fallback_answer(text: str, lang: str) -> str:
    lowered = text.lower()
    for words, key in _FAQ_RULES:
        if any(w in lowered for w in words):
            return t(lang, key)
    return t(lang, "faq_default")


_MONEY_RE = re.compile(r"\d[\d\s.,]*\s*(₸|тг\b|тенге|kzt|\$|usd|сум|sum\b|руб|eur|€)", re.IGNORECASE)


def sanitize_answer(answer: str, lang: str) -> str:
    """Защита: если модель всё-таки назвала сумму денег — заменяем ответ на стандартный."""
    answer = (answer or "").strip()
    if not answer:
        return t(lang, "faq_default")
    if _MONEY_RE.search(answer):
        logger.warning("AI answer contained a money amount — replaced with safe answer")
        return t(lang, "faq_price")
    return answer[:1000]


# ---------------------------------------------------------------- Gemini

class GeminiClient:
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash", timeout: float = 20.0) -> None:
        self.api_key = api_key
        self.model = model
        self.timeout = aiohttp.ClientTimeout(total=timeout)

    async def generate_json(self, system_prompt: str, user_text: str) -> dict[str, Any]:
        payload = {
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": user_text}]}],
            "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json", "maxOutputTokens": 1024},
        }
        headers = {"x-goog-api-key": self.api_key, "Content-Type": "application/json"}
        url = GEMINI_URL.format(model=self.model)
        try:
            async with aiohttp.ClientSession(timeout=self.timeout, trust_env=True) as http:
                async with http.post(url, json=payload, headers=headers) as response:
                    if response.status != 200:
                        body = (await response.text())[:300]
                        raise AIUnavailableError(f"Gemini HTTP {response.status}: {body}")
                    data = await response.json()
        except (aiohttp.ClientError, TimeoutError) as exc:
            raise AIUnavailableError(f"Gemini request failed: {exc!r}") from exc

        try:
            text = data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError) as exc:
            raise AIUnavailableError(f"Unexpected Gemini response: {str(data)[:300]}") from exc
        return parse_json_text(text)


def parse_json_text(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned)
    try:
        result = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise AIUnavailableError("Model returned invalid JSON") from exc
    if not isinstance(result, dict):
        raise AIUnavailableError("Model returned non-object JSON")
    return result


class AssistantService:
    def __init__(self, client: GeminiClient | None = None) -> None:
        self.client = client

    @property
    def ai_enabled(self) -> bool:
        return self.client is not None

    def _system_prompt(self, lang: str) -> str:
        cities = ", ".join(f"{c.names['en']} ({c.names['ru']})" for c in CITIES.values())
        return SYSTEM_PROMPT.format(cities=cities, language=LANG_NAMES.get(lang, "Russian"))

    async def handle(self, text: str, lang: str = "ru") -> AssistantReply:
        text = (text or "").strip()[:MAX_INPUT_LENGTH]
        rules = rule_based_extract(text)

        if self.client is not None:
            try:
                data = await self.client.generate_json(self._system_prompt(lang), text)
                extracted = normalize_extracted(data.get("shipment") if isinstance(data.get("shipment"), dict) else None)
                extracted = extracted.merge(rules)  # регулярки подстраховывают модель
                intent = "shipment" if data.get("intent") == "shipment" and not extracted.is_empty() else "question"
                if intent == "question" and looks_like_shipment(text, rules):
                    intent = "shipment"
                answer = sanitize_answer(str(data.get("answer") or ""), lang)
                return AssistantReply(
                    intent=intent, answer=answer,
                    shipment=extracted if intent == "shipment" else None, source="ai",
                )
            except AIUnavailableError as exc:
                logger.warning("AI unavailable, fallback mode: %s", exc)
            except Exception:  # noqa: BLE001 — AI не должен ронять бота ни при каких условиях
                logger.exception("Unexpected AI error, fallback mode")

        if looks_like_shipment(text, rules):
            return AssistantReply(intent="shipment", answer=t(lang, "ai_fallback_extracted"),
                                  shipment=rules, source="fallback")
        return AssistantReply(intent="question", answer=fallback_answer(text, lang), source="fallback")
