"""Мини-система локализации: ru / kk / en. Если ключа нет в языке — используется русский."""
from __future__ import annotations

import logging

from i18n.texts import TEXTS

logger = logging.getLogger(__name__)

DEFAULT_LANG = "ru"
LANGUAGES = {"ru": "🇷🇺 Русский", "kk": "🇰🇿 Қазақша", "en": "🇬🇧 English"}


def t(lang: str | None, key: str, **params: object) -> str:
    lang = lang if lang in TEXTS else DEFAULT_LANG
    template = TEXTS[lang].get(key) or TEXTS[DEFAULT_LANG].get(key)
    if template is None:
        logger.error("Missing i18n key: %s", key)
        return key
    if params:
        try:
            return template.format(**params)
        except (KeyError, IndexError, ValueError):
            logger.exception("Bad i18n params for key %s", key)
            return template
    return template


def all_translations(key: str) -> set[str]:
    """Все варианты текста (нужно для распознавания кнопок Reply-клавиатуры на любом языке)."""
    return {texts[key] for texts in TEXTS.values() if key in texts}
