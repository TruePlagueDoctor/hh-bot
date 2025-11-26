# app/handlers/history.py

from aiogram import Router, F, Dispatcher
from aiogram.types import Message
from sqlalchemy import select

from app.db.session import get_session
from app.db.models import (
    User,
    Vacancy,
    UserVacancy,
    GeneratedDocument,
    DocumentType,
    VacancyStatus,
)

router = Router()


@router.message(F.text.in_({"/history", "📜 История"}))
async def cmd_history(message: Message):
    """
    Показывает историю последних вакансий пользователя:
    - что за вакансия;
    - статус (отправлена, пропущена, новые документы);
    - наличие резюме / сопроводительного;
    - ссылка.
    """
    async for session in get_session():
        # 1) Находим пользователя
        result = await session.execute(
            select(User).where(User.telegram_id == message.from_user.id)
        )
        user = result.scalar_one_or_none()
        if not user:
            await message.answer("Сначала выполните /start.")
            return

        # 2) Берём последние 10 записей user_vacancies
        uv_stmt = (
            select(UserVacancy, Vacancy)
            .join(Vacancy, Vacancy.id == UserVacancy.vacancy_id)
            .where(UserVacancy.user_id == user.id)
            .order_by(UserVacancy.id.desc())
            .limit(10)
        )
        uv_result = await session.execute(uv_stmt)
        rows = uv_result.all()

        if not rows:
            await message.answer("История пока пуста. Попробуйте команду /vacancies.")
            return

        # Соберём id вакансий, чтобы одним запросом вытащить документы
        vacancy_ids = {vac.id for (_uv, vac) in rows}

        doc_stmt = select(GeneratedDocument).where(
            GeneratedDocument.user_id == user.id,
            GeneratedDocument.vacancy_id.in_(vacancy_ids),
        )
        doc_result = await session.execute(doc_stmt)
        docs = doc_result.scalars().all()

        # Сгруппируем документы по вакансии
        docs_by_vacancy: dict[int, dict[str, bool]] = {}
        for d in docs:
            info = docs_by_vacancy.setdefault(
                d.vacancy_id,
                {"resume": False, "cover": False},
            )
            if d.doc_type == DocumentType.resume:
                info["resume"] = True
            elif d.doc_type == DocumentType.cover_letter:
                info["cover"] = True

    # 3) Формируем красивый ответ
    lines: list[str] = ["<b>История последних вакансий:</b>\n"]

    status_map = {
        VacancyStatus.new: "новая",
        VacancyStatus.sent: "отправлена в рассылке",
        VacancyStatus.skipped: "помечена как неинтересная",
    }

    for idx, (uv, vac) in enumerate(rows, start=1):
        doc_flags = docs_by_vacancy.get(vac.id, {"resume": False, "cover": False})

        status_text = status_map.get(uv.status, "неизвестный статус")
        resume_text = "есть" if doc_flags["resume"] else "нет"
        cover_text = "есть" if doc_flags["cover"] else "нет"

        salary_text = "не указана"
        if vac.salary_from or vac.salary_to:
            _from = vac.salary_from or ""
            _to = vac.salary_to or ""
            cur = vac.currency or ""
            salary_text = f"{_from}–{_to} {cur}".strip("– ")

        lines.append(
            f"{idx}. <b>{vac.title}</b>\n"
            f"{vac.company or 'Компания не указана'} — {vac.city or 'Город не указан'}\n"
            f"Статус: {status_text}\n"
            f"Резюме: {resume_text}, Cover letter: {cover_text}\n"
            f"Зарплата: {salary_text}\n"
            f"{vac.url or ''}\n"
        )

    await message.answer("\n".join(lines))


def register_history_handlers(dp: Dispatcher):
    dp.include_router(router)
