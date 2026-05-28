from __future__ import annotations

import asyncio
import logging

from aiogram import Bot

from bot.database import Database
from bot.formatters import format_amount, format_date
from bot.keyboards import paid_keyboard

logger = logging.getLogger(__name__)


async def reminder_loop(
    bot: Bot,
    db: Database,
    remind_days_before: int,
    interval_seconds: int = 3600,
) -> None:
    offsets = {remind_days_before, 1, 0}
    while True:
        await send_due_reminders(bot, db, offsets)
        await asyncio.sleep(interval_seconds)


async def send_due_reminders(bot: Bot, db: Database, offsets: set[int]) -> None:
    for item in await db.list_due_subscriptions(offsets):
        payment_date = item["next_payment"]
        offset = item["remind_offset"]
        if await db.was_reminder_sent(item["id"], payment_date, offset):
            continue

        if offset == 0:
            prefix = "Сегодня списание"
        elif offset == 1:
            prefix = "Завтра списание"
        else:
            prefix = f"Через {offset} дн. списание"

        try:
            await bot.send_message(
                item["user_id"],
                f"🔔 {prefix}\n"
                f"{item['name']} — {format_amount(item['amount_cents'])}\n"
                f"Дата: {format_date(payment_date)}",
                reply_markup=paid_keyboard(item["id"]),
            )
        except Exception:
            logger.exception("Failed to send reminder for subscription %s", item["id"])
            continue
        await db.mark_reminder_sent(item["id"], payment_date, offset)
