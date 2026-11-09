"""Справочники: города, категории, виды транспорта, статусы (эмодзи и поиск по тексту)."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from database.models import CargoCategory, ShipmentStatus, TransportType


@dataclass(frozen=True)
class City:
    code: str
    names: dict[str, str]
    country: str  # ISO-код страны: KZ, UZ, KG
    stems: tuple[str, ...] = field(default_factory=tuple)  # основы слова для распознавания в тексте

    def name(self, lang: str) -> str:
        return self.names.get(lang) or self.names["ru"]


CITIES: dict[str, City] = {
    c.code: c
    for c in (
        City("shymkent", {"ru": "Шымкент", "kk": "Шымкент", "en": "Shymkent"}, "KZ",
             ("шымкент", "чимкент", "shymkent", "chimkent")),
        City("tashkent", {"ru": "Ташкент", "kk": "Ташкент", "en": "Tashkent"}, "UZ",
             ("ташкент", "тошкент", "tashkent", "toshkent")),
        City("almaty", {"ru": "Алматы", "kk": "Алматы", "en": "Almaty"}, "KZ",
             ("алматы", "алмата", "алма-ат", "almaty", "alma-ata")),
        City("astana", {"ru": "Астана", "kk": "Астана", "en": "Astana"}, "KZ",
             ("астана", "астан", "astana")),
        City("samarkand", {"ru": "Самарканд", "kk": "Самарқанд", "en": "Samarkand"}, "UZ",
             ("самарканд", "самарқанд", "samarkand", "samarqand")),
        City("bishkek", {"ru": "Бишкек", "kk": "Бішкек", "en": "Bishkek"}, "KG",
             ("бишкек", "бішкек", "bishkek")),
    )
}

COUNTRY_FLAGS = {"KZ": "🇰🇿", "UZ": "🇺🇿", "KG": "🇰🇬"}

CATEGORY_EMOJI: dict[CargoCategory, str] = {
    CargoCategory.CLOTHING: "👕",
    CargoCategory.ELECTRONICS: "💻",
    CargoCategory.FOOD: "🍎",
    CargoCategory.CONSTRUCTION: "🧱",
    CargoCategory.FURNITURE: "🛋",
    CargoCategory.OTHER: "📦",
}

CATEGORY_KEYWORDS: dict[CargoCategory, tuple[str, ...]] = {
    CargoCategory.CLOTHING: ("одежд", "текстил", "обув", "футбол", "киім", "clothes", "clothing", "apparel", "textile"),
    CargoCategory.ELECTRONICS: ("электрон", "техник", "телефон", "смартфон", "ноутбук", "компьютер",
                                "электроника", "electronic", "laptop", "phone", "gadget"),
    CargoCategory.FOOD: ("продукт", "еда", "фрукт", "овощ", "азық", "тамақ", "food", "fruit", "grocer"),
    CargoCategory.CONSTRUCTION: ("стройматериал", "строительн", "цемент", "кирпич", "плитк", "құрылыс",
                                 "construction", "cement", "brick"),
    CargoCategory.FURNITURE: ("мебел", "диван", "шкаф", "стол", "стул", "жиһаз", "furniture", "sofa", "chair"),
}

TRANSPORT_EMOJI: dict[TransportType, str] = {
    TransportType.ROAD: "🚛",
    TransportType.RAIL: "🚂",
}

TRANSPORT_KEYWORDS: dict[TransportType, tuple[str, ...]] = {
    # Регулярные выражения: совпадение только с начала слова («одежды» не должно давать «жд»)
    TransportType.ROAD: (r"авто", r"машин", r"фур", r"грузовик", r"truck", r"road\b", r"көлік"),
    TransportType.RAIL: (r"жд\b", r"ж/д", r"ж\.д", r"поезд", r"вагон", r"железн", r"rail", r"train",
                         r"темір\s*жол", r"пойыз"),
}

STATUS_EMOJI: dict[ShipmentStatus, str] = {
    ShipmentStatus.CREATED: "📝",
    ShipmentStatus.PENDING: "⏳",
    ShipmentStatus.CONFIRMED: "✅",
    ShipmentStatus.PREPARING: "📦",
    ShipmentStatus.PICKED_UP: "🤝",
    ShipmentStatus.IN_TRANSIT: "🚚",
    ShipmentStatus.AT_CUSTOMS: "🛃",
    ShipmentStatus.CUSTOMS_CLEARED: "📑",
    ShipmentStatus.ARRIVED: "🏙",
    ShipmentStatus.DELIVERED: "🎉",
    ShipmentStatus.CANCELLED: "❌",
}


def city_name(code: str, lang: str = "ru") -> str:
    city = CITIES.get(code)
    return city.name(lang) if city else code


def city_label(code: str, lang: str = "ru") -> str:
    city = CITIES.get(code)
    if not city:
        return code
    return f"{COUNTRY_FLAGS.get(city.country, '')} {city.name(lang)}".strip()


def is_international(origin: str, destination: str) -> bool:
    a, b = CITIES.get(origin), CITIES.get(destination)
    if not a or not b:
        return True  # неизвестный город — безопаснее считать, что таможня возможна
    return a.country != b.country


def find_city(name: str | None) -> str | None:
    """Находит код города по названию на любом языке ('Шымкента' -> 'shymkent')."""
    if not name:
        return None
    text = name.strip().lower()
    if text in CITIES:
        return text
    for city in CITIES.values():
        if any(stem in text for stem in city.stems):
            return city.code
    return None


_ORIGIN_PREPOSITIONS = {"из", "от", "с", "со", "from"}
_DEST_PREPOSITIONS = {"в", "во", "до", "на", "to", "into"}
_ORIGIN_SUFFIXES = ("тен", "тан", "нан", "нен", "дан", "ден")   # каз.: Шымкенттен
_DEST_SUFFIXES = ("ке", "ка", "ға", "ге", "қа")             # каз.: Ташкентке


def find_cities_in_text(text: str) -> tuple[str | None, str | None]:
    """Определяет (откуда, куда) по свободному тексту с учётом предлогов и казахских окончаний."""
    lowered = text.lower()
    mentions: list[tuple[int, str, str | None]] = []  # (позиция, код, роль)
    for city in CITIES.values():
        for stem in city.stems:
            for match in re.finditer(re.escape(stem) + r"[\w-]*", lowered):
                ending = match.group(0)[len(stem):]  # окончание после основы слова
                before = lowered[: match.start()].split()
                prev = before[-1] if before else ""
                role: str | None = None
                if prev in _ORIGIN_PREPOSITIONS or ending.endswith(_ORIGIN_SUFFIXES):
                    role = "origin"
                elif prev in _DEST_PREPOSITIONS or ending.endswith(_DEST_SUFFIXES):
                    role = "destination"
                mentions.append((match.start(), city.code, role))
                break  # одного совпадения по городу достаточно
    mentions.sort()

    origin = next((code for _, code, role in mentions if role == "origin"), None)
    destination = next((code for _, code, role in mentions if role == "destination" and code != origin), None)
    for _, code, _role in mentions:  # недостающие роли заполняем по порядку упоминания
        if code in (origin, destination):
            continue
        if origin is None:
            origin = code
        elif destination is None:
            destination = code
    return origin, destination


def find_category(text: str | None) -> CargoCategory | None:
    if not text:
        return None
    lowered = text.strip().lower()
    try:
        return CargoCategory(lowered)
    except ValueError:
        pass
    for category, words in CATEGORY_KEYWORDS.items():
        if any(re.search(r"(?<!\w)" + re.escape(w), lowered) for w in words):
            return category
    return None


def find_transport(text: str | None) -> TransportType | None:
    if not text:
        return None
    lowered = text.strip().lower()
    try:
        return TransportType(lowered)
    except ValueError:
        pass
    for transport, patterns in TRANSPORT_KEYWORDS.items():
        if any(re.search(r"(?<!\w)" + pattern, lowered) for pattern in patterns):
            return transport
    return None
