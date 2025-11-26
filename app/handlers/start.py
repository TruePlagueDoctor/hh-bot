# app/handlers/start.py

from aiogram import Router, F, Dispatcher
from aiogram.filters import CommandStart, StateFilter
from aiogram.types import Message

from app.db.session import get_session
from app.db.crud import get_or_create_user, update_user_profile
from aiogram.filters import CommandStart, StateFilter
from app.utils.keyboards import main_menu_keyboard

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    async for session in get_session():
        await get_or_create_user(session, message.from_user.id)

    await message.answer(
        "Привет! Я бот-поисковик вакансий.\n\n"
        "Давай заполним базовый профиль.\n"
        "Отправь мне сообщение в формате:\n\n"
        "<b>ФИО</b>\nГород\nЖелаемая должность\nНавыки через запятую\n\n"
        "Или просто напиши /skip, чтобы пропустить.\n\n"
        "Также можешь пользоваться кнопками внизу 👇",
        reply_markup=main_menu_keyboard(),
    )


# ⬇️ ВАЖНО: добавили StateFilter(None)
@router.message(
    StateFilter(None),
    F.text
    & ~F.text.startswith("/")
    & F.text.not_in(
        {
            "🔍 Настроить поиск",
            "📨 Вакансии",
            "📄 Моё резюме",
            "📜 История",
        }
    ),
)
async def handle_profile_text(message: Message):
    text = message.text or ""

    if text.strip().lower() == "/skip":
        await message.answer(
            "Ок, профиль можно заполнить позже командой /search_settings"
        )
        return

    lines = text.splitlines()
    if len(lines) < 3:
        await message.answer("Слишком мало данных. Дай хотя бы ФИО, город и должность.")
        return

    full_name = lines[0].strip()
    city = lines[1].strip()
    desired_position = lines[2].strip()
    skills = ",".join(line.strip() for line in lines[3:]) if len(lines) > 3 else ""

    async for session in get_session():
        user = await get_or_create_user(session, message.from_user.id)
        await update_user_profile(
            session,
            user,
            full_name=full_name,
            city=city,
            desired_position=desired_position,
            skills=skills,
        )

    await message.answer(
        "Профиль сохранён ✅\n"
        "Теперь можешь настроить фильтры поиска: /search_settings"
    )


def register_start_handlers(dp: Dispatcher):
    dp.include_router(router)
