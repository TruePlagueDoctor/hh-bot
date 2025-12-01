# tests/test_search_settings_parsers.py

import pytest

from app.handlers.search_settings import (
    _parse_employment_types,
    _parse_experience,
    _parse_bool,
    _parse_company_size,
)
from app.db.models import CompanySize


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Полная занятость", ["full"]),
        ("Частичная занятость", ["part"]),
        ("Удалённая работа", ["remote"]),
        ("Полная занятость, Удалённая работа", ["full", "remote"]),
        ("пропустить", None),
        ("неважно", None),
    ],
)
def test_parse_employment_types(text, expected):
    result = _parse_employment_types(text)
    if expected is None:
        assert result is None
    else:
        assert sorted(result) == sorted(expected)


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Нет опыта", "no_experience"),
        ("1–3 года", "1-3"),
        ("1-3 года", "1-3"),
        ("3–6 лет", "3-6"),
        ("Более 6 лет", "6+"),
        ("старше 6 лет", "6+"),
        ("что-то странное", None),
    ],
)
def test_parse_experience(text, expected):
    assert _parse_experience(text) == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Да", True),
        ("да", True),
        ("нет", False),
        ("No", False),
        ("ага", True),
        ("неа", False),
        ("что-то", None),
    ],
)
def test_parse_bool(text, expected):
    assert _parse_bool(text) == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Малая компания", CompanySize.small),
        ("Средняя компания", CompanySize.medium),
        ("Крупная компания", CompanySize.large),
        ("пропустить", "skip"),
        ("не важно", "skip"),
        ("что-то левое", None),
    ],
)
def test_parse_company_size(text, expected):
    assert _parse_company_size(text) == expected
