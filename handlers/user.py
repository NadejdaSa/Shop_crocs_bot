from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from database.connection import Session
from database.models import Category, Product, CartItem, User, Size
import keyboards.keyboards as kb
from aiogram.filters import CommandStart, Command
import logging
from states.user_states import UserStates
from filter.filter import IsUser
from aiogram.utils.keyboard import InlineKeyboardBuilder

user_router = Router()
user_router.message.filter(IsUser())
user_router.callback_query.filter(IsUser())
logger = logging.getLogger(__name__)

USER_PREFIXES = {"category_", "product_", "add_to_cart_", "back_to_", "cart"}


@user_router.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(UserStates.choosing_category)
    session = Session()
    user = session.query(User).filter(User.tg_id == message.from_user.id).first()
    if not user:
        user = User(tg_id=message.from_user.id)
        session.add(user)
        session.commit()
    session.close()

    await message.answer("👟 Добро пожаловать в магазин кроссовок!\n"
                         "Выберите категорию:",
                         reply_markup=kb.main_menu_user())


async def render_cart(user_id: int, chat_obj: Message | CallbackQuery,
                      is_callback: bool = False):
    session = Session()
    try:
        user = session.query(User).filter_by(tg_id=user_id).first()

        if not user or not user.cart_items:
            text = "🛒 Ваша корзина пуста"
            markup = kb.main_menu_user()
        else:
            total = 0
            cart_text = "🛒 Ваша корзина:\n\n"

            for item in user.cart_items:
                item_total = item.product.price * item.quantity
                total += item_total
                cart_text += f"👟 {item.product.name}\n"
                cart_text += f"📏 Размер: {item.size.size}\n"
                cart_text += f"💰 Цена: {item.product.price} руб x {item.quantity} = {item_total} руб\n\n"

            cart_text += f"💵 Общая сумма: {total} руб"

            builder = InlineKeyboardBuilder()
            builder.button(text="🗑 Очистить корзину",
                           callback_data="clear_cart")
            builder.button(text="⬅️ Назад", callback_data="back_to_categories")
            builder.adjust(1)
            markup = builder.as_markup()
            text = cart_text

        # Если пришло с кнопки — редактируем сообщение, если командой — отвечаем
        if is_callback:
            try:
                await chat_obj.message.edit_text(text, reply_markup=markup)
            except TelegramBadRequest:
                try:
                    await chat_obj.message.edit_reply_markup(reply_markup=markup)
                except TelegramBadRequest:
                    pass
        else:
            await chat_obj.answer(text, reply_markup=markup)

    finally:
        session.close()


@user_router.callback_query(F.data == "show_cart")
async def show_cart_callback(callback: CallbackQuery):
    await render_cart(callback.from_user.id, callback, is_callback=True)
    await callback.answer()


@user_router.message(Command("show_cart"))
async def show_cart_command(message: Message):
    await render_cart(message.from_user.id, message, is_callback=False)



@user_router.callback_query(F.data.startswith("category_"))
async def show_category_products(callback: CallbackQuery, state: FSMContext):
    category_id = int(callback.data.split("_")[1])
    
    session = Session()
    category = session.query(Category).get(category_id)
    products = session.query(Product).filter_by(category_id=category_id).all()
    session.close()
    
    if not products:
        await callback.message.edit_text(
            f"В категории '{category.name}' пока нет товаров.",
            reply_markup=kb.main_menu_user()
        )
        await callback.answer()
        return
    
    await state.set_state(UserStates.choosing_product)
    await state.update_data(category_id=category_id)
    
    await callback.message.edit_text(
        f"Категория: {category.name}\nВыберите товар:",
        reply_markup=kb.products_menu(products)
    )
    await callback.answer()


@user_router.callback_query(F.data == "back_to_categories")
async def back_to_categories(callback: CallbackQuery, state: FSMContext):
    await state.set_state(UserStates.choosing_category)
    await callback.message.edit_text(
        "👟 Выберите категорию:",
        reply_markup=kb.main_menu_user()
    )
    await callback.answer()


@user_router.callback_query(F.data.startswith("product_"))
async def show_product(callback: CallbackQuery, state: FSMContext):
    product_id = int(callback.data.split("_")[1])
    
    session = Session()
    product = session.query(Product).get(product_id)
    sizes = [str(size.size) for size in product.sizes]
    session.close()
    
    await state.set_state(UserStates.choosing_size)
    await state.update_data(product_id=product_id)
    
    text = (
        f"👟 {product.name}\n"
        f"💵 Цена: {product.price} руб\n"
        f"📏 Доступные размеры: {', '.join(sizes)}"
    )

    try:
        await callback.message.delete()
    except:
        pass  # Если не получилось удалить, продолжаем
    
    await callback.message.answer_photo(
        photo=product.photo_url,
        caption=text,
        reply_markup=kb.product_detail_menu(product.id, sizes)
    )
    await callback.answer()


@user_router.callback_query(F.data == "back_to_products")
async def back_to_products(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    category_id = data.get("category_id")
    
    session = Session()
    category = session.query(Category).get(category_id)
    products = session.query(Product).filter_by(category_id=category_id).all()
    session.close()
    
    await state.set_state(UserStates.choosing_product)
    
    try:
        await callback.message.delete()
    except:
        pass  # Если не получилось удалить, продолжаем
    
    await callback.message.answer(
        f"Категория: {category.name}\nВыберите товар:",
        reply_markup=kb.products_menu(products)
    )
    await callback.answer()


@user_router.callback_query(F.data.startswith("add_to_cart_"))
async def add_to_cart(callback: CallbackQuery, state: FSMContext):
    try:
        # Разбираем callback data правильно
        parts = callback.data.split("_")
        print(f"Debug: callback data = {callback.data}")
        print(f"Debug: parts = {parts}")
        
        if len(parts) >= 5:
            product_id = int(parts[3])
            size = float(parts[4])
        else:
            await callback.answer("❌ Ошибка в данных товара")
            return
        
        print(f"Debug: product_id = {product_id}, size = {size}")
        
        session = Session()
        
        # Находим пользователя
        user = session.query(User).filter_by(tg_id=callback.from_user.id).first()
        if not user:
            user = User(tg_id=callback.from_user.id)
            session.add(user)
            session.commit()
            session.refresh(user)
        
        # Находим размер и товар ОДНОВРЕМЕННО в одной сессии
        size_obj = session.query(Size).filter_by(product_id=product_id, size=size).first()
        if not size_obj:
            await callback.answer("❌ Размер не найден")
            session.close()
            return
        
        # Находим товар для названия в ТОЙ ЖЕ сессии
        product = session.query(Product).get(product_id)
        product_name = product.name  # Сохраняем название до закрытия сессии
        
        # Добавляем в корзину
        cart_item = session.query(CartItem).filter_by(
            user_id=user.id,
            product_id=product_id,
            size_id=size_obj.id
        ).first()
        
        if cart_item:
            cart_item.quantity += 1
            quantity = cart_item.quantity
        else:
            cart_item = CartItem(
                user_id=user.id,
                product_id=product_id,
                size_id=size_obj.id,
                quantity=1
            )
            session.add(cart_item)
            quantity = 1
        
        session.commit()
        session.close()  # Теперь сессия закрывается после получения всех данных
        
        # Отправляем сообщение в чат вместо всплывающего уведомления
        await callback.message.answer(
            f"✅ Товар '{product_name}' (размер {size}) добавлен в корзину!\n"
            f"📦 Всего в корзине: {quantity} шт\n\n"
            f"🛒 Посмотреть корзину: /show_cart"
        )
        
        # Все равно вызываем answer чтобы убрать часики на кнопке
        await callback.answer()
        
    except Exception as e:
        print(f"Error: {e}")
        await callback.answer("❌ Ошибка при добавлении в корзину")


@user_router.callback_query(F.data == "clear_cart")
async def clear_cart_callback(callback: CallbackQuery):
    session = Session()
    try:
        user = session.query(User).filter_by(tg_id=callback.from_user.id).first()
        if user:
            deleted_count = session.query(CartItem).filter_by(user_id=user.id).delete()
            session.commit()
            await callback.answer(f"✅ Корзина очищена ({deleted_count} товаров удалено)")
        else:
            await callback.answer("❌ Пользователь не найден")

        # Сразу обновляем сообщение корзины
        await render_cart(callback.from_user.id, callback, is_callback=True)

    except Exception as e:
        session.rollback()
        await callback.answer(f"❌ Ошибка: {e}")
    finally:
        session.close()
