from aiogram import Router
from aiogram.types import Message, CallbackQuery
from filter.filter import IsUser, IsAdmin

fallback_router = Router()


# Обработчик неизвестных команд для пользователей
@fallback_router.message(IsUser())
async def user_unknown_command(message: Message):
    await message.answer("❌ Неизвестная команда. Используйте /start")


# Обработчик неизвестных callback'ов для пользователей  
@fallback_router.callback_query(IsUser())
async def user_unknown_callback(callback: CallbackQuery):
    await callback.answer("❌ Неизвестное действие")


@fallback_router.message(IsAdmin())
async def admin_unknown_command(message: Message):
    """Обработчик неизвестных команд для админов"""
    await message.answer(
        "👑 Неизвестная команда.\n\n"
        "Админские команды:\n"
        "• /start или /admin - админская панель\n")


@fallback_router.callback_query(IsAdmin())
async def admin_unknown_callback(callback: CallbackQuery):
    """Обработчик неизвестных callback'ов для админов"""
    await callback.answer("❌ Неизвестное админское действие")


@fallback_router.message()
async def universal_unknown_command(message: Message):
    """Универсальный обработчик для всех неизвестных команд"""
    await message.answer(
        "🤔 Я не понимаю эту команду.\n\n"
        "Попробуйте /start чтобы начать"
    )


@fallback_router.callback_query()
async def universal_unknown_callback(callback: CallbackQuery):
    """Универсальный обработчик для всех неизвестных callback'ов"""
    await callback.answer("⚠️ Это действие недоступно")