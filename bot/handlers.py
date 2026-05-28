from __future__ import annotations

from datetime import date

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.database import Database
from bot.formatters import (
    add_period,
    format_stats,
    format_subscription_card,
    format_subscriptions_list,
    parse_amount_to_cents,
    parse_user_date,
    validate_period,
)
from bot.keyboards import main_menu, period_keyboard, subscriptions_keyboard
from bot.states import AddSubscription, ChangeDate


def create_router(db: Database) -> Router:
    router = Router()

    @router.message(CommandStart())
    async def start(message: Message) -> None:
        await message.answer(
            "Привет. Я помогу вести подписки в USD и помнить о списаниях.\n"
            "Начни с «➕ Добавить».",
            reply_markup=main_menu(),
        )

    @router.message(Command("help"))
    async def help_command(message: Message) -> None:
        await message.answer(
            "/add — добавить подписку\n"
            "/list — список\n"
            "/stats — статистика\n"
            "/date — изменить дату списания\n"
            "/delete — удалить подписку",
            reply_markup=main_menu(),
        )

    @router.message(Command("add"))
    @router.message(F.text == "➕ Добавить")
    async def add_start(message: Message, state: FSMContext) -> None:
        await state.set_state(AddSubscription.name)
        await message.answer("Как называется подписка?", reply_markup=main_menu())

    @router.message(F.text == "❌ Отмена")
    async def cancel(message: Message, state: FSMContext) -> None:
        await state.clear()
        await message.answer("Отменено", reply_markup=main_menu())

    @router.message(AddSubscription.name)
    async def add_name(message: Message, state: FSMContext) -> None:
        name = (message.text or "").strip()
        if not name:
            await message.answer("Введи название подписки")
            return
        await state.update_data(name=name)
        await state.set_state(AddSubscription.amount)
        await message.answer("Сколько списывается? Укажи сумму в $, например 9.99")

    @router.message(AddSubscription.amount)
    async def add_amount(message: Message, state: FSMContext) -> None:
        try:
            amount_cents = parse_amount_to_cents(message.text or "")
        except ValueError:
            await message.answer("Введи число вроде 9.99")
            return
        await state.update_data(amount_cents=amount_cents)
        await state.set_state(AddSubscription.period)
        await message.answer("Как часто списывается?", reply_markup=period_keyboard())

    @router.callback_query(AddSubscription.period, F.data.startswith("period:"))
    async def add_period_callback(callback: CallbackQuery, state: FSMContext) -> None:
        try:
            period = validate_period(callback.data.split(":", 1)[1])
        except ValueError:
            await callback.answer("Неизвестный период", show_alert=True)
            return
        data = await state.get_data()
        next_payment = add_period(date.today(), period)
        await db.create_subscription(
            user_id=callback.from_user.id,
            name=data["name"],
            amount_cents=data["amount_cents"],
            period=period,
            next_payment=next_payment,
        )
        await state.clear()
        item = {
            "name": data["name"],
            "amount_cents": data["amount_cents"],
            "period": period,
            "next_payment": next_payment,
        }
        await callback.message.answer(
            "✅ Сохранено\n\n" + format_subscription_card(item),
            reply_markup=main_menu(),
        )
        await callback.answer()

    @router.message(Command("list"))
    @router.message(F.text == "📋 Список")
    async def list_command(message: Message) -> None:
        items = await db.list_subscriptions(message.from_user.id)
        await message.answer(format_subscriptions_list(items), reply_markup=main_menu())

    @router.message(Command("stats"))
    @router.message(F.text == "📊 Статистика")
    async def stats_command(message: Message) -> None:
        items = await db.list_subscriptions(message.from_user.id)
        await message.answer(format_stats(items), reply_markup=main_menu())

    @router.message(Command("delete"))
    @router.message(F.text == "🗑 Удалить")
    async def delete_command(message: Message) -> None:
        items = await db.list_subscriptions(message.from_user.id)
        if not items:
            await message.answer("Подписок пока нет", reply_markup=main_menu())
            return
        await message.answer(
            "Какую подписку удалить?",
            reply_markup=subscriptions_keyboard(items, "delete", delete_label=True),
        )

    @router.callback_query(F.data.startswith("delete:"))
    async def delete_callback(callback: CallbackQuery) -> None:
        value = callback.data.split(":", 1)[1]
        if value == "cancel":
            await callback.message.answer("Отменено", reply_markup=main_menu())
            await callback.answer()
            return
        deleted = await db.delete_subscription(callback.from_user.id, int(value))
        text = "Подписка удалена" if deleted else "Подписка не найдена"
        await callback.message.answer(text, reply_markup=main_menu())
        await callback.answer()

    @router.message(Command("date"))
    async def date_command(message: Message, state: FSMContext) -> None:
        items = await db.list_subscriptions(message.from_user.id)
        if not items:
            await message.answer("Подписок пока нет", reply_markup=main_menu())
            return
        await state.clear()
        await message.answer(
            "У какой подписки поменять дату?",
            reply_markup=subscriptions_keyboard(items, "date"),
        )

    @router.callback_query(F.data.startswith("date:"))
    async def date_pick_callback(callback: CallbackQuery, state: FSMContext) -> None:
        value = callback.data.split(":", 1)[1]
        if value == "cancel":
            await state.clear()
            await callback.message.answer("Отменено", reply_markup=main_menu())
            await callback.answer()
            return
        item = await db.get_subscription(callback.from_user.id, int(value))
        if item is None:
            await callback.message.answer("Подписка не найдена", reply_markup=main_menu())
            await callback.answer()
            return
        await state.update_data(subscription_id=item["id"])
        await state.set_state(ChangeDate.next_payment)
        await callback.message.answer("Введи дату следующего списания: 15.06.2026")
        await callback.answer()

    @router.message(ChangeDate.next_payment)
    async def date_save(message: Message, state: FSMContext) -> None:
        try:
            next_payment = parse_user_date(message.text or "")
        except ValueError:
            await message.answer("Введи дату в формате 15.06.2026")
            return
        data = await state.get_data()
        item = await db.update_next_payment(
            message.from_user.id, data["subscription_id"], next_payment
        )
        await state.clear()
        if item is None:
            await message.answer("Подписка не найдена", reply_markup=main_menu())
            return
        await message.answer(
            "✅ Дата обновлена\n\n" + format_subscription_card(item),
            reply_markup=main_menu(),
        )

    @router.callback_query(F.data.startswith("paid:"))
    async def paid_callback(callback: CallbackQuery) -> None:
        subscription_id = int(callback.data.split(":", 1)[1])
        item = await db.get_subscription(callback.from_user.id, subscription_id)
        if item is None:
            await callback.message.answer("Подписка не найдена", reply_markup=main_menu())
            await callback.answer()
            return
        next_payment = add_period(item["next_payment"], item["period"])
        updated = await db.update_next_payment(
            callback.from_user.id, subscription_id, next_payment
        )
        await db.clear_reminders_for_subscription(subscription_id)
        await callback.message.answer(
            "✅ Оплачено. Следующая дата сдвинута\n\n"
            + format_subscription_card(updated),
            reply_markup=main_menu(),
        )
        await callback.answer()

    @router.message(F.text)
    async def fallback_text(message: Message) -> None:
        await message.answer(
            "Я потерял шаг диалога. Нажми «➕ Добавить» и начни заново.",
            reply_markup=main_menu(),
        )

    return router
