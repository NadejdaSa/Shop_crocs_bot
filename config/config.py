from dataclasses import dataclass
from dotenv import load_dotenv
import os

load_dotenv()


@dataclass
class BotConfig:
    token: str
    provider_token: str


@dataclass
class DatabaseConfig:
    driver: str
    user: str
    password: str
    host: str
    port: str
    name: str


@dataclass
class Config:
    bot: BotConfig
    database: DatabaseConfig
    admin_ids: list[int]


def load_config() -> Config:
    # Получаем строку с ID админов из .env
    admin_ids_str = os.getenv("ADMIN_IDS", "").strip()
    admin_ids = []
    if admin_ids_str:
        admin_ids = [int(id_str.strip()) for id_str in admin_ids_str.split(",")]

    return Config(
        bot=BotConfig(
            token=os.getenv("BOT_TOKEN"),
            provider_token=os.getenv("PROVIDER_TOKEN")
        ),
        database=DatabaseConfig(
            driver=os.getenv("DB_DRIVER"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            name=os.getenv("DB_NAME")
        ),
        admin_ids=admin_ids
    )
