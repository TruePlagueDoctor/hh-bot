# app/handlers/search_settings.py

from aiogram import Router, F, Dispatcher
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)

from app.db.session import get_session
from app.db.crud import get_or_create_user, upsert_search_filters
from app.db.models import CompanySize

router = Router()


class SearchSettingsStates(StatesGroup):
    position = State()
    city = State()
    min_salary = State()
    metro = State()
    freshness = State()
    employment = State()
    experience = State()
    direct_only = State()
    company_size = State()
    top_companies = State()


# === Старт настройки ===


@router.message(F.text == "/search_settings")
async def cmd_search_settings(message: Message, state: FSMContext):
    await state.set_state(SearchSettingsStates.position)
    await message.answer("Какую должность ищем?")


# === Должность ===


@router.message(SearchSettingsStates.position)
async def set_position(message: Message, state: FSMContext):
    await state.update_data(position=(message.text or "").strip())
    await state.set_state(SearchSettingsStates.city)
    await message.answer("В каком городе ищем вакансии?")


# === Город ===


@router.message(SearchSettingsStates.city)
async def set_city(message: Message, state: FSMContext):
    await state.update_data(city=(message.text or "").strip())
    await state.set_state(SearchSettingsStates.min_salary)
    await message.answer(
        "Минимальная желаемая зарплата (число)?\nЕсли без ограничения — напиши 0."
    )


# === Минимальная зарплата ===


@router.message(SearchSettingsStates.min_salary)
async def set_min_salary(message: Message, state: FSMContext):
    txt = (message.text or "").strip()
    try:
        min_salary = int(txt)
        if min_salary < 0:
            raise ValueError
    except ValueError:
        await message.answer("Нужно неотрицательное число. Попробуй ещё раз.")
        return

    await state.update_data(min_salary=min_salary if min_salary > 0 else None)
    await state.set_state(SearchSettingsStates.metro)

    await message.answer(
        "Около каких станций метро искать вакансии?\n\n"
        "Перечисли через запятую (например: «Таганская, Китай-город»)\n"
        "или напиши «пропустить», если метро не важно."
    )


# === Станции метро ===


@router.message(SearchSettingsStates.metro)
async def set_metro(message: Message, state: FSMContext):
    text = (message.text or "").strip().lower()

    metro_stations: list[str] | None
    if text in ("пропустить", "/skip", "нет"):
        metro_stations = None
    else:
        raw = [p.strip() for p in (message.text or "").split(",")]
        metro_stations = [s for s in raw if s]

        if not metro_stations:
            metro_stations = None

    await state.update_data(metro_stations=metro_stations)
    await state.set_state(SearchSettingsStates.freshness)

    await message.answer("Свежесть вакансий в днях (1–3)?")


# === Свежесть вакансий ===


@router.message(SearchSettingsStates.freshness)
async def set_freshness(message: Message, state: FSMContext):
    try:
        freshness = int((message.text or "").strip())
        if freshness not in (1, 2, 3):
            raise ValueError
    except ValueError:
        await message.answer("Нужно число 1, 2 или 3.")
        return

    await state.update_data(freshness_days=freshness)

    # Клавиатура для типа занятости
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Полная занятость")],
            [KeyboardButton(text="Частичная занятость")],
            [KeyboardButton(text="Удалённая работа")],
            [KeyboardButton(text="Несколько вариантов (через запятую)")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

    await state.set_state(SearchSettingsStates.employment)
    await message.answer(
        "Тип занятости?\nМожешь перечислить через запятую: "
        "«Полная занятость, Удалённая работа».\n"
        "Если не важно — напиши «пропустить».",
        reply_markup=kb,
    )


# === Тип занятости ===


def _parse_employment_types(text: str) -> list[str] | None:
    """
    Преобразует русские названия в наши коды:
    full / part / remote
    """
    text = text.lower()
    if text in ("пропустить", "/skip", "неважно", "любая"):
        return None

    parts = [p.strip().lower() for p in text.split(",")]
    result: set[str] = set()

    for p in parts:
        if not p:
            continue
        if "полная" in p:
            result.add("full")
        if "частич" in p or "неполная" in p:
            result.add("part")
        if "удал" in p or "дистанц" in p:
            result.add("remote")

    return list(result) or None


@router.message(SearchSettingsStates.employment)
async def set_employment(message: Message, state: FSMContext):
    employment_types = _parse_employment_types(message.text or "")
    await state.update_data(employment_types=employment_types)

    await state.set_state(SearchSettingsStates.experience)

    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Нет опыта")],
            [KeyboardButton(text="1–3 года")],
            [KeyboardButton(text="3–6 лет")],
            [KeyboardButton(text="Более 6 лет")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

    await message.answer(
        "Какой опыт работы должен быть в вакансиях?\n" "Выбери один вариант.",
        reply_markup=kb,
    )


# === Опыт работы ===


def _parse_experience(text: str) -> str | None:
    t = (text or "").lower()
    if "нет" in t:
        return "no_experience"
    if "1" in t or "од" in t:
        return "1-3"
    if "3" in t and "6" in t:
        return "3-6"
    if "6" in t or "более" in t or "старше" in t:
        return "6+"
    return None


@router.message(SearchSettingsStates.experience)
async def set_experience(message: Message, state: FSMContext):
    exp = _parse_experience(message.text or "")
    if exp is None:
        await message.answer(
            "Не понял опыт. Напиши, пожалуйста, один из вариантов:\n"
            "«Нет опыта», «1–3 года», «3–6 лет», «Более 6 лет»."
        )
        return

    await state.update_data(experience_level=exp)

    await state.set_state(SearchSettingsStates.direct_only)

    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Да")],
            [KeyboardButton(text="Нет")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

    await message.answer(
        "Только прямые работодатели (без агентств)?",
        reply_markup=kb,
    )


# === Только прямые работодатели ===


def _parse_bool(text: str) -> bool | None:
    t = (text or "").lower()
    if t in ("да", "yes", "y", "true", "ага", "конечно"):
        return True
    if t in ("нет", "no", "n", "false", "неа"):
        return False
    return None


@router.message(SearchSettingsStates.direct_only)
async def set_direct_only(message: Message, state: FSMContext):
    val = _parse_bool(message.text or "")
    if val is None:
        await message.answer("Ответь, пожалуйста, «Да» или «Нет».")
        return

    await state.update_data(only_direct_employers=val)

    await state.set_state(SearchSettingsStates.company_size)

    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Малая компания")],
            [KeyboardButton(text="Средняя компания")],
            [KeyboardButton(text="Крупная компания")],
            [KeyboardButton(text="Пропустить")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

    await message.answer(
        "Размер компании?\n"
        "Можно выбрать: «Малая компания», «Средняя компания», "
        "«Крупная компания» или «Пропустить».",
        reply_markup=kb,
    )


# === Размер компании ===


def _parse_company_size(text: str) -> CompanySize | None | str:
    t = (text or "").lower()
    if "проп" in t or "не важн" in t or "любая" in t:
        return "skip"

    if "мал" in t:
        return CompanySize.small
    if "сред" in t:
        return CompanySize.medium
    if "круп" in t or "больш" in t:
        return CompanySize.large

    return None


@router.message(SearchSettingsStates.company_size)
async def set_company_size(message: Message, state: FSMContext):
    size = _parse_company_size(message.text or "")

    if size is None:
        await message.answer(
            "Не понял размер компании. Напиши: «Малая компания», "
            "«Средняя компания», «Крупная компания» или «Пропустить»."
        )
        return

    company_size = None if size == "skip" else size
    await state.update_data(company_size=company_size)

    await state.set_state(SearchSettingsStates.top_companies)

    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Да")],
            [KeyboardButton(text="Нет")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

    await message.answer(
        "Только ТОП-компании?\n(если «Да» — будут отфильтрованы только лучшие работодатели, "
        "когда это возможно).",
        reply_markup=kb,
    )


# === Только ТОП-компании ===


@router.message(SearchSettingsStates.top_companies)
async def set_top_companies(message: Message, state: FSMContext):
    val = _parse_bool(message.text or "")
    if val is None:
        await message.answer("Ответь, пожалуйста, «Да» или «Нет».")
        return

    await state.update_data(only_top_companies=val)

    data = await state.get_data()

    # Чистим FSM СТРОГО после того, как всё прочитали
    await state.clear()

    # Убираем клавиатуру
    rm = ReplyKeyboardRemove()

    async for session in get_session():
        user = await get_or_create_user(session, message.from_user.id)
        await upsert_search_filters(
            session,
            user,
            position=data.get("position"),
            city=data.get("city"),
            min_salary=data.get("min_salary"),
            metro_stations=data.get("metro_stations"),
            freshness_days=data.get("freshness_days"),
            employment_types=data.get("employment_types"),
            experience_level=data.get("experience_level"),
            only_direct_employers=data.get("only_direct_employers", True),
            company_size=data.get("company_size"),
            only_top_companies=data.get("only_top_companies", False),
        )

    await message.answer(
        "Фильтры поиска сохранены ✅\nМожешь проверить вакансии командой /vacancies",
        reply_markup=rm,
    )


def register_search_settings_handlers(dp: Dispatcher):
    dp.include_router(router)
