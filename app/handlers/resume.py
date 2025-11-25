# app/handlers/resume.py

from aiogram import Router, F, Dispatcher
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.db.session import get_session
from app.db.crud import get_or_create_user, update_user_profile

router = Router()


class ResumeStates(StatesGroup):
    waiting_text = State()


@router.message(F.text == "/resume")
async def cmd_resume(message: Message, state: FSMContext):
    """
    Старт команды /resume — просим пользователя прислать базовое резюме.
    """
    await state.set_state(ResumeStates.waiting_text)
    await message.answer(
        "Отправь мне свой базовый текст резюме.\n\n"
        "Можно просто скопировать содержимое из файла.\n"
        "Когда закончишь, просто отправь одним сообщением.\n\n"
        "Если передумал — напиши /cancel."
    )


@router.message(ResumeStates.waiting_text, F.text == "/cancel")
async def cancel_resume(message: Message, state: FSMContext):
    """
    Отмена ввода резюме.
    """
    await state.clear()
    await message.answer(
        "Ок, ввод резюме отменён. Ты можешь вернуться к этому позже командой /resume."
    )


@router.message(ResumeStates.waiting_text)
async def save_resume(message: Message, state: FSMContext):
    """
    Сохраняем текст резюме в базу.
    """
    text = (message.text or "").strip()
    if not text:
        await message.answer("Пустое резюме не подойдёт 🙂 Пришли, пожалуйста, текст.")
        return

    async for session in get_session():
        user = await get_or_create_user(session, message.from_user.id)
        await update_user_profile(session, user, base_resume=text)

    await state.clear()
    await message.answer(
        "Базовое резюме сохранено ✅\nТеперь я буду использовать его при генерации адаптированных версий."
    )


def register_resume_handlers(dp: Dispatcher):
    dp.include_router(router)
