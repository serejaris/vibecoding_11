from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Добавить"), KeyboardButton(text="📋 Список")],
            [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="🗑 Удалить")],
            [KeyboardButton(text="❌ Отмена")],
        ],
        resize_keyboard=True,
    )


def period_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Еженедельно", callback_data="period:weekly"),
                InlineKeyboardButton(text="Ежемесячно", callback_data="period:monthly"),
            ],
            [InlineKeyboardButton(text="Ежегодно", callback_data="period:yearly")],
        ]
    )


def subscriptions_keyboard(
    items: list[dict], prefix: str, delete_label: bool = False
) -> InlineKeyboardMarkup:
    rows = []
    for item in items:
        text = f"🗑 {item['name']}" if delete_label else item["name"]
        rows.append(
            [InlineKeyboardButton(text=text, callback_data=f"{prefix}:{item['id']}")]
        )
    rows.append([InlineKeyboardButton(text="Отмена", callback_data=f"{prefix}:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def paid_keyboard(subscription_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Оплачено — сдвинуть дату",
                    callback_data=f"paid:{subscription_id}",
                )
            ]
        ]
    )
