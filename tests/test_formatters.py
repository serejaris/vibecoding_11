import unittest
from datetime import date

from bot.formatters import (
    add_period,
    format_amount,
    monthly_cents,
    parse_amount_to_cents,
    parse_user_date,
    validate_period,
    urgency_icon,
)


class FormatterTests(unittest.TestCase):
    def test_parse_amount_to_cents_accepts_dot_and_comma(self):
        self.assertEqual(parse_amount_to_cents("9.99"), 999)
        self.assertEqual(parse_amount_to_cents("15,50"), 1550)

    def test_parse_amount_to_cents_rejects_invalid_values(self):
        for value in ("", "abc", "-1", "0", "1.999", "NaN", "Infinity"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    parse_amount_to_cents(value)

    def test_format_amount_uses_usd_symbol(self):
        self.assertEqual(format_amount(999), "$9.99")
        self.assertEqual(format_amount(1500), "$15")

    def test_monthly_cents_normalizes_periods(self):
        self.assertEqual(monthly_cents(1200, "monthly"), 1200)
        self.assertEqual(monthly_cents(1200, "yearly"), 100)
        self.assertEqual(monthly_cents(1200, "weekly"), 5200)

    def test_add_period_handles_calendar_month_end(self):
        self.assertEqual(add_period(date(2026, 1, 31), "monthly"), date(2026, 2, 28))
        self.assertEqual(add_period(date(2026, 2, 28), "yearly"), date(2027, 2, 28))
        self.assertEqual(add_period(date(2026, 5, 21), "weekly"), date(2026, 5, 28))

    def test_parse_user_date_uses_day_month_year(self):
        self.assertEqual(parse_user_date("15.06.2026"), date(2026, 6, 15))
        with self.assertRaises(ValueError):
            parse_user_date("2026-06-15")

    def test_urgency_icon_matches_prd_thresholds(self):
        self.assertEqual(urgency_icon(2), "🔴")
        self.assertEqual(urgency_icon(7), "🟡")
        self.assertEqual(urgency_icon(8), "🟢")

    def test_validate_period_accepts_only_supported_periods(self):
        self.assertEqual(validate_period("weekly"), "weekly")
        self.assertEqual(validate_period("monthly"), "monthly")
        self.assertEqual(validate_period("yearly"), "yearly")
        with self.assertRaises(ValueError):
            validate_period("daily")


if __name__ == "__main__":
    unittest.main()
