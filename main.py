from __future__ import annotations

import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from dotenv import load_dotenv

from bot.database import Database
from bot.handlers import create_router
from bot.reminders import reminder_loop


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    load_dotenv()
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN не найден. Создай .env по примеру .env.example")

    remind_days_before = int(os.getenv("REMIND_DAYS_BEFORE", "3"))
    interval_seconds = int(os.getenv("REMINDER_INTERVAL_SECONDS", "3600"))

    db = Database("data/subscriptions.db")
    await db.init()

    bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dispatcher = Dispatcher()
    dispatcher.include_router(create_router(db))

    reminder_task = asyncio.create_task(
        reminder_loop(bot, db, remind_days_before, interval_seconds)
    )
    try:
        await dispatcher.start_polling(bot)
    finally:
        reminder_task.cancel()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
