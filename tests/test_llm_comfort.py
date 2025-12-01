# tests/test_llm_comfort.py

import pytest
from types import SimpleNamespace

from app.services import llm_service


@pytest.mark.asyncio
async def test_evaluate_vacancy_comfort_monkeypatched(monkeypatch):
    # Фейковый user и vacancy
    user = SimpleNamespace(
        desired_position="Python-разработчик",
        skills="Python, Django, SQL",
    )
    vacancy = SimpleNamespace(
        title="Python developer",
        company="ООО Рога и Копыта",
        city="Санкт-Петербург",
        salary_from=150000,
        salary_to=200000,
        currency="RUR",
    )

    async def fake_request_chat(prompt: str) -> str:
        # Здесь можно дополнительно проверять prompt, если хочешь
        assert "Python developer" in prompt
        assert "ООО Рога и Копыта" in prompt
        return (
            "Оценка: 8/10\n"
            "Плюсы:\n- нормальная зарплата\n- адекватная компания\n"
            "Минусы:\n- неясна нагрузка\n"
            "Риски:\n- возможны переработки\n"
            "Краткий вердикт:\nВыглядит комфортной вакансией."
        )

    # Подменяем llm_client._request_chat
    monkeypatch.setattr(llm_service.llm_client, "_request_chat", fake_request_chat)

    text = await llm_service.evaluate_vacancy_comfort(user, vacancy)

    assert "Оценка:" in text
    assert "8/10" in text
    assert "комфортной вакансией" in text
