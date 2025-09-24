from aiogram import Bot
from aiogram.types import BotCommand
from aiogram.types import BotCommand, BotCommandScopeDefault, BotCommandScopeChat

from config.config import load_config

config = load_config()
ADMIN_IDS = config.admin_ids


async def set_main_menu(bot: Bot):
    # меню для обычных пользователей
    user_commands = [
        BotCommand(command="/start", description="Начать работу"),
        BotCommand(command="/show_cart", description="Посмотреть корзину"),
    ]

    # меню для админов
    admin_commands = [
        BotCommand(command="/start", description="Начать работу"),
        BotCommand(command="/admin", description="Начать работу"),
    ]

    # применяем меню для всех по умолчанию (обычные юзеры)
    await bot.set_my_commands(user_commands, scope=BotCommandScopeDefault())

    # переопределяем меню для каждого админа
    for admin_id in ADMIN_IDS:
        await bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=admin_id))
