from dotenv import load_dotenv
import sqlalchemy
from database.models import create_tables
from sqlalchemy.orm import sessionmaker
from config.config import load_config  # Импортируем наш конфиг

load_dotenv()

# Загружаем конфиг
config = load_config()


def create_connection():
    DSN = f"{config.database.driver}://{config.database.user}:{config.database.password}@{config.database.host}:{config.database.port}/{config.database.name}"
    engine = sqlalchemy.create_engine(DSN)
    return engine


# Создаём engine используя конфиг
engine = create_connection()

# Создаём все таблицы
create_tables(engine)

Session = sessionmaker(bind=engine)
