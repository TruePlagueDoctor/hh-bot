from datetime import datetime
from typing import Sequence

from sqlalchemy import select, insert
from sqlalchemy.ext.asyncio import AsyncSession

from .models import User, SearchFilter, Vacancy, UserVacancy, VacancyStatus


async def get_or_create_user(session: AsyncSession, telegram_id: int) -> User:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if user:
        return user
    user = User(telegram_id=telegram_id)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def update_user_profile(
    session: AsyncSession,
    user: User,
    full_name: str | None = None,
    city: str | None = None,
    desired_position: str | None = None,
    skills: str | None = None,
    base_resume: str | None = None,
) -> User:
    if full_name is not None:
        user.full_name = full_name
    if city is not None:
        user.city = city
    if desired_position is not None:
        user.desired_position = desired_position
    if skills is not None:
        user.skills = skills
    if base_resume is not None:
        user.base_resume = base_resume

    await session.commit()
    await session.refresh(user)
    return user


# app/db/crud.py

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import SearchFilter, User, CompanySize


async def upsert_search_filters(
    session: AsyncSession,
    user: User,
    position: str | None,
    city: str | None,
    min_salary: int | None,
    metro_stations: list[str] | None,
    freshness_days: int | None,
    employment_types: list[str] | None,
    experience_level: str | None,
    only_direct_employers: bool,
    company_size: CompanySize | None,
    only_top_companies: bool,
) -> SearchFilter:
    stmt = select(SearchFilter).where(SearchFilter.user_id == user.id)
    result = await session.execute(stmt)
    filt = result.scalar_one_or_none()

    if filt is None:
        filt = SearchFilter(user_id=user.id)
        session.add(filt)

    filt.position = position
    filt.city = city
    filt.min_salary = min_salary
    filt.metro_stations = metro_stations
    filt.freshness_days = freshness_days
    filt.employment_types = employment_types
    filt.experience_level = experience_level
    filt.only_direct_employers = only_direct_employers
    filt.company_size = company_size
    filt.only_top_companies = only_top_companies

    await session.commit()
    await session.refresh(filt)
    return filt


async def get_unsent_vacancies_for_user(
    session: AsyncSession,
    user: User,
    limit: int = 10,
) -> Sequence[Vacancy]:
    stmt = (
        select(Vacancy)
        .join(UserVacancy, UserVacancy.vacancy_id == Vacancy.id)
        .where(
            UserVacancy.user_id == user.id,
            UserVacancy.status == VacancyStatus.new,
        )
        .limit(limit)
    )
    result = await session.execute(stmt)
    return result.scalars().all()


async def mark_vacancies_as_sent(
    session: AsyncSession,
    user: User,
    vacancies: list[Vacancy],
) -> None:
    """
    Помечает вакансии для пользователя как отправленные.
    Никаких insert/upsert здесь не нужно — только update существующих связок.
    """
    if not vacancies:
        return

    vac_ids = [v.id for v in vacancies]

    stmt = select(UserVacancy).where(
        UserVacancy.user_id == user.id,
        UserVacancy.vacancy_id.in_(vac_ids),
    )
    result = await session.execute(stmt)
    links = result.scalars().all()

    for uv in links:
        uv.status = VacancyStatus.sent

    await session.commit()
