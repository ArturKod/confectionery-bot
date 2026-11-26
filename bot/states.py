from aiogram.fsm.state import State, StatesGroup

class OrderState(StatesGroup):
    """Состояния для оформления заказа."""
    waiting_for_phone = State()
    waiting_for_date = State()
    waiting_for_confirm = State()

class AdminState(StatesGroup):
    waiting_for_new_price = State()
    waiting_for_admin_comment = State()