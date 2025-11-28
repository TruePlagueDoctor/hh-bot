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


async def evaluate_vacancy_comfort(user: User, vacancy: Vacancy) -> str:
    """
    Оценка вакансии по "приятности" для работника.
    Возвращает готовый текст с оценкой и кратким разбором.
    НИЧЕГО не сохраняем в БД, просто считаем на лету.
    """
    # Соберём краткое описание вакансии
    desc_lines = [
        f"Название: {vacancy.title or 'не указано'}",
        f"Компания: {vacancy.company or 'не указано'}",
        f"Город: {vacancy.city or 'не указано'}",
    ]

    if vacancy.salary_from or vacancy.salary_to:
        salary_parts = []
        if vacancy.salary_from:
            salary_parts.append(f"от {vacancy.salary_from}")
        if vacancy.salary_to:
            salary_parts.append(f"до {vacancy.salary_to}")
        if vacancy.currency:
            salary_parts.append(vacancy.currency)
        desc_lines.append("Зарплата: " + " ".join(salary_parts))
    else:
        desc_lines.append("Зарплата: не указана")

    # немного контекста по пользователю (желательная должность и навыки)
    profile_parts = []
    if user.desired_position:
        profile_parts.append(
            f"Желаемая должность пользователя: {user.desired_position}"
        )
    if user.skills:
        profile_parts.append(f"Навыки пользователя: {user.skills}")

    vacancy_text = "\n".join(desc_lines)
    profile_text = (
        "\n".join(profile_parts)
        if profile_parts
        else "Информация о пользователе минимальна."
    )

    prompt = f"""
Ты карьерный консультант, который помогает оценить вакансию с точки зрения комфортности для сотрудника.

У тебя есть:

Вакансия:
{vacancy_text}

Профиль пользователя:
{profile_text}

Твоя задача:

1. Дай общую оценку комфортности вакансии для работника по шкале от 1 до 10, где:
   1–3 — очень сомнительно,
   4–6 — средне, есть заметные минусы,
   7–8 — в целом хорошая вакансия,
   9–10 — отличные условия.

2. Отметь:
   - условия труда (график, формат, возможная нагрузка, по косвенным признакам);
   - уровень зарплаты (ориентировочно, даже если не указан — укажи, что это риск);
   - стабильность / репутация работодателя (по названию, если можно предположить);
   - перспективы развития.

3. Дай вывод: "Краткий вердикт" — в 1–2 предложениях.

Ответ верни в структурированном виде:

Оценка: X/10
Плюсы:
- ...
Минусы:
- ...
Риски:
- ...
Краткий вердикт:
... (1–2 предложения)
"""

    content = await llm_client._request_chat(prompt)
    return content
