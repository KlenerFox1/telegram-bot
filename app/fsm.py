from aiogram.fsm.state import State, StatesGroup


class SellStates(StatesGroup):
    waiting_type = State()
    waiting_phone = State()


class DepositStates(StatesGroup):
    waiting_amount = State()


class WithdrawStates(StatesGroup):
    waiting_amount = State()


class AdminAccountTypesStates(StatesGroup):
    waiting_new_label = State()
    waiting_new_price = State()
    waiting_add_key = State()
    waiting_add_label = State()
    waiting_add_price = State()


class AdminBroadcastStates(StatesGroup):
    waiting_text = State()

