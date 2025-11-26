from aiogram import Router, F, Dispatcher
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
    BufferedInputFile,
)
from sqlalchemy import select

from app.db.session import get_session
from app.db.models import User, Vacancy, UserVacancy, SearchFilter
from app.db.crud import get_unsent_vacancies_for_user, mark_vacancies_as_sent
from app.services.llm_service import generate_adapted_resume, generate_cover_letter
from app.services.hh_service import fetch_vacancies_for_user
from app.utils.pdf_utils import render_text_to_pdf

router = Router()


def vacancy_keyboard(vacancy_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📄 Сгенерировать резюме",
                    callback_data=f"gen_resume:{vacancy_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="✉️ Сопроводительное",
                    callback_data=f"gen_cover:{vacancy_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Неинтересно",
                    callback_data=f"skip:{vacancy_id}",
                )
            ],
        ]
    )


@router.message(F.text.in_({"/vacancies", "📨 Вакансии"}))
async def cmd_vacancies(message: Message):
    async for session in get_session():
        # 1) находим пользователя
        result = await session.execute(
            select(User).where(User.telegram_id == message.from_user.id)
        )
        user = result.scalar_one_or_none()
        if not user:
            await message.answer("Сначала выполните /start")
            return

        # 2) вытаскиваем фильтры
        filt_result = await session.execute(
            select(SearchFilter).where(SearchFilter.user_id == user.id)
        )
        filt = filt_result.scalar_one_or_none()
        if not filt:
            await message.answer("Сначала настройте фильтры: /search_settings")
            return

        # 3) тянем свежие вакансии из hh.ru
        try:
            await fetch_vacancies_for_user(session, user, filt, limit=20)
        except Exception as e:
            await message.answer(f"Не удалось получить вакансии с hh.ru: {e}")
            return

        # 4) берём новые (не отправленные ещё) вакансии
        vacancies = await get_unsent_vacancies_for_user(session, user, limit=5)

    if not vacancies:
        await message.answer("Пока нет новых вакансий по вашим фильтрам.")
        return

    for v in vacancies:
        salary_text = "не указана"
        if v.salary_from or v.salary_to:
            _from = v.salary_from or ""
            _to = v.salary_to or ""
            cur = v.currency or ""
            salary_text = f"{_from}–{_to} {cur}".strip("– ")

        text = (
            f"<b>{v.title}</b>\n"
            f"{v.company} — {v.city}\n"
            f"Зарплата: {salary_text}\n"
            f"<a href='{v.url}'>Ссылка на hh.ru</a>"
        )
        await message.answer(
            text,
            reply_markup=vacancy_keyboard(v.id),
            disable_web_page_preview=True,
        )

    # помечаем эти вакансии как отправленные
    async for session in get_session():
        await mark_vacancies_as_sent(session, user, list(vacancies))


@router.callback_query(F.data.startswith("gen_resume:"))
async def cb_gen_resume(callback: CallbackQuery):
    vacancy_id = int(callback.data.split(":", 1)[1])

    async for session in get_session():
        result = await session.execute(
            select(User).where(User.telegram_id == callback.from_user.id)
        )
        user = result.scalar_one()
        vacancy = await session.get(Vacancy, vacancy_id)

        doc = await generate_adapted_resume(session, user, vacancy)

    # 1) Отправляем текст как раньше
    await callback.message.answer("Готовое резюме:\n\n" + doc.content)

    # 2) Формируем PDF
    pdf_bytes = render_text_to_pdf(
        doc.content, title=vacancy.title if vacancy else "Резюме"
    )
    input_file = BufferedInputFile(pdf_bytes, filename="resume.pdf")

    # 3) Отправляем PDF как документ
    await callback.message.answer_document(
        input_file,
        caption="Резюме в формате PDF",
    )

    await callback.answer()


@router.callback_query(F.data.startswith("gen_cover:"))
async def cb_gen_cover(callback: CallbackQuery):
    vacancy_id = int(callback.data.split(":", 1)[1])

    async for session in get_session():
        result = await session.execute(
            select(User).where(User.telegram_id == callback.from_user.id)
        )
        user = result.scalar_one()
        vacancy = await session.get(Vacancy, vacancy_id)

        doc = await generate_cover_letter(session, user, vacancy)

    # 1) Текст
    await callback.message.answer("Сопроводительное письмо:\n\n" + doc.content)

    # 2) PDF
    pdf_bytes = render_text_to_pdf(
        doc.content, title=f"Сопроводительное: {vacancy.title if vacancy else ''}"
    )
    input_file = BufferedInputFile(pdf_bytes, filename="cover_letter.pdf")

    await callback.message.answer_document(
        input_file,
        caption="Сопроводительное письмо в PDF",
    )

    await callback.answer()


@router.callback_query(F.data.startswith("skip:"))
async def cb_skip(callback: CallbackQuery):
    vacancy_id = int(callback.data.split(":", 1)[1])

    async for session in get_session():
        result = await session.execute(
            select(User).where(User.telegram_id == callback.from_user.id)
        )
        user = result.scalar_one()
        uv_result = await session.execute(
            select(UserVacancy).where(
                UserVacancy.user_id == user.id,
                UserVacancy.vacancy_id == vacancy_id,
            )
        )
        uv = uv_result.scalar_one_or_none()
        if uv:
            uv.skipped = True
            await session.commit()

    await callback.answer("Ок, скрываю эту вакансию.")
    # Можно удалить сообщение с вакансией
    try:
        await callback.message.delete()
    except Exception:
        pass


def register_vacancy_handlers(dp: Dispatcher) -> None:
    """Вызывается из main.py для подключения роутера."""
    dp.include_router(router)
