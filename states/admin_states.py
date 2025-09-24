from aiogram.fsm.state import StatesGroup, State


class AdminStates(StatesGroup):
    waiting_for_category_name = State()
    waiting_for_product_name = State()
    waiting_for_category_id = State()
    waiting_for_price = State()
    waiting_for_photo_url = State()
    waiting_for_sizes = State()
