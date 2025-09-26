from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message, CallbackQuery, LabeledPrice, PreCheckoutQuery, ContentType
from aiogram.fsm.context import FSMContext
from database.connection import Session
from database.models import Category, Product, CartItem, User, Size
import keyboards.keyboards as kb
from aiogram.filters import CommandStart, Command
import logging
from states.user_states import UserStates
from filter.filter import IsUser
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

user_router = Router()
user_router.message.filter(IsUser())
user_router.callback_query.filter(IsUser())
logger = logging.getLogger(__name__)

USER_PREFIXES = {"category_", "product_", "add_to_cart_", "back_to_", "cart"}
PROVIDER_TOKEN = "381764678:TEST:143408"


# Главное меню
@user_router.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(UserStates.choosing_category)
    session = Session()
    user = session.query(User).filter(
        User.tg_id == message.from_user.id).first()
    if not user:
        user = User(tg_id=message.from_user.id)
        session.add(user)
        session.commit()
    session.close()

    await message.answer("👟 Добро пожаловать в магазин кроссовок!",
                         reply_markup=kb.main_menu_user())


# Категории
@user_router.callback_query(F.data == "show_categories")
async def show_categories(callback: CallbackQuery, state: FSMContext):
    await state.set_state(UserStates.choosing_category)
    await callback.message.edit_text(
        "Выберите категорию:",
        reply_markup=kb.show_categories()
    )
    await callback.answer()


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


@user_router.callback_query(F.data == "go_to_main_menu")
async def back_to_main_menu(callback: CallbackQuery, state: FSMContext):
    await state.set_state(UserStates.choosing_category)
    await callback.message.edit_text(
        "👟 Главное меню",
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
    except Exception as e:
        print(f"Ошибка при удалении сообщения: {e}")

    await callback.message.answer_photo(
        photo=product.photo_url,
        caption=text,
        reply_markup=kb.product_detail_menu(product.id, sizes)
    )
    await callback.answer()


@user_router.callback_query(F.data == "back_to_category_list")
async def back_to_category_list(callback: CallbackQuery, state: FSMContext):
    await state.set_state(UserStates.choosing_category)
    await callback.message.edit_text(
        "Выберите категорию:",
        reply_markup=kb.show_categories()
    )
    await callback.answer()


@user_router.callback_query(F.data == "back_to_categories")
async def back_to_categories(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    category_id = data.get("category_id")
    if not category_id:
        # Если категории нет в state — вернуться в главное меню
        await callback.message.edit_text(
            "👟 Главное меню",
            reply_markup=kb.main_menu_user()
        )
        await callback.answer()
        return

    session = Session()
    category = session.query(Category).get(category_id)
    products = session.query(Product).filter_by(category_id=category_id).all()
    session.close()

    await state.set_state(UserStates.choosing_product)
    await callback.message.edit_text(
        f"Категория: {category.name}\nВыберите товар:",
        reply_markup=kb.products_menu(products)
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
    except Exception as e:
        print(f"Ошибка при удалении сообщения: {e}")

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
        user = session.query(User).filter_by(
            tg_id=callback.from_user.id).first()
        if not user:
            user = User(tg_id=callback.from_user.id)
            session.add(user)
            session.commit()
            session.refresh(user)

        # Находим размер и товар ОДНОВРЕМЕННО в одной сессии
        size_obj = session.query(Size).filter_by(
            product_id=product_id, size=size).first()
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
        session.close()

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


# Корзина
async def render_cart_overview(user_id: int,
                               chat_obj: Message | CallbackQuery,
                               is_callback: bool = False):
    session = Session()
    try:
        user = session.query(User).filter_by(tg_id=user_id).first()

        if not user or not user.cart_items:
            text = "🛒 Ваша корзина пуста"
            markup = kb.main_menu_user()
        else:
            cart_text = "🛒 Ваша корзина:\n\n"
            builder = InlineKeyboardBuilder()

            for item in user.cart_items:
                cart_text += f"👟 {item.product.name} ({item.size.size}) x{item.quantity}\n"
                builder.button(
                    text=f"{item.product.name} ({item.size.size})",
                    callback_data=f"edit_item_{item.id}"
                )

            builder.button(text="🗑 Очистить корзину",
                           callback_data="clear_cart")
            builder.button(text="⬅️ Назад", callback_data="back_to_categories")
            builder.button(text="💳 Оплатить заказ", callback_data="pay")
            builder.adjust(1)
            markup = builder.as_markup()
            text = cart_text

        if is_callback:
            try:
                await chat_obj.message.edit_text(text, reply_markup=markup)
            except TelegramBadRequest:
                try:
                    await chat_obj.message.edit_reply_markup(
                        reply_markup=markup)
                except TelegramBadRequest:
                    pass
        else:
            await chat_obj.answer(text, reply_markup=markup)

    finally:
        session.close()


async def render_cart_item(item_id: int, chat_obj: Message | CallbackQuery):
    session = Session()
    try:
        item = session.query(CartItem).get(item_id)
        if not item:
            await chat_obj.answer("❌ Товар не найден")
            return

        text = (
            f"👟 {item.product.name}\n"
            f"📏 Размер: {item.size.size}\n"
            f"💵 Цена: {item.product.price} руб\n"
            f"📦 Количество: {item.quantity}"
        )

        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="➖",
                                 callback_data=f"decrease_item_{item.id}"),
            InlineKeyboardButton(text=f"{item.quantity}",
                                 callback_data="noop"),
            InlineKeyboardButton(text="➕",
                                 callback_data=f"increase_item_{item.id}")
        )
        builder.row(
            InlineKeyboardButton(text="🗑 Удалить",
                                 callback_data=f"remove_item_{item.id}"),
            InlineKeyboardButton(text="⬅️ Назад", callback_data="show_cart")
        )
        builder.adjust(2)
        markup = builder.as_markup()

        try:
            await chat_obj.message.edit_text(text, reply_markup=markup)
        except TelegramBadRequest:
            await chat_obj.message.answer(text, reply_markup=markup)

    finally:
        session.close()


@user_router.callback_query(F.data == "show_cart")
async def show_cart_overview_callback(callback: CallbackQuery):
    await render_cart_overview(callback.from_user.id,
                               callback,
                               is_callback=True)
    await callback.answer()


@user_router.message(Command("show_cart"))
async def show_cart_command(message: Message):
    await render_cart_overview(message.from_user.id,
                               message,
                               is_callback=False)


@user_router.callback_query(F.data.startswith("edit_item_"))
async def edit_cart_item(callback: CallbackQuery):
    item_id = int(callback.data.split("_")[2])
    await render_cart_item(item_id, callback)
    await callback.answer()


@user_router.callback_query(F.data == "clear_cart")
async def clear_cart_callback(callback: CallbackQuery):
    session = Session()
    try:
        user = session.query(User).filter_by(
            tg_id=callback.from_user.id).first()
        if user:
            deleted_count = session.query(CartItem).filter_by(
                user_id=user.id).delete()
            session.commit()
            await callback.answer(
                f"✅ Корзина очищена ({deleted_count} товаров удалено)")
        else:
            await callback.answer("❌ Пользователь не найден")

        # Сразу обновляем сообщение корзины
        await render_cart_overview(callback.from_user.id,
                                   callback,
                                   is_callback=True)

    except Exception as e:
        session.rollback()
        await callback.answer(f"❌ Ошибка: {e}")
    finally:
        session.close()


@user_router.callback_query(F.data.startswith("increase_item_"))
async def increase_item(callback: CallbackQuery):
    item_id = int(callback.data.split("_")[2])
    session = Session()
    try:
        item = session.query(CartItem).get(item_id)
        if item:
            item.quantity += 1
            session.commit()
            await render_cart_item(item_id, callback)
        await callback.answer()
    finally:
        session.close()


@user_router.callback_query(F.data.startswith("decrease_item_"))
async def decrease_item(callback: CallbackQuery):
    item_id = int(callback.data.split("_")[2])
    session = Session()
    try:
        item = session.query(CartItem).get(item_id)
        if item:
            if item.quantity > 1:
                item.quantity -= 1
                session.commit()
                await render_cart_item(item_id, callback)
            else:
                # Если 1 — удаляем товар
                session.delete(item)
                session.commit()
                await render_cart_overview(callback.from_user.id,
                                           callback,
                                           is_callback=True)
        await callback.answer()
    finally:
        session.close()


@user_router.callback_query(F.data.startswith("remove_item_"))
async def remove_item(callback: CallbackQuery):
    item_id = int(callback.data.split("_")[2])
    session = Session()
    try:
        item = session.query(CartItem).get(item_id)
        if item:
            session.delete(item)
            session.commit()
            await render_cart_overview(callback.from_user.id,
                                       callback,
                                       is_callback=True)
        await callback.answer()
    finally:
        session.close()


# Генерация счета
@user_router.callback_query(F.data == "pay")
async def pay_callback(callback: CallbackQuery):
    session = Session()
    try:
        user = session.query(User).filter_by(
            tg_id=callback.from_user.id).first()
        if not user or not user.cart_items:
            await callback.answer("❌ Корзина пуста")
            return

        prices = []
        total_amount = 0

        for item in user.cart_items:
            amount = int(item.product.price * 100)
            prices.append(LabeledPrice(
                label=f"{item.product.name} ({item.size.size}) x{item.quantity}",
                amount=amount * item.quantity
            ))
            total_amount += item.product.price * item.quantity

        await callback.message.answer_invoice(
            title="💳 Оплата заказа",
            description=f"Заказ на сумму {total_amount} руб.",
            provider_token=PROVIDER_TOKEN,
            currency="RUB",
            prices=prices,
            start_parameter="order",
            payload=f"order_user_{user.id}"
        )
        await callback.answer()
    finally:
        session.close()


@user_router.pre_checkout_query()
async def pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)


@user_router.message(F.successful_payment)
async def successful_payment(message: Message):
    print("=== SUCCESSFUL PAYMENT HANDLER TRIGGERED ===")  # для отладки

    payment_info = message.successful_payment

    session = Session()
    try:
        user = session.query(User).filter_by(
            tg_id=message.from_user.id
        ).first()
        if user:
            session.query(CartItem).filter_by(user_id=user.id).delete()
            session.commit()
    finally:
        session.close()

    await message.answer(
        f"✅ Спасибо за покупку! Оплата прошла успешно.\n"
        f"Детали платежа:\n"
        f"Сумма: {payment_info.total_amount / 100} {payment_info.currency}\n"
        f"Название: {payment_info.invoice_payload}"
    )
    await render_cart_overview(message.from_user.id, message, is_callback=False)
