# tests/test_hh_service_params.py

from types import SimpleNamespace

from app.services.hh_service import _build_hh_params


def make_user(
    desired_position: str | None = None,
    city: str | None = None,
):
    return SimpleNamespace(
        desired_position=desired_position,
        city=city,
    )


def make_filter(
    position: str | None = None,
    city: str | None = None,
    min_salary: int | None = None,
    freshness_days: int | None = None,
    experience_level: str | None = None,
    employment_types: list[str] | None = None,
):
    return SimpleNamespace(
        position=position,
        city=city,
        min_salary=min_salary,
        freshness_days=freshness_days,
        employment_types=employment_types,
        experience_level=experience_level,
        metro_stations=None,
        only_direct_employers=True,
        company_size=None,
        only_top_companies=False,
    )


def test_build_hh_params_position_priority_filter_over_user():
    user = make_user(desired_position="Программист", city="Санкт-Петербург")
    filt = make_filter(position="Повар", city="Санкт-Петербург", freshness_days=2)

    params = _build_hh_params(user, filt)

    assert params["text"] == "Повар"
    assert params.get("search_field") == "name"
    assert params["area"] == 2  # СПб
    assert "date_from" in params


def test_build_hh_params_min_salary_and_only_with_salary():
    user = make_user(desired_position="Программист", city="Москва")
    filt = make_filter(
        position="Программист", city="Москва", min_salary=100000, freshness_days=1
    )

    params = _build_hh_params(user, filt)

    assert params["salary"] == 100000
    assert params["only_with_salary"] is True


def test_build_hh_params_experience_and_employment():
    user = make_user(desired_position="Программист", city="Москва")
    filt = make_filter(
        position="Программист",
        city="Москва",
        experience_level="1-3",
        freshness_days=3,
        employment_types=["full", "remote"],
    )

    params = _build_hh_params(user, filt)

    assert params["experience"] == "between1And3"
    assert "employment" in params
    assert "full" in params["employment"]
    assert "schedule" in params
    assert "remote" in params["schedule"]
