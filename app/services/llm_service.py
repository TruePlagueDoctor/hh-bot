import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import config
from app.db.models import User, Vacancy, GeneratedDocument, DocumentType


class LLMClient:
    def __init__(self, base_url: str, api_key: str, model_name: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model_name = model_name

    async def _request_chat(self, prompt: str) -> str:
        url = f"{self.base_url}/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
        }
        payload = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "system",
                    "content": "You are an assistant that writes CVs and cover letters in Russian.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.4,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        return data["choices"][0]["message"]["content"]


# Один глобальный клиент на модуль
llm_client = LLMClient(
    base_url=config.llm_base_url,
    api_key=config.llm_api_key,
    model_name=config.llm_model_name,
)


async def generate_adapted_resume(
    session: AsyncSession,
    user: User,
    vacancy: Vacancy,
) -> GeneratedDocument:
    prompt = f"""
Составь адаптированное резюме для вакансии.

Вакансия:
Название: {vacancy.title}
Компания: {vacancy.company}
Город: {vacancy.city}
Зарплата: от {vacancy.salary_from} до {vacancy.salary_to} {vacancy.currency}
Полное описание (если есть в raw): {vacancy.raw.get('snippet', {}) if vacancy.raw else ''}

Профиль кандидата:
ФИО: {user.full_name}
Город: {user.city}
Желаемая должность: {user.desired_position}
Навыки: {user.skills}
Базовое резюме:
{user.base_resume}

Сделай результат в виде аккуратного текстового резюме.
"""
    content = await llm_client._request_chat(prompt)

    doc = GeneratedDocument(
        user_id=user.id,
        vacancy_id=vacancy.id,
        doc_type=DocumentType.resume,
        content=content,
    )
    session.add(doc)
    await session.commit()
    await session.refresh(doc)
    return doc


async def generate_cover_letter(
    session: AsyncSession,
    user: User,
    vacancy: Vacancy,
) -> GeneratedDocument:
    prompt = f"""
Напиши короткое сопроводительное письмо к вакансии.

Вакансия:
Название: {vacancy.title}
Компания: {vacancy.company}
Город: {vacancy.city}

Кандидат:
ФИО: {user.full_name}
Город: {user.city}
Желаемая должность: {user.desired_position}
Основные навыки: {user.skills}

Напиши вежливое, убедительное письмо на русском.
"""
    content = await llm_client._request_chat(prompt)

    doc = GeneratedDocument(
        user_id=user.id,
        vacancy_id=vacancy.id,
        doc_type=DocumentType.cover_letter,
        content=content,
    )
    session.add(doc)
    await session.commit()
    await session.refresh(doc)
    return doc
