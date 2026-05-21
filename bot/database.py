from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import aiosqlite


class Database:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    async def init(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.path) as db:
            await db.execute("PRAGMA foreign_keys = ON")
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    amount_cents INTEGER NOT NULL,
                    period TEXT NOT NULL CHECK(period IN ('weekly', 'monthly', 'yearly')),
                    next_payment TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS reminders_sent (
                    subscription_id INTEGER NOT NULL,
                    payment_date TEXT NOT NULL,
                    remind_offset INTEGER NOT NULL,
                    sent_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (subscription_id, payment_date, remind_offset),
                    FOREIGN KEY (subscription_id) REFERENCES subscriptions(id) ON DELETE CASCADE
                )
                """
            )
            await db.commit()

    async def create_subscription(
        self,
        user_id: int,
        name: str,
        amount_cents: int,
        period: str,
        next_payment: date,
    ) -> int:
        async with self._connect() as db:
            cursor = await db.execute(
                """
                INSERT INTO subscriptions
                    (user_id, name, amount_cents, period, next_payment)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, name, amount_cents, period, next_payment.isoformat()),
            )
            await db.commit()
            return int(cursor.lastrowid)

    async def list_subscriptions(self, user_id: int) -> list[dict[str, Any]]:
        async with self._connect() as db:
            cursor = await db.execute(
                """
                SELECT id, user_id, name, amount_cents, period, next_payment
                FROM subscriptions
                WHERE user_id = ?
                ORDER BY next_payment ASC, name ASC
                """,
                (user_id,),
            )
            rows = await cursor.fetchall()
            return [self._row_to_dict(row) for row in rows]

    async def get_subscription(
        self, user_id: int, subscription_id: int
    ) -> dict[str, Any] | None:
        async with self._connect() as db:
            cursor = await db.execute(
                """
                SELECT id, user_id, name, amount_cents, period, next_payment
                FROM subscriptions
                WHERE user_id = ? AND id = ?
                """,
                (user_id, subscription_id),
            )
            row = await cursor.fetchone()
            return self._row_to_dict(row) if row else None

    async def update_next_payment(
        self, user_id: int, subscription_id: int, next_payment: date
    ) -> dict[str, Any] | None:
        async with self._connect() as db:
            await db.execute(
                """
                UPDATE subscriptions
                SET next_payment = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND id = ?
                """,
                (next_payment.isoformat(), user_id, subscription_id),
            )
            await db.commit()
        return await self.get_subscription(user_id, subscription_id)

    async def delete_subscription(self, user_id: int, subscription_id: int) -> bool:
        async with self._connect() as db:
            cursor = await db.execute(
                "DELETE FROM subscriptions WHERE user_id = ? AND id = ?",
                (user_id, subscription_id),
            )
            await db.commit()
            return cursor.rowcount > 0

    async def list_due_subscriptions(self, offsets: set[int]) -> list[dict[str, Any]]:
        today = date.today()
        targets = {(today.toordinal() + offset): offset for offset in offsets}
        min_date = date.fromordinal(min(targets)).isoformat()
        max_date = date.fromordinal(max(targets)).isoformat()
        async with self._connect() as db:
            cursor = await db.execute(
                """
                SELECT id, user_id, name, amount_cents, period, next_payment
                FROM subscriptions
                WHERE next_payment BETWEEN ? AND ?
                ORDER BY next_payment ASC
                """,
                (min_date, max_date),
            )
            rows = await cursor.fetchall()
        result = []
        for row in rows:
            item = self._row_to_dict(row)
            offset = (item["next_payment"] - today).days
            if offset in offsets:
                item["remind_offset"] = offset
                result.append(item)
        return result

    async def was_reminder_sent(
        self, subscription_id: int, payment_date: date, remind_offset: int
    ) -> bool:
        async with self._connect() as db:
            cursor = await db.execute(
                """
                SELECT 1
                FROM reminders_sent
                WHERE subscription_id = ? AND payment_date = ? AND remind_offset = ?
                """,
                (subscription_id, payment_date.isoformat(), remind_offset),
            )
            return await cursor.fetchone() is not None

    async def mark_reminder_sent(
        self, subscription_id: int, payment_date: date, remind_offset: int
    ) -> None:
        async with self._connect() as db:
            await db.execute(
                """
                INSERT OR IGNORE INTO reminders_sent
                    (subscription_id, payment_date, remind_offset)
                VALUES (?, ?, ?)
                """,
                (subscription_id, payment_date.isoformat(), remind_offset),
            )
            await db.commit()

    async def clear_reminders_for_subscription(self, subscription_id: int) -> None:
        async with self._connect() as db:
            await db.execute(
                "DELETE FROM reminders_sent WHERE subscription_id = ?",
                (subscription_id,),
            )
            await db.commit()

    async def count_reminders(self) -> int:
        async with self._connect() as db:
            cursor = await db.execute("SELECT COUNT(*) FROM reminders_sent")
            row = await cursor.fetchone()
            return int(row[0])

    def _connect(self) -> aiosqlite.Connection:
        return aiosqlite.connect(self.path)

    @staticmethod
    def _row_to_dict(row: aiosqlite.Row | tuple[Any, ...]) -> dict[str, Any]:
        return {
            "id": row[0],
            "user_id": row[1],
            "name": row[2],
            "amount_cents": row[3],
            "period": row[4],
            "next_payment": date.fromisoformat(row[5]),
        }
