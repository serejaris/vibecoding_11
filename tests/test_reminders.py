import unittest
from datetime import date

from bot.reminders import send_due_reminders


class FakeBot:
    def __init__(self, failures_before_success=0):
        self.failures_before_success = failures_before_success
        self.sent_messages = []

    async def send_message(self, user_id, text, reply_markup=None):
        if self.failures_before_success > 0:
            self.failures_before_success -= 1
            raise RuntimeError("telegram send failed")
        self.sent_messages.append(
            {"user_id": user_id, "text": text, "reply_markup": reply_markup}
        )


class FakeReminderDb:
    def __init__(self, items):
        self.items = items
        self.sent = set()

    async def list_due_subscriptions(self, offsets):
        return self.items

    async def was_reminder_sent(self, subscription_id, payment_date, remind_offset):
        return (subscription_id, payment_date, remind_offset) in self.sent

    async def mark_reminder_sent(self, subscription_id, payment_date, remind_offset):
        self.sent.add((subscription_id, payment_date, remind_offset))


class ReminderTests(unittest.IsolatedAsyncioTestCase):
    async def test_send_due_reminders_continues_after_send_failure(self):
        first = {
            "id": 1,
            "user_id": 10,
            "name": "Broken",
            "amount_cents": 1000,
            "next_payment": date(2026, 6, 1),
            "remind_offset": 1,
        }
        second = {
            "id": 2,
            "user_id": 20,
            "name": "Spotify",
            "amount_cents": 999,
            "next_payment": date(2026, 6, 1),
            "remind_offset": 1,
        }
        bot = FakeBot(failures_before_success=1)
        db = FakeReminderDb([first, second])

        with self.assertLogs("bot.reminders", level="ERROR") as logs:
            await send_due_reminders(bot, db, {1})

        self.assertEqual([message["user_id"] for message in bot.sent_messages], [20])
        self.assertNotIn((1, date(2026, 6, 1), 1), db.sent)
        self.assertIn((2, date(2026, 6, 1), 1), db.sent)
        self.assertIn("Failed to send reminder for subscription 1", logs.output[0])


if __name__ == "__main__":
    unittest.main()
