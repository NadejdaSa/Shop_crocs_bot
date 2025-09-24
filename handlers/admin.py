import math
from aiogram import F, Router
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from states.admin_states import AdminStates
from database.connection import Session
from database.models import Category, Product, Size
import keyboards.keyboards as kb
from filter.filter import IsAdmin
from aiogram.utils.keyboard import InlineKeyboardBuilder


admin_router = Router()
admin_router.message.filter(IsAdmin())
admin_router.callback_query.filter(IsAdmin())

ADMIN_PREFIXES = {"admin_",
                  "select_category_",
                  "delete_", "edit_",
                  "products_page_"}
PRODUCTS_PER_PAGE = 5


@admin_router.callback_query(F.data == "admin_cancel")
async def cancel_action(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "❌ Действие отменено",
        reply_markup=kb.admin_menu_keyboard()
    )
    await callback.answer()


@admin_router.message(CommandStart())
@admin_router.message(Command("admin"))
async def admin_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "👑 Панель администратора",
        reply_markup=kb.admin_menu_keyboard()
    )


@admin_router.callback_query(F.data == "admin_menu")
async def admin_menu(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "👑 Панель администратора",
        reply_markup=kb.admin_menu_keyboard()
    )
    await callback.answer()


@admin_router.callback_query(F.data == "admin_add_category")
async def add_category_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.waiting_for_category_name)
    await callback.message.answer(
        "📝 Введите название новой категории:\n\n"
        "❌ Для отмены нажмите кнопку ниже",
        reply_markup=kb.cancel_keyboard()
    )
    await callback.answer()


@admin_router.message(AdminStates.waiting_for_category_name)
async def add_category_finish(message: Message, state: FSMContext):
    category_name = message.text.strip()
    # Проверка на команду отмены
    if category_name.lower() in ['отмена', 'cancel', '❌ отменить']:
        await state.clear()
        await message.answer(
            "❌ Создание категории отменено",
            reply_markup=kb.admin_menu_keyboard()
        )
        return
    session = Session()

    # Проверяем, существует ли категория
    existing_category = session.query(Category).filter_by(name=category_name).first()
    if existing_category:
        await message.answer("❌ Категория с таким названием уже существует")
        session.close()
        return

    # Создаем новую категорию
    new_category = Category(name=category_name)
    session.add(new_category)
    session.commit()
    session.close()

    await state.clear()
    await message.answer(
        f"✅ Категория '{category_name}' успешно добавлена!",
        reply_markup=kb.admin_menu_keyboard()
    )


@admin_router.callback_query(F.data == "admin_add_product")
async def add_product_start(callback: CallbackQuery, state: FSMContext):
    session = Session()
    categories = session.query(Category).all()
    session.close()

    if not categories:
        await callback.message.answer(
            "❌ Сначала создайте хотя бы одну категорию",
            reply_markup=kb.admin_menu_keyboard()
        )
        await callback.answer()
        return

    await state.set_state(AdminStates.waiting_for_product_name)
    await callback.message.answer("📝 Введите название товара:\n\n"
                                  "❌ Для отмены нажмите кнопку ниже",
                                  reply_markup=kb.cancel_keyboard())
    await callback.answer()


@admin_router.message(AdminStates.waiting_for_product_name)
async def process_product_name(message: Message, state: FSMContext):
    await state.update_data(product_name=message.text)
    await state.set_state(AdminStates.waiting_for_price)
    await message.answer("Введите цену товара:")


@admin_router.message(AdminStates.waiting_for_price)
async def process_price(message: Message, state: FSMContext):
    try:
        price = float(message.text)
        await state.update_data(price=price)
        await state.set_state(AdminStates.waiting_for_photo_url)
        await message.answer("Отправьте фото товара:\n\n"
                             "❌ Для отмены нажмите кнопку ниже",
                             reply_markup=kb.cancel_keyboard())
    except ValueError:
        await message.answer("❌ Введите корректную цену (число):")


@admin_router.message(AdminStates.waiting_for_photo_url, F.photo)
async def process_photo(message: Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    await state.update_data(photo_url=photo_id)

    # Показываем выбор категории
    session = Session()
    categories = session.query(Category).all()
    session.close()

    builder = kb.InlineKeyboardBuilder()
    for category in categories:
        builder.button(
            text=category.name,
            callback_data=f"select_category_{category.id}"
        )
    builder.adjust(1)

    await state.set_state(AdminStates.waiting_for_category_id)
    await message.answer("Выберите категорию:", reply_markup=builder.as_markup())


@admin_router.callback_query(F.data.startswith("select_category_"), AdminStates.waiting_for_category_id)
async def process_category(callback: CallbackQuery, state: FSMContext):
    category_id = int(callback.data.split("_")[2])
    await state.update_data(category_id=category_id)
    await state.set_state(AdminStates.waiting_for_sizes)
    await callback.message.answer("Введите доступные размеры через запятую (например: 39, 40, 41):"
                                  "❌ Для отмены нажмите кнопку ниже",
                                  reply_markup=kb.cancel_keyboard())
    await callback.answer()


@admin_router.message(AdminStates.waiting_for_sizes)
async def process_sizes(message: Message, state: FSMContext):
    try:
        sizes_text = message.text.strip()
        sizes = [float(size.strip()) for size in sizes_text.split(",")]

        data = await state.get_data()

        session = Session()

        # Создаем товар
        product = Product(
            name=data['product_name'],
            price=data['price'],
            photo_url=data['photo_url'],
            category_id=data['category_id']
        )
        session.add(product)
        session.flush()  # Получаем ID товара

        # Добавляем размеры
        for size_value in sizes:
            size = Size(size=size_value, product_id=product.id)
            session.add(size)

        session.commit()
        session.close()

        await state.clear()
        await message.answer(
            f"✅ Товар '{data['product_name']}' успешно добавлен!",
            reply_markup=kb.admin_menu_keyboard()
        )

    except ValueError:
        await message.answer("❌ Введите размеры в правильном формате (числа через запятую):")


@admin_router.callback_query(F.data == "admin_products")
async def show_products(callback: CallbackQuery, state: FSMContext):
    await show_products_page(callback, 1)
    await callback.answer()


@admin_router.callback_query(F.data.startswith("products_page_"))
async def show_products_page_handler(callback: CallbackQuery):
    page = int(callback.data.split("_")[2])
    await show_products_page(callback, page)
    await callback.answer()


async def show_products_page(callback: CallbackQuery, page: int):
    session = Session()
    total_products = session.query(Product).count()

    if total_products == 0:
        await callback.message.answer("❌ Товаров нет")
        session.close()
        return

    total_pages = math.ceil(total_products / PRODUCTS_PER_PAGE)
    if page < 1:
        page = 1
    elif page > total_pages:
        page = total_pages

    offset = (page - 1) * PRODUCTS_PER_PAGE
    products = session.query(Product).offset(offset).limit(PRODUCTS_PER_PAGE).all()
    text = f"📦 Список товаров (Страница {page}/{total_pages}):\n\n"

    for i, product in enumerate(products, start=offset + 1):
        sizes = [str(size.size) for size in product.sizes]
        text += f"#{i}\n"
        text += f"👟 Название: {product.name}\n"
        text += f"💵 Цена: {product.price} руб\n"
        text += f"📁 Категория: {product.category.name}\n"
        text += f"📏 Размеры: {', '.join(sizes)}\n"
        text += f"🆔 ID: {product.id}\n"
        text += "─" * 30 + "\n\n"

    session.close()

    # Создаем клавиатуру пагинации
    builder = InlineKeyboardBuilder()
    if page > 1:
        builder.button(text="⬅️ Предыдущая",
                       callback_data=f"products_page_{page - 1}")
    if page < total_pages:
        builder.button(text="Следующая ➡️",
                       callback_data=f"products_page_{page + 1}")
    builder.button(text="⬅️ Назад к меню", callback_data="admin_menu")
    builder.adjust(2, 1)

    if hasattr(callback.message, 'edit_text'):
        await callback.message.edit_text(text,
                                         reply_markup=builder.as_markup())
    else:
        await callback.message.answer(text, reply_markup=builder.as_markup())


@admin_router.callback_query(F.data == "admin_delete_category")
async def delete_category_start(callback: CallbackQuery, state: FSMContext):
    session = Session()
    categories = session.query(Category).all()
    session.close()

    if not categories:
        await callback.message.answer(
            "❌ Категорий пока нет",
            reply_markup=kb.admin_menu_keyboard()
        )
        await callback.answer()
        return

    builder = InlineKeyboardBuilder()
    for category in categories:
        builder.button(
            text=f"🗑 {category.name}",
            callback_data=f"delete_category_{category.id}"
        )
    builder.adjust(1)

    await callback.message.answer(
        "Выберите категорию для удаления:",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@admin_router.callback_query(F.data.startswith("delete_category_"))
async def delete_category_confirm(callback: CallbackQuery, state: FSMContext):
    category_id = int(callback.data.split("_")[2])

    session = Session()
    category = session.query(Category).get(category_id)

    if not category:
        await callback.message.answer("❌ Категория не найдена")
        session.close()
        await callback.answer()
        return

    # Удаляем все товары этой категории и связанные размеры
    for product in category.products:
        for size in product.sizes:
            session.delete(size)
        session.delete(product)

    session.delete(category)
    session.commit()
    session.close()

    await callback.message.answer(
        f"✅ Категория '{category.name}' и её товары удалены",
        reply_markup=kb.admin_menu_keyboard()
    )
    await callback.answer()
