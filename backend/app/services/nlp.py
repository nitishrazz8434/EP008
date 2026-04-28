from __future__ import annotations

import re

from app.data_sources.registry import COUNTRIES, INDICATORS, IndicatorDef, match_countries, match_indicator
from app.models import ChatRequest, QueryPlan, Series, SeriesInsight
from app.services.query_model import get_query_model
from app.settings import DEFAULT_FORECAST_YEARS

YEAR_RE = re.compile(r"\b(19\d{2}|20\d{2}|21\d{2})\b")


def make_plan(request: ChatRequest) -> tuple[QueryPlan, IndicatorDef]:
    text = request.message.strip()
    lower = text.lower()
    indicator = _predict_indicator(text, request.indicator_id)
    countries = match_countries(text, request.countries)
    years = [int(value) for value in YEAR_RE.findall(text)]

    start_year = request.start_year
    end_year = request.end_year
    if start_year is None and years:
        start_year = min(years)
    if end_year is None and len(years) >= 2:
        end_year = max(years)

    forecast_years = request.forecast_years or _extract_horizon(lower) or DEFAULT_FORECAST_YEARS
    intent = _intent(lower, len(countries))
    chart = "bar" if intent in {"compare", "ranking"} else "line"

    plan = QueryPlan(
        raw_query=text,
        intent=intent,
        indicator_id=indicator.id,
        countries=countries,
        start_year=start_year,
        end_year=end_year,
        forecast_years=forecast_years,
        chart=chart,
    )
    return plan, indicator


def clarification_questions(request: ChatRequest, plan: QueryPlan) -> list[str]:
    questions: list[str] = []
    has_indicator = _has_indicator_context(request)
    has_country = _has_country_context(request)

    if not has_indicator:
        questions.append(
            "Which public health indicator should I analyze: malaria incidence, TB incidence, "
            "maternal mortality, life expectancy, hospital beds, or another WHO indicator?"
        )

    if plan.intent == "compare":
        if len(plan.countries) < 2:
            questions.append("Which countries should I compare? Please give at least two.")
    elif plan.intent == "ranking":
        if not has_country:
            questions.append(
                "Which countries should I rank? You can name a few countries, or ask for a global ranking."
            )
    elif not has_country:
        questions.append("Which country should I use? For example: India, Brazil, United States, or World.")

    return questions


def build_clarification_answer(
    plan: QueryPlan,
    indicator: IndicatorDef,
    questions: list[str],
) -> tuple[str, list[str], list[str]]:
    answer = (
        "I need a little more detail before I fetch public health data confidently. "
        + " ".join(questions)
    )
    follow_ups = [
        "Compare malaria incidence in India and Brazil",
        "Forecast tuberculosis incidence in India for 3 years",
        "Is maternal mortality improving in India?",
    ]
    if plan.intent == "compare" and plan.countries:
        follow_ups.insert(0, f"Compare {indicator.label} in India and Brazil since 2010")
    return (
        answer,
        follow_ups[:4],
        ["No source data was fetched because the question needs clarification first."],
    )


def _intent(lower: str, country_count: int) -> str:
    model_prediction = get_query_model().predict_intent(lower)
    if any(word in lower for word in ("report", "brief", "summary report")):
        return "report"
    if any(word in lower for word in ("forecast", "predict", "future", "next")):
        return "forecast"
    if any(word in lower for word in ("risk", "outbreak", "spike", "alert", "danger")):
        return "risk"
    if any(word in lower for word in ("highest", "lowest", "top", "rank", "ranking")):
        return "ranking"
    if country_count > 1 or any(word in lower for word in ("compare", "versus", " vs ", "between")):
        return "compare"
    if model_prediction.confidence >= 0.28:
        return model_prediction.intent
    return "trend"


def _predict_indicator(text: str, explicit_id: str | None) -> IndicatorDef:
    if explicit_id:
        return match_indicator(text, explicit_id)
    model_prediction = get_query_model().predict_indicator(text)
    keyword_prediction = match_indicator(text)
    if model_prediction.confidence >= 0.18:
        return model_prediction.indicator
    return keyword_prediction


def _extract_horizon(lower: str) -> int | None:
    match = re.search(r"(?:next|for)\s+(\d{1,2})\s+(year|years)", lower)
    if not match:
        return None
    return max(1, min(10, int(match.group(1))))


def _has_country_context(request: ChatRequest) -> bool:
    if request.countries:
        return any(code.upper() in COUNTRIES for code in request.countries)
    lower = request.message.lower()
    return any(
        any(_contains_token(lower, token) for token in (country.name, code, *country.aliases))
        for code, country in COUNTRIES.items()
    )


def _has_indicator_context(request: ChatRequest) -> bool:
    if request.indicator_id:
        return request.indicator_id in INDICATORS
    lower = request.message.lower()
    for indicator in INDICATORS.values():
        tokens = (indicator.id.replace("_", " "), indicator.label, *indicator.aliases)
        if any(_contains_token(lower, token) for token in tokens):
            return True
    return False


def _contains_token(query: str, token: str) -> bool:
    escaped = re.escape(token.lower())
    return re.search(rf"(?<![a-z0-9]){escaped}(?![a-z0-9])", query) is not None


def build_answer(
    plan: QueryPlan,
    indicator: IndicatorDef,
    series: list[Series],
    insights: list[SeriesInsight],
) -> tuple[str, list[str], list[str]]:
    limitations: list[str] = []
    if not series:
        return (
            f"I could not find usable observations for {indicator.label} with the selected country and year filters.",
            [
                "Try a wider year range.",
                "Try another country or indicator.",
                "Upload a custom CSV if your topic is regional or disease-specific.",
            ],
            ["No data points were returned by the selected public source."],
        )

    primary = insights[0]
    answer_parts: list[str] = []
    if plan.intent == "compare" and len(insights) > 1:
        ranked = sorted(
            [item for item in insights if item.latest_value is not None],
            key=lambda item: item.latest_value or 0,
            reverse=True,
        )
        if ranked:
            leader = ranked[0]
            answer_parts.append(
                f"{leader.country_name} has the highest latest value for {indicator.label}: "
                f"{leader.latest_value:.2f} {indicator.unit} in {leader.latest_year}."
            )
        summary = ", ".join(
            f"{item.country_name}: {item.latest_value:.2f} in {item.latest_year}"
            for item in ranked
            if item.latest_value is not None
        )
        if summary:
            answer_parts.append(summary + ".")
    else:
        if primary.latest_value is not None:
            answer_parts.append(
                f"For {primary.country_name}, the latest {indicator.label} value is "
                f"{primary.latest_value:.2f} {indicator.unit} in {primary.latest_year}."
            )
        answer_parts.append(f"The selected series is {primary.trend_label}.")
        direction = _health_direction(indicator, primary.trend_label)
        if direction:
            answer_parts.append(direction)
        if primary.percent_change is not None:
            answer_parts.append(f"The latest year-over-year change is {primary.percent_change:.1f}%.")

    if plan.intent in {"risk", "report"}:
        answer_parts.append(
            f"Risk level: {primary.risk.level.replace('_', ' ')} "
            f"({primary.risk.score:.0f}/100). {primary.risk.reason}"
        )

    if plan.intent in {"forecast", "report"} and primary.forecast:
        last_forecast = primary.forecast[-1]
        answer_parts.append(
            f"The {plan.forecast_years}-year damped trend forecast reaches "
            f"{last_forecast.value:.2f} {indicator.unit} by {last_forecast.year}."
        )

    for item in insights:
        limitations.extend(item.data_quality)
    if indicator.source == "Our World in Data":
        limitations.append("COVID series are aggregated to annual averages from higher-frequency source data.")
    if plan.intent in {"forecast", "report"} and any(item.forecast for item in insights):
        limitations.append("Forecasts are statistical estimates, not clinical or government advisories.")

    follow_ups = [
        f"Compare {indicator.label} for India and United States since 2010",
        f"Forecast {indicator.label} for India for the next 3 years",
        f"Show risk alerts for {indicator.label} in India",
    ]
    return " ".join(answer_parts), follow_ups, sorted(set(limitations))


def _health_direction(indicator: IndicatorDef, trend_label: str) -> str | None:
    if trend_label not in {"increasing", "decreasing", "stable"}:
        return None
    if trend_label == "stable":
        return "From a public-health view, this looks mostly stable."
    if indicator.polarity == "higher_is_good":
        status = "improving" if trend_label == "increasing" else "worsening"
    elif indicator.polarity == "higher_is_bad":
        status = "improving" if trend_label == "decreasing" else "worsening"
    else:
        return None
    return f"From a public-health view, this looks {status}."
