from datetime import time

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from app.db.session import get_session
from app.db.models import User, SearchFilter
from app.db.crud import get_unsent_vacancies_for_user, mark_vacancies_as_sent
from app.services.hh_service import fetch_vacancies_for_user


async def _daily_job(bot: Bot):
    # один общий проход по всем пользователям
    async for session in get_session():
        result = await session.execute(select(User))
        users = result.scalars().all()

    for user in users:
        async for session in get_session():
            result = await session.execute(
                select(SearchFilter).where(SearchFilter.user_id == user.id)
            )
            filt = result.scalar_one_or_none()
            if not filt:
                continue

            # получаем новые вакансии
            await fetch_vacancies_for_user(session, user, filt, limit=50)
            vacancies = await get_unsent_vacancies_for_user(session, user, limit=10)

            if not vacancies:
                continue

            # отправляем пользователю
            text_parts = []
            for v in vacancies:
                line = (
                    f"<b>{v.title}</b>\n"
                    f"{v.company} — {v.city}\n"
                    f"Зарплата: {v.salary_from}–{v.salary_to} {v.currency}\n"
                    f"<a href='{v.url}'>Ссылка на hh.ru</a>\n"
                )
                text_parts.append(line)

            text = "Вот новые вакансии для вас:\n\n" + "\n".join(text_parts)
            await bot.send_message(
                user.telegram_id, text, disable_web_page_preview=True
            )

            await mark_vacancies_as_sent(session, user, list(vacancies))


def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    # каждый день в 09:00
    scheduler.add_job(
        _daily_job,
        trigger="cron",
        hour=9,
        minute=0,
        args=(bot,),
    )
    return scheduler
