"""Проверка пользовательского ввода.

Ошибки возвращаются как InputError с ключом текста (i18n), чтобы
сообщение об ошибке показывалось на языке пользователя.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation

MAX_WEIGHT_KG = Decimal("60000")   # ограничение MVP (ж/д вагон)
MAX_VOLUME_M3 = Decimal("150")
MIN_VOLUME_M3 = Decimal("0.001")
MAX_PACKAGES = 10_000
MAX_DAYS_AHEAD = 180


class InputError(ValueError):
    def __init__(self, key: str, **params: object) -> None:
        super().__init__(key)
        self.key = key
        self.params = params


_UNIT_RE = re.compile(r"(кг|kg|килограмм\w*|м3|м³|m3|m³|куб\w*|шт\.?|pcs)$", re.IGNORECASE)


def parse_decimal(raw: str | int | float | Decimal) -> Decimal:
    if isinstance(raw, Decimal):
        value = raw
    elif isinstance(raw, (int, float)):
        value = Decimal(str(raw))
    else:
        text = str(raw).strip().lower().replace(" ", "").replace(" ", "").replace(",", ".")
        text = _UNIT_RE.sub("", text)
        if not text or not re.fullmatch(r"-?\d+(\.\d+)?", text):
            raise InputError("err_number")
        try:
            value = Decimal(text)
        except InvalidOperation as exc:  # pragma: no cover - защищено регуляркой
            raise InputError("err_number") from exc
    if not value.is_finite():
        raise InputError("err_number")
    return value


def parse_weight(raw: str | int | float | Decimal) -> Decimal:
    value = parse_decimal(raw)
    if value <= 0:
        raise InputError("err_positive")
    if value > MAX_WEIGHT_KG:
        raise InputError("err_weight_max", max=int(MAX_WEIGHT_KG))
    return value.quantize(Decimal("0.01"))


def parse_volume(raw: str | int | float | Decimal) -> Decimal:
    value = parse_decimal(raw)
    if value <= 0:
        raise InputError("err_positive")
    if value < MIN_VOLUME_M3:
        raise InputError("err_volume_min")
    if value > MAX_VOLUME_M3:
        raise InputError("err_volume_max", max=int(MAX_VOLUME_M3))
    return value.quantize(Decimal("0.001"))


def parse_packages(raw: str | int) -> int:
    value = parse_decimal(raw)
    if value != value.to_integral_value():
        raise InputError("err_packages")
    count = int(value)
    if count <= 0 or count > MAX_PACKAGES:
        raise InputError("err_packages")
    return count


def parse_price(raw: str | int | float | Decimal) -> Decimal:
    """Цена в тарифе: неотрицательное число до 100 млн."""
    value = parse_decimal(raw)
    if value < 0:
        raise InputError("err_positive")
    if value > Decimal("100000000"):
        raise InputError("err_number")
    return value.quantize(Decimal("0.01"))


def normalize_phone(raw: str) -> str:
    """Приводит номер к формату E.164: '8 701 123 45 67' -> '+77011234567'."""
    text = re.sub(r"[\s\-()]", "", raw or "")
    if text.startswith("00"):
        text = "+" + text[2:]
    if re.fullmatch(r"8\d{10}", text):  # казахстанский формат 8XXXXXXXXXX
        text = "+7" + text[1:]
    if not text.startswith("+") and re.fullmatch(r"\d{10,15}", text):
        text = "+" + text
    if not re.fullmatch(r"\+\d{10,15}", text):
        raise InputError("err_phone")
    return text


_DATE_FORMATS = ("%d.%m.%Y", "%d.%m.%y", "%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y")


def parse_date(raw: str, today: date) -> date:
    text = (raw or "").strip()
    parsed: date | None = None
    for fmt in _DATE_FORMATS:
        try:
            parsed = datetime.strptime(text, fmt).date()
            break
        except ValueError:
            continue
    if parsed is None and re.fullmatch(r"\d{1,2}\.\d{1,2}", text):  # 25.11 — текущий/следующий год
        day, month = map(int, text.split("."))
        try:
            parsed = date(today.year, month, day)
            if parsed < today:
                parsed = date(today.year + 1, month, day)
        except ValueError:
            parsed = None
    if parsed is None:
        raise InputError("err_date_format")
    validate_date(parsed, today)
    return parsed


def validate_date(value: date, today: date) -> date:
    if value < today:
        raise InputError("err_date_past")
    if value > today + timedelta(days=MAX_DAYS_AHEAD):
        raise InputError("err_date_far", days=MAX_DAYS_AHEAD)
    return value
