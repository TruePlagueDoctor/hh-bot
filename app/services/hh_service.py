# app/services/hh_service.py

from datetime import datetime, timedelta
from typing import Any
import logging

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import SearchFilter, Vacancy, User, UserVacancy, VacancyStatus

logger = logging.getLogger(__name__)

HH_API_URL = "https://api.hh.ru/vacancies"

# Простейший маппинг городов в area-id hh.ru
CITY_TO_AREA_ID: dict[str, int] = {
    "санкт-петербург": 2,
    "спб": 2,
    "питер": 2,
    "петербург": 2,
    "москва": 1,
    "moscow": 1,
    "saint petersburg": 2,
}


def _normalize_city_name(city: str | None) -> str | None:
    if not city:
        return None
    return city.strip().lower()


def _build_hh_params(user: User, filt: SearchFilter) -> dict[str, Any]:
    params: dict[str, Any] = {}

    # 👉 Приоритет: позиция из фильтра, потом из профиля
    search_text = (filt.position or "").strip()
    if not search_text:
        search_text = (user.desired_position or "").strip()

    if search_text:
        params["text"] = search_text
        # 🔍 ВАЖНО: ищем только в названии вакансии, а не везде
        params["search_field"] = "name"

    # дальше всё как у тебя: area, salary, date_from и т.д.
    city_norm = _normalize_city_name(filt.city or user.city)
    if city_norm:
        area_id = CITY_TO_AREA_ID.get(city_norm)
        if area_id is not None:
            params["area"] = area_id
        else:
            logger.info("Unknown city for HH area mapping: %r", city_norm)

    # Минимальная зарплата
    if filt.min_salary:
        params["salary"] = filt.min_salary
        params["only_with_salary"] = True

    # Свежесть
    days = filt.freshness_days or 1
    date_from = datetime.utcnow() - timedelta(days=days)
    params["date_from"] = date_from.isoformat(timespec="seconds")

    # Опыт работы — наши коды -> коды hh
    # https://api.hh.ru/openapi/redoc#tag/Obshie-spravochniki/operation/get-experience
    exp_map = {
        "no_experience": "noExperience",
        "1-3": "between1And3",
        "3-6": "between3And6",
        "6+": "moreThan6",
    }
    if filt.experience_level and filt.experience_level in exp_map:
        params["experience"] = exp_map[filt.experience_level]

    # Тип занятости / расписание.
    # В hh есть:
    #   employment: full, part, project, volunteer, probation
    #   schedule: fullDay, shift, flexible, remote, flyInFlyOut
    if filt.employment_types:
        # Небольшая эвристика:
        emps: set[str] = set()
        schedules: set[str] = set()
        for t in filt.employment_types:
            if t == "full":
                emps.add("full")
            if t == "part":
                emps.add("part")
            if t == "remote":
                schedules.add("remote")

        # hh позволяет передавать массивы employment/schedule
        # (httpx сам сделает repeated params)
        if emps:
            params["employment"] = list(emps)
        if schedules:
            params["schedule"] = list(schedules)

    # Только прямые работодатели — для hh есть параметр only_with_salary, но
    # фильтра "только прямые" нет, это обычно делается на стороне клиента.
    # Поэтому просто игнорируем, но оставляем поле в БД на будущее.

    # Размер компании / ТОП-компании — у hh нет прямых параметров под это,
    # тоже можно реализовывать позже через доп. фильтрацию raw-данных.

    # Метро тоже пока пропускаем (там нужна отдельная справочника станций + id)

    logger.info("Built HH params: %s", params)
    return params


async def fetch_vacancies_for_user(
    session: AsyncSession,
    user: User,
    filt: SearchFilter,
    limit: int = 50,
) -> list[Vacancy]:
    params = _build_hh_params(user, filt)
    params["per_page"] = limit

    logger.info("Requesting HH vacancies with params: %s", params)

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(HH_API_URL, params=params)
        logger.info("HH response status: %s", resp.status_code)
        resp.raise_for_status()
        data = resp.json()

    items = data.get("items", [])
    logger.info("HH returned %d items", len(items))

    # 👉 Дополнительно фильтруем по названию, если указана позиция
    if filt.position:
        p = filt.position.strip().lower()
        items = [item for item in items if p in (item.get("name") or "").lower()]
        logger.info("Filtered items by position '%s': %d left", p, len(items))

    new_vacancies: list[Vacancy] = []

    existing_stmt = select(Vacancy).where(
        Vacancy.hh_id.in_([item["id"] for item in items])
    )
    result = await session.execute(existing_stmt)
    existing_by_hh_id = {v.hh_id: v for v in result.scalars().all()}

    for item in items:
        hh_id = item["id"]
        vac = existing_by_hh_id.get(hh_id)
        if not vac:
            vac = Vacancy(
                hh_id=hh_id,
                title=item.get("name"),
                company=(item.get("employer") or {}).get("name"),
                city=(item.get("area") or {}).get("name"),
                url=item.get("alternate_url"),
                salary_from=(item.get("salary") or {}).get("from"),
                salary_to=(item.get("salary") or {}).get("to"),
                currency=(item.get("salary") or {}).get("currency"),
                raw=item,
            )
            session.add(vac)
            await session.flush()
            new_vacancies.append(vac)

        uv_stmt = select(UserVacancy).where(
            UserVacancy.user_id == user.id,
            UserVacancy.vacancy_id == vac.id,
        )
        uv_result = await session.execute(uv_stmt)
        uv = uv_result.scalar_one_or_none()
        if uv is None:
            session.add(
                UserVacancy(
                    user_id=user.id,
                    vacancy_id=vac.id,
                    status=VacancyStatus.new,
                )
            )

    await session.commit()
    return new_vacancies
