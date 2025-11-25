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


async def upsert_search_filters(
    session: AsyncSession, user: User, **kwargs
) -> SearchFilter:
    result = await session.execute(
        select(SearchFilter).where(SearchFilter.user_id == user.id)
    )
    filt = result.scalar_one_or_none()
    if filt is None:
        filt = SearchFilter(user_id=user.id)
        session.add(filt)

    for k, v in kwargs.items():
        setattr(filt, k, v)

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
):
    now = datetime.utcnow()
    for vac in vacancies:
        stmt = (
            insert(UserVacancy)
            .values(
                user_id=user.id,
                vacancy_id=vac.id,
                status=VacancyStatus.sent,
                sent_at=now,
            )
            .on_conflict_do_update(
                index_elements=["user_id", "vacancy_id"],
                set_={"status": VacancyStatus.sent, "sent_at": now},
            )
        )
        await session.execute(stmt)
    await session.commit()
