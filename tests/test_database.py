import tempfile
import unittest
from datetime import date
from pathlib import Path

from bot.database import Database


class DatabaseTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / "subscriptions.db"
        self.db = Database(self.db_path)
        await self.db.init()

    async def asyncTearDown(self):
        self.tmpdir.cleanup()

    async def test_subscription_crud_is_scoped_by_user_id(self):
        first_id = await self.db.create_subscription(
            user_id=1,
            name="Netflix",
            amount_cents=1599,
            period="monthly",
            next_payment=date(2026, 6, 21),
        )
        await self.db.create_subscription(
            user_id=2,
            name="Spotify",
            amount_cents=999,
            period="monthly",
            next_payment=date(2026, 6, 22),
        )

        first_user_items = await self.db.list_subscriptions(1)
        second_user_items = await self.db.list_subscriptions(2)

        self.assertEqual([item["id"] for item in first_user_items], [first_id])
        self.assertEqual(first_user_items[0]["name"], "Netflix")
        self.assertEqual(second_user_items[0]["name"], "Spotify")

        deleted = await self.db.delete_subscription(user_id=1, subscription_id=first_id)

        self.assertTrue(deleted)
        self.assertEqual(await self.db.list_subscriptions(1), [])
        self.assertEqual(len(await self.db.list_subscriptions(2)), 1)

    async def test_reminder_dedupe_for_same_date_and_offset(self):
        subscription_id = await self.db.create_subscription(
            user_id=1,
            name="Netflix",
            amount_cents=1599,
            period="monthly",
            next_payment=date(2026, 6, 21),
        )

        self.assertFalse(
            await self.db.was_reminder_sent(subscription_id, date(2026, 6, 21), 3)
        )
        await self.db.mark_reminder_sent(subscription_id, date(2026, 6, 21), 3)
        await self.db.mark_reminder_sent(subscription_id, date(2026, 6, 21), 3)

        self.assertTrue(
            await self.db.was_reminder_sent(subscription_id, date(2026, 6, 21), 3)
        )
        self.assertEqual(await self.db.count_reminders(), 1)


if __name__ == "__main__":
    unittest.main()
