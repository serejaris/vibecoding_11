from __future__ import annotations

import calendar
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

PERIOD_LABELS = {
    "weekly": "еженедельно",
    "monthly": "ежемесячно",
    "yearly": "ежегодно",
}


def parse_amount_to_cents(raw: str) -> int:
    value = raw.strip().replace(",", ".")
    try:
        amount = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError("invalid amount") from exc

    if amount <= 0:
        raise ValueError("amount must be positive")
    cents = (amount * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    if amount.as_tuple().exponent < -2:
        raise ValueError("too many decimal places")
    return int(cents)


def format_amount(cents: int) -> str:
    dollars = cents // 100
    remainder = cents % 100
    if remainder == 0:
        return f"${dollars}"
    return f"${dollars}.{remainder:02d}"


def monthly_cents(amount_cents: int, period: str) -> int:
    if period == "weekly":
        return round(amount_cents * 52 / 12)
    if period == "monthly":
        return amount_cents
    if period == "yearly":
        return round(amount_cents / 12)
    raise ValueError(f"unknown period: {period}")


def add_period(source: date, period: str) -> date:
    if period == "weekly":
        return source + timedelta(days=7)
    if period == "yearly":
        return _add_months(source, 12)
    if period == "monthly":
        return _add_months(source, 1)
    raise ValueError(f"unknown period: {period}")


def _add_months(source: date, months: int) -> date:
    month_index = source.month - 1 + months
    year = source.year + month_index // 12
    month = month_index % 12 + 1
    day = min(source.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def parse_user_date(raw: str) -> date:
    parts = raw.strip().split(".")
    if len(parts) != 3:
        raise ValueError("invalid date")
    day, month, year = [int(part) for part in parts]
    return date(year, month, day)


def urgency_icon(days_left: int) -> str:
    if days_left <= 3:
        return "🔴"
    if days_left <= 7:
        return "🟡"
    return "🟢"


def days_until(next_payment: date, today: date | None = None) -> int:
    today = today or date.today()
    return (next_payment - today).days


def format_date(value: date) -> str:
    return value.strftime("%d.%m.%Y")


def period_label(period: str) -> str:
    return PERIOD_LABELS.get(period, period)


def format_subscription_card(item: dict, today: date | None = None) -> str:
    next_payment = item["next_payment"]
    days_left = days_until(next_payment, today)
    monthly = monthly_cents(item["amount_cents"], item["period"])
    if days_left == 0:
        when = "сегодня"
    elif days_left < 0:
        when = f"просрочено на {abs(days_left)} дн."
    else:
        when = f"через {days_left} дн."
    return (
        f"{urgency_icon(days_left)} <b>{item['name']}</b>\n"
        f"{format_amount(item['amount_cents'])} / {period_label(item['period'])}\n"
        f"Следующее списание: {format_date(next_payment)} ({when})\n"
        f"≈ {format_amount(monthly)}/мес"
    )


def format_subscriptions_list(items: list[dict], today: date | None = None) -> str:
    if not items:
        return "Подписок пока нет"
    cards = [format_subscription_card(item, today) for item in items]
    return "📋 <b>Твои подписки</b>\n\n" + "\n\n".join(cards)


def format_stats(items: list[dict], today: date | None = None) -> str:
    if not items:
        return "Подписок пока нет"
    today = today or date.today()
    total = sum(monthly_cents(item["amount_cents"], item["period"]) for item in items)
    upcoming = [
        item for item in items if 0 <= days_until(item["next_payment"], today) <= 30
    ]
    lines = [f"📊 <b>Итого ≈ {format_amount(total)}/мес</b>"]
    if upcoming:
        lines.append("\nБлижайшие 30 дней:")
        for item in upcoming:
            days_left = days_until(item["next_payment"], today)
            when = "сегодня" if days_left == 0 else f"через {days_left} дн."
            lines.append(
                f"• {item['name']}: {format_amount(item['amount_cents'])}, {when}"
            )
    else:
        lines.append("\nВ ближайшие 30 дней списаний нет")
    return "\n".join(lines)
