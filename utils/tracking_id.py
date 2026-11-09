"""Генерация Tracking ID вида QDM-261106-7KX4P.

QDM — префикс бренда, 261106 — дата создания (ГГММДД), 5 случайных символов
из алфавита без похожих символов (нет 0/O, 1/I/L). Используется
криптостойкий генератор secrets; уникальность дополнительно проверяется в БД.
"""
from __future__ import annotations

import re
import secrets
from datetime import date

PREFIX = "QDM"
ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"
RANDOM_PART_LENGTH = 5

TRACKING_RE = re.compile(rf"^{PREFIX}-\d{{6}}-[{ALPHABET}]{{{RANDOM_PART_LENGTH}}}$")


def generate_tracking_number(today: date | None = None) -> str:
    today = today or date.today()
    random_part = "".join(secrets.choice(ALPHABET) for _ in range(RANDOM_PART_LENGTH))
    return f"{PREFIX}-{today:%y%m%d}-{random_part}"


def normalize_tracking_number(raw: str) -> str:
    text = (raw or "").strip().upper().replace(" ", "").replace("_", "-")
    # Разрешаем ввод без дефисов: QDM2611067KX4P
    compact = text.replace("-", "")
    if len(compact) == len(PREFIX) + 6 + RANDOM_PART_LENGTH and compact.startswith(PREFIX):
        text = f"{compact[:3]}-{compact[3:9]}-{compact[9:]}"
    return text


def is_valid_tracking_number(value: str) -> bool:
    return bool(TRACKING_RE.match(value or ""))
