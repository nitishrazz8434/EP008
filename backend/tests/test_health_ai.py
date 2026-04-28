from __future__ import annotations

from app.data_sources.registry import get_indicator
from app.models import ChatRequest, DataPoint, Series
from app.services.analytics import analyze_series
from app.services.nlp import make_plan


def test_query_model_detects_forecast_malaria_india() -> None:
    plan, indicator = make_plan(ChatRequest(message="forecast malaria in india next 3 years"))

    assert plan.intent == "forecast"
    assert indicator.id == "malaria_incidence"
    assert plan.countries == ["IND"]
    assert plan.forecast_years == 3


def test_query_model_detects_risk_for_tuberculosis() -> None:
    plan, indicator = make_plan(ChatRequest(message="is tuberculosis outbreak risk increasing in india"))

    assert plan.intent == "risk"
    assert indicator.id == "tb_incidence"
    assert plan.countries == ["IND"]


def test_query_model_detects_required_project_examples() -> None:
    compare_plan, compare_indicator = make_plan(ChatRequest(message="Compare malaria in India and Brazil"))
    forecast_plan, forecast_indicator = make_plan(ChatRequest(message="Forecast TB in India for 3 years"))
    trend_plan, trend_indicator = make_plan(ChatRequest(message="Is maternal mortality improving in India?"))

    assert compare_plan.intent == "compare"
    assert compare_indicator.id == "malaria_incidence"
    assert compare_plan.countries == ["IND", "BRA"]

    assert forecast_plan.intent == "forecast"
    assert forecast_indicator.id == "tb_incidence"
    assert forecast_plan.forecast_years == 3

    assert trend_plan.intent == "trend"
    assert trend_indicator.id == "maternal_mortality"


def test_core_health_indicators_are_who_first() -> None:
    expenditure_plan, expenditure_indicator = make_plan(ChatRequest(message="health expenditure in India"))
    diabetes_plan, diabetes_indicator = make_plan(ChatRequest(message="diabetes prevalence in India"))

    assert expenditure_plan.indicator_id == "health_expenditure_gdp"
    assert expenditure_indicator.source == "WHO"

    assert diabetes_plan.indicator_id == "diabetes_prevalence"
    assert diabetes_indicator.source == "WHO"


def test_damped_forecast_avoids_immediate_zero_collapse() -> None:
    indicator = get_indicator("malaria_incidence")
    series = Series(
        country_code="IND",
        country_name="India",
        points=[
            DataPoint(year=2018, value=3.43),
            DataPoint(year=2019, value=2.84),
            DataPoint(year=2020, value=2.53),
            DataPoint(year=2021, value=2.50),
            DataPoint(year=2022, value=1.40),
            DataPoint(year=2023, value=1.34),
            DataPoint(year=2024, value=1.48),
        ],
    )

    insight = analyze_series(series, indicator, horizon=3)

    assert len(insight.forecast) == 3
    assert insight.forecast[0].value > 0
    assert insight.forecast[-1].value > 0
