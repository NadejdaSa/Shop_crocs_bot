from aiogram.fsm.state import StatesGroup, State


class UserStates(StatesGroup):
    choosing_category = State()
    choosing_product = State()
    choosing_size = State()
    confirming_add_to_cart = State()
