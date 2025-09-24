from aiogram.utils.keyboard import InlineKeyboardBuilder
from database.connection import Session
from database.models import Category, Product


def main_menu_user():
    session = Session()
    categories = session.query(Category).all()
    session.close()
    
    builder = InlineKeyboardBuilder()
    for category in categories:
        builder.button(
            text=category.name,
            callback_data=f"category_{category.id}"
        )
    builder.button(text="🛒 Корзина", callback_data="show_cart")
    builder.adjust(1)
    return builder.as_markup()


def products_menu(products):
    builder = InlineKeyboardBuilder()
    for product in products:
        builder.button(
            text=product.name,
            callback_data=f"product_{product.id}"
        )
    builder.button(text="⬅️ Назад к категориям", callback_data="back_to_categories")
    builder.adjust(1)
    return builder.as_markup()


def product_detail_menu(product_id, sizes):
    builder = InlineKeyboardBuilder()
    for size in sizes:
        builder.button(
            text=f"Размер {size}",
            callback_data=f"add_to_cart_{product_id}_{size}"
        )
    builder.button(text="⬅️ Назад к товарам", callback_data="back_to_products")
    builder.adjust(1)
    return builder.as_markup()


def admin_menu_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Добавить категорию", callback_data="admin_add_category")
    builder.button(text="🗑 Удалить категорию", callback_data="admin_delete_category")
    builder.button(text="➕ Добавить товар", callback_data="admin_add_product")
    builder.button(text="📦 Список товаров", callback_data="admin_products")
    
    builder.adjust(1)
    return builder.as_markup()


def cancel_keyboard():
    """Клавиатура для отмены действия"""
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отменить", callback_data="admin_cancel")
    return builder.as_markup()


def admin_cancel_keyboard():
    """Клавиатура для отмены с возвратом в админское меню"""
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отменить и вернуться в меню", callback_data="admin_menu")
    return builder.as_markup()