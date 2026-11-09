"""Точка входа: python bot.py"""
from __future__ import annotations

import asyncio
import logging
import sys
from logging.handlers import RotatingFileHandler

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramNetworkError, TelegramUnauthorizedError
from aiogram.types import BotCommand

from app import build_assistant, create_dispatcher
from config import BASE_DIR, get_settings
from database.engine import create_engine, create_session_maker, init_models
from database.seed import seed_demo_data


def setup_logging(level: str) -> None:
    log_dir = BASE_DIR / "logs"
    log_dir.mkdir(exist_ok=True)
    fmt = logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(fmt)
    file_handler = RotatingFileHandler(log_dir / "bot.log", maxBytes=5_000_000, backupCount=3, encoding="utf-8")
    file_handler.setFormatter(fmt)
    logging.basicConfig(level=level, handlers=[console, file_handler])
    logging.getLogger("aiogram.event").setLevel(logging.WARNING)


async def main() -> None:
    settings = get_settings()
    setup_logging(settings.log_level)
    log = logging.getLogger("qadam")

    if not settings.bot_token:
        log.critical("BOT_TOKEN не задан. Скопируйте .env.example в .env и укажите токен от @BotFather.")
        raise SystemExit(1) from None
    if not settings.admin_ids:
        log.warning("ADMIN_IDS пуст — административная панель будет недоступна никому.")

    engine = create_engine(settings.database_url)
    session_maker = create_session_maker(engine)
    if settings.db_auto_create:
        await init_models(engine)
    async with session_maker() as session:
        await seed_demo_data(session)

    bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = create_dispatcher(settings, session_maker, build_assistant(settings))

    try:
        me = await bot.get_me()
        await bot.set_my_commands([
            BotCommand(command="start", description="Начать / Бастау / Start"),
            BotCommand(command="menu", description="Главное меню"),
            BotCommand(command="track", description="Отследить груз"),
            BotCommand(command="cancel", description="Отменить действие"),
            BotCommand(command="language", description="Язык / Тіл / Language"),
            BotCommand(command="help", description="Помощь"),
        ])
    except TelegramUnauthorizedError:
        log.critical("Telegram отклонил BOT_TOKEN. Проверьте токен в .env (получите новый у @BotFather).")
        await bot.session.close()
        await engine.dispose()
        raise SystemExit(1) from None
    except TelegramNetworkError as exc:
        log.critical("Нет связи с api.telegram.org: %s. Проверьте интернет/прокси.", exc)
        await bot.session.close()
        await engine.dispose()
        raise SystemExit(1) from None

    log.info("Qadam Logistics bot started as @%s (admins: %s)", me.username, len(settings.admin_ids))
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()
        await engine.dispose()
        log.info("Bot stopped, DB connections closed")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit) as exc:
        if isinstance(exc, SystemExit) and exc.code not in (0, None):
            raise
