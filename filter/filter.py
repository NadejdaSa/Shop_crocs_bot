from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery
from config.config import load_config

config = load_config()


class IsAdmin(BaseFilter):
    async def __call__(self, message: Message | CallbackQuery) -> bool:
        return message.from_user.id in config.admin_ids


class IsUser(BaseFilter):
    async def __call__(self, message: Message | CallbackQuery) -> bool:
        return message.from_user.id not in config.admin_ids
