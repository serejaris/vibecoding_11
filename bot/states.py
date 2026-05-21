from aiogram.fsm.state import State, StatesGroup


class AddSubscription(StatesGroup):
    name = State()
    amount = State()
    period = State()


class ChangeDate(StatesGroup):
    subscription_id = State()
    next_payment = State()
