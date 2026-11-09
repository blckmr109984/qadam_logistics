"""Конфигурация приложения.

Все секреты читаются из переменных окружения (файл .env), в исходном коде их нет.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR.parent / ".env", override=True)


def _parse_admin_ids(raw: str | None) -> frozenset[int]:
    """'123, 456' -> {123, 456}. Некорректные значения игнорируются."""
    if not raw:
        return frozenset()
    ids: set[int] = set()
    for part in raw.replace(";", ",").split(","):
        part = part.strip()
        if part.lstrip("-").isdigit():
            ids.add(int(part))
    return frozenset(ids)


def _parse_bool(raw: str | None, default: bool) -> bool:
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on", "y"}


class Settings(BaseModel):
    bot_token: str = ""
    admin_ids: frozenset[int] = frozenset()
    database_url: str = f"sqlite+aiosqlite:///{BASE_DIR / 'qadam.db'}"
    db_auto_create: bool = True

    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3.5-flash"
    gemini_timeout: float = Field(default=20.0, gt=0, le=120)

    log_level: str = "INFO"
    tz_offset_hours: int = Field(default=5, ge=-12, le=14)  # Казахстан/Узбекистан: UTC+5
    currency: str = "₸"

    @property
    def ai_enabled(self) -> bool:
        return bool(self.gemini_api_key)

    def is_admin(self, telegram_id: int | None) -> bool:
        return telegram_id is not None and telegram_id in self.admin_ids


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        bot_token=os.getenv("BOT_TOKEN", "").strip(),
        admin_ids=_parse_admin_ids(os.getenv("ADMIN_IDS")),
        database_url=os.getenv("DATABASE_URL") or Settings.model_fields["database_url"].default,
        db_auto_create=_parse_bool(os.getenv("DB_AUTO_CREATE"), True),
        gemini_api_key=(os.getenv("GEMINI_API_KEY") or "").strip() or None,
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip(),
        gemini_timeout=float(os.getenv("GEMINI_TIMEOUT", "20")),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        tz_offset_hours=int(os.getenv("TZ_OFFSET_HOURS", "5")),
        currency=os.getenv("CURRENCY", "₸"),
    )
