import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties  # ✅ новое

from app.config import config
from app.db.session import init_db
from app.handlers.start import register_start_handlers
from app.handlers.search_settings import register_search_settings_handlers
from app.handlers.vacancies import register_vacancy_handlers
from app.services.scheduler import setup_scheduler
from app.handlers.resume import register_resume_handlers
from app.handlers.history import register_history_handlers


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


async def main():
    # Инициализация БД
    await init_db(config.database_url)

    # ✅ Новая инициализация бота для aiogram 3.7+
    bot = Bot(
        token=config.token,
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML,
        ),
    )

    dp = Dispatcher()

    # Регистрация хендлеров
    register_start_handlers(dp)
    register_search_settings_handlers(dp)
    register_vacancy_handlers(dp)
    register_resume_handlers(dp)
    register_history_handlers(dp)
    # Планировщик рассылки
    scheduler = setup_scheduler(bot)
    scheduler.start()

    try:
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown(wait=False)


if __name__ == "__main__":
    asyncio.run(main())
