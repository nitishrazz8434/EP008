from __future__ import annotations

import math
from statistics import mean, pstdev

from app.data_sources.registry import IndicatorDef
from app.models import ForecastPoint, RiskAssessment, Series, SeriesInsight


def build_insights(series_list: list[Series], indicator: IndicatorDef, horizon: int) -> list[SeriesInsight]:
    return [analyze_series(series, indicator, horizon) for series in series_list]


def analyze_series(series: Series, indicator: IndicatorDef, horizon: int) -> SeriesInsight:
    points = sorted(series.points, key=lambda point: point.year)
    quality: list[str] = []
    if len(points) < 3:
        quality.append("Fewer than 3 observations; trend and forecast confidence are limited.")

    years = [point.year for point in points]
    values = [point.value for point in points]
    if years:
        missing_years = (max(years) - min(years) + 1) - len(set(years))
        if missing_years > 0:
            quality.append(f"{missing_years} year(s) are missing inside the selected range.")

    latest = points[-1] if points else None
    previous = points[-2] if len(points) >= 2 else None
    percent_change = None
    if latest and previous and previous.value != 0:
        percent_change = ((latest.value - previous.value) / abs(previous.value)) * 100

    slope, intercept, r_squared = _linear_regression(years, values)
    trend_label = _trend_label(slope, values)
    forecast = _forecast(years, values, indicator, horizon, slope, intercept, r_squared)
    risk = _risk_assessment(values, percent_change, indicator)

    return SeriesInsight(
        country_code=series.country_code,
        country_name=series.country_name,
        latest_year=latest.year if latest else None,
        latest_value=latest.value if latest else None,
        previous_value=previous.value if previous else None,
        percent_change=percent_change,
        trend_label=trend_label,
        annual_slope=slope,
        r_squared=r_squared,
        min_value=min(values) if values else None,
        max_value=max(values) if values else None,
        risk=risk,
        forecast=forecast,
        data_quality=quality,
    )


def _linear_regression(years: list[int], values: list[float]) -> tuple[float | None, float | None, float | None]:
    if len(years) < 2:
        return None, None, None
    x_mean = mean(years)
    y_mean = mean(values)
    numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(years, values, strict=True))
    denominator = sum((x - x_mean) ** 2 for x in years)
    if denominator == 0:
        return None, None, None
    slope = numerator / denominator
    intercept = y_mean - slope * x_mean
    predictions = [slope * x + intercept for x in years]
    ss_res = sum((y - y_hat) ** 2 for y, y_hat in zip(values, predictions, strict=True))
    ss_tot = sum((y - y_mean) ** 2 for y in values)
    r_squared = 1 - (ss_res / ss_tot) if ss_tot else 1.0
    return slope, intercept, max(0.0, min(1.0, r_squared))


def _trend_label(slope: float | None, values: list[float]) -> str:
    if slope is None or not values:
        return "insufficient data"
    baseline = max(abs(mean(values)), 1e-9)
    relative_slope = abs(slope) / baseline
    if relative_slope < 0.005:
        return "stable"
    return "increasing" if slope > 0 else "decreasing"


def _forecast(
    years: list[int],
    values: list[float],
    indicator: IndicatorDef,
    horizon: int,
    slope: float | None,
    intercept: float | None,
    r_squared: float | None,
) -> list[ForecastPoint]:
    if len(years) < 3:
        return []

    forecast_values, residuals = _damped_recent_trend_forecast(years, values, horizon)
    error = pstdev(residuals) if len(residuals) > 1 else 0.0
    confidence_multiplier = 1.0 + (1.0 - (r_squared or 0.0))
    forecast: list[ForecastPoint] = []
    last_year = max(years)
    for offset, predicted in enumerate(forecast_values, start=1):
        year = last_year + offset
        predicted = _clamp(predicted, indicator)
        interval = max(error * confidence_multiplier * math.sqrt(offset), abs(predicted) * 0.03)
        forecast.append(
            ForecastPoint(
                year=year,
                value=predicted,
                lower=_clamp(predicted - interval, indicator),
                upper=_clamp(predicted + interval, indicator),
            )
        )
    return forecast


def _damped_recent_trend_forecast(
    years: list[int],
    values: list[float],
    horizon: int,
) -> tuple[list[float], list[float]]:
    recent_count = min(10, len(values))
    recent_years = years[-recent_count:]
    recent_values = values[-recent_count:]
    recent_slope, recent_intercept, _ = _linear_regression(recent_years, recent_values)
    if recent_slope is None or recent_intercept is None:
        return [], []

    fitted = [recent_slope * year + recent_intercept for year in recent_years]
    residuals = [actual - predicted for actual, predicted in zip(recent_values, fitted, strict=True)]

    last_value = values[-1]
    forecast_values: list[float] = []
    level = last_value
    damping = 0.72
    for offset in range(1, horizon + 1):
        level += recent_slope * (damping ** (offset - 1))
        if last_value > 0 and recent_slope < 0:
            level = max(level, last_value * (0.55 ** offset))
        forecast_values.append(level)
    return forecast_values, residuals


def _clamp(value: float, indicator: IndicatorDef) -> float:
    value = max(0.0, value)
    if indicator.bounded_100:
        value = min(100.0, value)
    return value


def _risk_assessment(
    values: list[float],
    percent_change: float | None,
    indicator: IndicatorDef,
) -> RiskAssessment:
    if len(values) < 4:
        return RiskAssessment(
            level="insufficient_data",
            score=0,
            reason="Risk scoring needs at least 4 observations.",
        )

    latest = values[-1]
    baseline_values = values[:-1][-5:]
    baseline = mean(baseline_values)
    spread = pstdev(baseline_values) if len(baseline_values) > 1 else 0.0
    z_score = (latest - baseline) / spread if spread > 0 else 0.0
    change = percent_change or 0.0

    if indicator.polarity == "higher_is_good":
        adverse_change = -change
        adverse_z = -z_score
    elif indicator.polarity == "higher_is_bad":
        adverse_change = change
        adverse_z = z_score
    else:
        adverse_change = abs(change)
        adverse_z = abs(z_score)

    score = min(100.0, max(0.0, adverse_z * 25 + adverse_change * 1.4))
    if score >= 65:
        level = "high"
    elif score >= 30:
        level = "moderate"
    else:
        level = "low"

    direction = "above" if latest >= baseline else "below"
    reason = f"Latest value is {direction} the recent baseline"
    if percent_change is not None:
        reason += f" with a {percent_change:.1f}% year-over-year change."
    else:
        reason += "."

    return RiskAssessment(level=level, score=round(score, 1), reason=reason)
