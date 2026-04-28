from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class SourceCitation(BaseModel):
    name: str
    url: str
    accessed_via: str
    note: str | None = None


class MetricInfo(BaseModel):
    id: str
    label: str
    unit: str
    source: str
    source_id: str
    polarity: Literal["higher_is_good", "higher_is_bad", "mixed"]
    bounded_100: bool = False


class DataPoint(BaseModel):
    year: int
    value: float


class Series(BaseModel):
    country_code: str
    country_name: str
    points: list[DataPoint]


class ForecastPoint(BaseModel):
    year: int
    value: float
    lower: float
    upper: float


class RiskAssessment(BaseModel):
    level: Literal["low", "moderate", "high", "insufficient_data"]
    score: float = Field(ge=0, le=100)
    reason: str


class SeriesInsight(BaseModel):
    country_code: str
    country_name: str
    latest_year: int | None
    latest_value: float | None
    previous_value: float | None
    percent_change: float | None
    trend_label: str
    annual_slope: float | None
    r_squared: float | None
    min_value: float | None
    max_value: float | None
    risk: RiskAssessment
    forecast: list[ForecastPoint]
    data_quality: list[str]


class QueryPlan(BaseModel):
    raw_query: str
    intent: Literal["trend", "compare", "forecast", "risk", "ranking", "report"]
    indicator_id: str
    countries: list[str]
    start_year: int | None = None
    end_year: int | None = None
    forecast_years: int = 3
    chart: Literal["line", "bar", "ranking"] = "line"


class ChatRequest(BaseModel):
    message: str
    indicator_id: str | None = None
    countries: list[str] | None = None
    start_year: int | None = None
    end_year: int | None = None
    forecast_years: int | None = Field(default=None, ge=1, le=10)


class ChatResponse(BaseModel):
    answer: str
    plan: QueryPlan
    metric: MetricInfo
    series: list[Series]
    insights: list[SeriesInsight]
    citations: list[SourceCitation]
    follow_up_questions: list[str]
    limitations: list[str]
    needs_clarification: bool = False
    clarification_questions: list[str] = []


class IndicatorOption(BaseModel):
    id: str
    label: str
    unit: str
    source: str
    aliases: list[str]


class CountryOption(BaseModel):
    code: str
    name: str
    aliases: list[str] = []


class ReportRequest(BaseModel):
    response: ChatResponse


class ReportResponse(BaseModel):
    title: str
    markdown: str


class UploadResult(BaseModel):
    dataset_id: str
    rows_ingested: int
    indicators: list[str]
    countries: list[str]
    warnings: list[str]


class CustomAnalyzeRequest(BaseModel):
    dataset_id: str
    indicator: str
    countries: list[str] | None = None
    start_year: int | None = None
    end_year: int | None = None
    forecast_years: int = Field(default=3, ge=1, le=10)
